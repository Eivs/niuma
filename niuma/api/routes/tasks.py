"""Task management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel

router = APIRouter()


class CreateTaskRequest(BaseModel):
    """Request to create a task."""

    description: str
    agent_type: str = "assistant"
    use_background: bool = False
    timeout: int = 300


class TaskResponse(BaseModel):
    """Task response."""

    id: str
    status: str
    agent_type: str
    created_at: str


@router.post("")
async def create_task(request: CreateTaskRequest) -> dict[str, Any]:
    """Create and execute a task."""
    from niuma.api.main import _orchestrator

    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    result = await _orchestrator.execute(
        request.description,
        agent_type=request.agent_type,
        use_background=request.use_background,
    )

    # Handle both TaskResult and string (background task ID)
    if isinstance(result, str):
        return {
            "task_id": result,
            "status": "background",
            "message": "Task submitted for background execution",
        }
    else:
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata,
        }


@router.post("/batch")
async def create_tasks_batch(
    requests: list[CreateTaskRequest],
) -> list[dict[str, Any]]:
    """Execute multiple tasks in batch."""
    from niuma.api.main import _orchestrator

    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    tasks = [(r.description, r.agent_type) for r in requests]
    results = await _orchestrator.execute_parallel(tasks)

    response = []
    for req, result in zip(requests, results):
        if hasattr(result, "success"):
            response.append({
                "success": result.success,
                "output": result.output,
                "error": result.error,
            })
        else:
            response.append({
                "task_id": result,
                "status": "background",
            })

    return response


@router.websocket("/ws/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    """WebSocket for real-time task updates."""
    await websocket.accept()

    try:
        while True:
            # In a full implementation, this would stream task progress
            # For now, just echo back
            data = await websocket.receive_text()
            await websocket.send_json({
                "task_id": task_id,
                "status": "running",
                "message": f"Received: {data}",
            })
    except Exception:
        await websocket.close()
