"""FastAPI application for Niuma."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from niuma import __version__
from niuma.agents import AgentFactory, Orchestrator

# Global state
_orchestrator: Orchestrator | None = None
_agent_factory: AgentFactory | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    global _orchestrator, _agent_factory

    _agent_factory = AgentFactory()
    _orchestrator = Orchestrator()
    await _orchestrator.initialize()

    yield

    # Shutdown
    if _orchestrator:
        await _orchestrator.shutdown()


app = FastAPI(
    title="Niuma API",
    description="A cognitive multi-agent AI system",
    version=__version__,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint."""
    return {
        "name": "Niuma",
        "version": __version__,
        "status": "running",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "orchestrator": _orchestrator is not None,
    }


# Include routers
from niuma.api.routes import agents, tasks, memory, tools

app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(memory.router, prefix="/memory", tags=["memory"])
app.include_router(tools.router, prefix="/tools", tags=["tools"])
