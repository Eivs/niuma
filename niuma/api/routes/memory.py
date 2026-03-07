"""Memory management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class StoreMemoryRequest(BaseModel):
    """Request to store a memory."""

    key: str
    value: Any
    memory_type: str = "auto"
    importance: float = 0.5
    category: str = "general"


class QueryMemoryRequest(BaseModel):
    """Request to query memories."""

    query: str
    memory_type: str = "semantic"
    n_results: int = 5


@router.post("/store")
async def store_memory(request: StoreMemoryRequest) -> dict[str, Any]:
    """Store a memory."""
    from niuma.memory import MemoryManager

    memory = MemoryManager()
    await memory.initialize()

    memory_id = await memory.store(
        key=request.key,
        value=request.value,
        memory_type=request.memory_type,
        importance=request.importance,
        category=request.category,
    )

    return {
        "success": True,
        "memory_id": memory_id,
        "type": request.memory_type,
    }


@router.get("/retrieve/{key}")
async def retrieve_memory(
    key: str,
    memory_type: str = "short_term",
) -> dict[str, Any]:
    """Retrieve a memory."""
    from niuma.memory import MemoryManager

    memory = MemoryManager()
    await memory.initialize()

    value = await memory.retrieve(key, memory_type=memory_type)

    if value is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"key": key, "value": value, "type": memory_type}


@router.post("/search")
async def search_memories(request: QueryMemoryRequest) -> dict[str, Any]:
    """Search memories."""
    from niuma.memory import MemoryManager

    memory = MemoryManager()
    await memory.initialize()

    results = await memory.search(
        query=request.query,
        memory_type=request.memory_type,
        n_results=request.n_results,
    )

    return {
        "query": request.query,
        "results": results,
        "count": len(results),
    }


@router.get("/stats")
async def get_memory_stats() -> dict[str, Any]:
    """Get memory statistics."""
    from niuma.memory import MemoryManager

    memory = MemoryManager()
    await memory.initialize()

    return memory.get_stats()
