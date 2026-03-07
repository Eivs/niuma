"""Tool management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ExecuteToolRequest(BaseModel):
    """Request to execute a tool."""

    name: str
    params: dict[str, Any] = {}


@router.get("")
async def list_tools() -> list[dict[str, Any]]:
    """List available tools."""
    from niuma.tools import ToolRegistry

    registry = ToolRegistry()
    await registry.initialize()

    return [
        {"name": name, "info": registry.get_tool_info(name)}
        for name in registry.list_tools()
    ]


@router.post("/execute")
async def execute_tool(request: ExecuteToolRequest) -> dict[str, Any]:
    """Execute a tool."""
    from niuma.tools import ToolRegistry

    registry = ToolRegistry()
    await registry.initialize()

    result = await registry.execute(request.name, **request.params)

    return {
        "success": result.success,
        "data": result.data,
        "error": result.error,
    }


@router.get("/{name}/schema")
async def get_tool_schema(name: str) -> dict[str, Any]:
    """Get tool schema."""
    from niuma.tools import ToolRegistry

    registry = ToolRegistry()
    await registry.initialize()

    info = registry.get_tool_info(name)
    if not info:
        raise HTTPException(status_code=404, detail="Tool not found")

    return info.to_schema()
