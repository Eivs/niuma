"""Tool registry for Niuma - dynamic tool discovery and management."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: str
    description: str = ""
    required: bool = True
    default: Any = None
    enum: list[Any] | None = None


@dataclass
class ToolResult:
    """Result of tool execution."""

    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolInfo:
    """Information about a registered tool."""

    name: str
    description: str
    parameters: list[ToolParameter]
    returns: dict[str, Any] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_schema(self) -> dict[str, Any]:
        """Convert to JSON schema format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class BaseTool(ABC):
    """Base class for tools."""

    @property
    @abstractmethod
    def info(self) -> ToolInfo:
        """Tool information."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        pass

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """Validate parameters."""
        for param in self.info.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"

            value = kwargs.get(param.name)
            if value is not None and param.enum and value not in param.enum:
                return False, f"Invalid value for {param.name}: {value}"

        return True, ""


ToolFunction = Callable[..., Any]


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self) -> None:
        """Initialize tool registry."""
        self._tools: dict[str, BaseTool | ToolFunction] = {}
        self._schemas: dict[str, ToolInfo] = {}
        self._initialized = False

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize tool registry."""
        self._initialized = True

        # Register built-in tools
        await self._register_builtin_tools()

        # Discover and register MCP tools if configured
        mcp_config = config.get("mcp", {}) if config else {}
        if mcp_config.get("enabled", False):
            await self._discover_mcp_tools(mcp_config)

    async def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        # Import and register built-in tools
        try:
            from niuma.tools.builtin.file import FileTool
            from niuma.tools.builtin.shell import ShellTool

            self.register_tool(FileTool())
            self.register_tool(ShellTool())
        except ImportError:
            pass  # Built-in tools may not be fully implemented yet

    async def _discover_mcp_tools(self, config: dict[str, Any]) -> None:
        """Discover MCP tools from configured servers."""
        from niuma.tools.mcp.client import MCPClient

        client = MCPClient()
        servers = config.get("servers", [])

        for server_config in servers:
            try:
                await client.connect_to_server(server_config)
                tools = await client.list_tools()

                for tool in tools:
                    self.register(tool.name, tool)

            except Exception as e:
                # Log error but continue with other servers
                print(f"Failed to connect to MCP server {server_config}: {e}")

    def register(self, name: str, tool: BaseTool | ToolFunction) -> None:
        """Register a tool.

        Args:
            name: Tool name.
            tool: Tool instance or function.
        """
        self._tools[name] = tool

        # Store schema if available
        if isinstance(tool, BaseTool):
            self._schemas[name] = tool.info

    def register_tool(self, tool: BaseTool) -> None:
        """Register a BaseTool instance.

        Args:
            tool: Tool to register.
        """
        self.register(tool.info.name, tool)

    def unregister(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name.

        Returns:
            True if removed, False if not found.
        """
        if name in self._tools:
            del self._tools[name]
            self._schemas.pop(name, None)
            return True
        return False

    def get(self, name: str) -> BaseTool | ToolFunction | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool instance or None if not found.
        """
        return self._tools.get(name)

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Execute a tool.

        Args:
            name: Tool name.
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Tool not found: {name}",
            )

        try:
            if isinstance(tool, BaseTool):
                # Validate parameters
                valid, error = tool.validate(**kwargs)
                if not valid:
                    return ToolResult(success=False, error=error)

                # Execute
                return await tool.execute(**kwargs)

            else:
                # Execute function directly
                import asyncio

                if asyncio.iscoroutinefunction(tool):
                    result = await tool(**kwargs)
                else:
                    result = tool(**kwargs)

                return ToolResult(success=True, data=result)

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tools_schema(self) -> list[dict[str, Any]]:
        """Get schemas for all tools."""
        return [info.to_schema() for info in self._schemas.values()]

    def get_tool_info(self, name: str) -> ToolInfo | None:
        """Get information about a tool."""
        return self._schemas.get(name)

    def find_tools(
        self,
        query: str,
        tags: list[str] | None = None,
    ) -> list[ToolInfo]:
        """Find tools matching query.

        Args:
            query: Search query.
            tags: Filter by tags.

        Returns:
            List of matching tool info.
        """
        matching = []
        for name, info in self._schemas.items():
            if query.lower() in name.lower() or query.lower() in info.description.lower():
                if tags:
                    tool_tags = info.metadata.get("tags", [])
                    if not any(tag in tool_tags for tag in tags):
                        continue
                matching.append(info)
        return matching

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._tools.clear()
        self._schemas.clear()
        self._initialized = False

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
