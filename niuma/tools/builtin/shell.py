"""Shell execution tool for Niuma."""

import asyncio
from pathlib import Path
from typing import Any

from niuma.tools.registry import BaseTool, ToolInfo, ToolParameter, ToolResult


class ShellTool(BaseTool):
    """Tool for executing shell commands."""

    def __init__(
        self,
        working_dir: Path | None = None,
        allowed_commands: list[str] | None = None,
        timeout: int = 60,
    ) -> None:
        """Initialize shell tool.

        Args:
            working_dir: Working directory for commands.
            allowed_commands: List of allowed command prefixes.
            timeout: Command timeout in seconds.
        """
        self.working_dir = working_dir or Path.cwd()
        self.allowed_commands = allowed_commands or []
        self.timeout = timeout

        self._info = ToolInfo(
            name="shell",
            description="Execute shell commands",
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="Command to execute",
                    required=True,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds",
                    required=False,
                ),
            ],
            metadata={"type": "builtin", "category": "system"},
        )

    @property
    def info(self) -> ToolInfo:
        """Tool information."""
        return self._info

    def _is_allowed(self, command: str) -> bool:
        """Check if command is allowed."""
        if not self.allowed_commands:
            return True

        cmd = command.strip().split()[0]
        return any(allowed in cmd for allowed in self.allowed_commands)

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute shell command."""
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", self.timeout)

        if not command:
            return ToolResult(success=False, error="No command provided")

        if not self._is_allowed(command):
            return ToolResult(
                success=False,
                error=f"Command not allowed: {command}",
            )

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return ToolResult(
                success=process.returncode == 0,
                data={
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "returncode": process.returncode,
                },
                error=stderr.decode("utf-8") if process.returncode != 0 else None,
            )

        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s")

        except Exception as e:
            return ToolResult(success=False, error=str(e))
