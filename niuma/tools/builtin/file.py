"""File system tool for Niuma."""

import asyncio
from pathlib import Path
from typing import Any

from niuma.tools.registry import BaseTool, ToolInfo, ToolParameter, ToolResult


class FileTool(BaseTool):
    """Tool for file system operations."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize file tool.

        Args:
            base_path: Base directory for operations.
        """
        self.base_path = base_path or Path.cwd()
        self._info = ToolInfo(
            name="file",
            description="File system operations",
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation to perform",
                    required=True,
                    enum=["read", "write", "list", "exists", "delete"],
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="File path",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write (for write operation)",
                    required=False,
                ),
            ],
            metadata={"type": "builtin", "category": "filesystem"},
        )

    @property
    def info(self) -> ToolInfo:
        """Tool information."""
        return self._info

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to base."""
        target = Path(path)
        if not target.is_absolute():
            target = self.base_path / target
        return target.resolve()

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute file operation."""
        operation = kwargs.get("operation")
        path = self._resolve_path(kwargs.get("path", ""))

        try:
            if operation == "read":
                if not path.exists():
                    return ToolResult(
                        success=False, error=f"File not found: {path}"
                    )
                content = await asyncio.to_thread(path.read_text, encoding="utf-8")
                return ToolResult(success=True, data={"content": content})

            elif operation == "write":
                content = kwargs.get("content", "")
                await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
                await asyncio.to_thread(path.write_text, content, encoding="utf-8")
                return ToolResult(success=True, data={"path": str(path)})

            elif operation == "list":
                if not path.exists():
                    return ToolResult(
                        success=False, error=f"Directory not found: {path}"
                    )
                items = [
                    {"name": item.name, "type": "dir" if item.is_dir() else "file"}
                    for item in path.iterdir()
                ]
                return ToolResult(success=True, data={"items": items})

            elif operation == "exists":
                exists = await asyncio.to_thread(path.exists)
                return ToolResult(success=True, data={"exists": exists})

            elif operation == "delete":
                if path.is_file():
                    await asyncio.to_thread(path.unlink)
                elif path.is_dir():
                    await asyncio.to_thread(path.rmdir)
                return ToolResult(success=True)

            else:
                return ToolResult(success=False, error=f"Unknown operation: {operation}")

        except Exception as e:
            return ToolResult(success=False, error=str(e))
