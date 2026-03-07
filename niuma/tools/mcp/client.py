"""MCP (Model Context Protocol) client for Niuma."""

from __future__ import annotations

import asyncio
import json
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from niuma.tools.registry import ToolInfo, ToolParameter


@dataclass
class MCPTool:
    """An MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server: str = ""  # Which server this tool came from

    def to_tool_info(self) -> ToolInfo:
        """Convert to ToolInfo."""
        # Parse input schema to extract parameters
        properties = self.input_schema.get("properties", {})
        required = self.input_schema.get("required", [])

        parameters = []
        for name, prop in properties.items():
            param = ToolParameter(
                name=name,
                type=prop.get("type", "string"),
                description=prop.get("description", ""),
                required=name in required,
                enum=prop.get("enum"),
            )
            parameters.append(param)

        return ToolInfo(
            name=self.name,
            description=self.description,
            parameters=parameters,
            metadata={"source": "mcp", "server": self.server},
        )


class MCPClient:
    """Client for connecting to MCP servers."""

    def __init__(self) -> None:
        """Initialize MCP client."""
        self.sessions: dict[str, ClientSession] = {}
        self.tools: dict[str, MCPTool] = {}
        self._lock = asyncio.Lock()
        self._exit_stack = AsyncExitStack()

    async def connect_to_server(
        self,
        server_config: dict[str, Any],
    ) -> list[MCPTool]:
        """Connect to an MCP server.

        Args:
            server_config: Server configuration with keys:
                - name: Server name
                - transport: "stdio" or "sse"
                - For stdio: command, args, env
                - For sse: url

        Returns:
            List of available tools from this server.
        """
        name = server_config.get("name", "unknown")
        transport = server_config.get("transport", "stdio")

        async with self._lock:
            if name in self.sessions:
                # Already connected
                return [
                    tool for tool in self.tools.values() if tool.server == name
                ]

            if transport == "stdio":
                session = await self._connect_stdio(server_config)
            elif transport == "sse":
                session = await self._connect_sse(server_config)
            else:
                raise ValueError(f"Unknown transport: {transport}")

            self.sessions[name] = session

            # List and store tools
            server_tools = await self._list_tools(session, name)
            for tool in server_tools:
                self.tools[tool.name] = tool

            return server_tools

    async def _connect_stdio(
        self,
        config: dict[str, Any],
    ) -> ClientSession:
        """Connect via stdio transport."""
        command = config.get("command")
        args = config.get("args", [])
        env = config.get("env")

        if not command:
            raise ValueError("stdio transport requires 'command'")

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio_client_instance = stdio_transport[0]
        read_stream = stdio_transport[1]
        write_stream = stdio_transport[2]

        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        return session

    async def _connect_sse(
        self,
        config: dict[str, Any],
    ) -> ClientSession:
        """Connect via SSE transport."""
        url = config.get("url")

        if not url:
            raise ValueError("sse transport requires 'url'")

        # Parse URL to extract headers if present
        parsed = urlparse(url)
        headers = config.get("headers", {})

        streams = await self._exit_stack.enter_async_context(
            sse_client(url, headers=headers)
        )

        session = await self._exit_stack.enter_async_context(
            ClientSession(streams[0], streams[1])
        )
        await session.initialize()

        return session

    async def _list_tools(
        self,
        session: ClientSession,
        server_name: str,
    ) -> list[MCPTool]:
        """List tools from a session."""
        response = await session.list_tools()

        tools = []
        for tool in response.tools:
            mcp_tool = MCPTool(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema,
                server=server_name,
            )
            tools.append(mcp_tool)

        return tools

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute an MCP tool.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        session = self.sessions.get(tool.server)
        if not session:
            raise RuntimeError(f"Server not connected: {tool.server}")

        result = await session.call_tool(tool_name, arguments)
        return result

    async def list_tools(self) -> list[MCPTool]:
        """List all available tools from all servers."""
        return list(self.tools.values())

    async def get_tool(self, name: str) -> MCPTool | None:
        """Get a specific tool by name."""
        return self.tools.get(name)

    async def disconnect(self, server_name: str | None = None) -> None:
        """Disconnect from server(s).

        Args:
            server_name: Specific server to disconnect (None = all).
        """
        async with self._lock:
            if server_name:
                if server_name in self.sessions:
                    # Remove this server's tools
                    self.tools = {
                        name: tool
                        for name, tool in self.tools.items()
                        if tool.server != server_name
                    }
                    del self.sessions[server_name]
            else:
                # Disconnect all
                self.sessions.clear()
                self.tools.clear()
                await self._exit_stack.aclose()
                self._exit_stack = AsyncExitStack()

    async def is_connected(self, server_name: str) -> bool:
        """Check if connected to a server."""
        return server_name in self.sessions

    def get_server_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        stats = {}
        for name in self.sessions:
            tools = [t.name for t in self.tools.values() if t.server == name]
            stats[name] = {"connected": True, "tools": len(tools)}
        return stats
