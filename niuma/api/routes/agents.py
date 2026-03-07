"""Agent management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class CreateAgentRequest(BaseModel):
    """Request to create an agent."""

    agent_type: str
    custom_config: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    """Agent information response."""

    id: str
    type: str
    state: str
    role: dict[str, Any]


@router.get("")
async def list_agents() -> list[AgentResponse]:
    """List all managed agents."""
    # Import here to avoid circular imports
    from niuma.api.main import _orchestrator

    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agents = []
    for agent_id in _orchestrator.list_agents():
        agent = _orchestrator.get_agent(agent_id)
        if agent:
            agents.append(
                AgentResponse(
                    id=agent_id,
                    type=agent.role.name,
                    state=agent.state.name,
                    role={
                        "name": agent.role.name,
                        "description": agent.role.description,
                    },
                )
            )

    return agents


@router.post("")
async def create_agent(request: CreateAgentRequest) -> dict[str, Any]:
    """Create a new agent."""
    from niuma.api.main import _orchestrator

    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        agent_id = _orchestrator.create_agent(request.agent_type)
        return {"id": agent_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> AgentResponse:
    """Get agent information."""
    from niuma.api.main import _orchestrator

    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = _orchestrator.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(
        id=agent_id,
        type=agent.role.name,
        state=agent.state.name,
        role={
            "name": agent.role.name,
            "description": agent.role.description,
        },
    )


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str) -> dict[str, Any]:
    """Delete an agent."""
    from niuma.api.main import _orchestrator

    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    success = _orchestrator.terminate_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {"id": agent_id, "status": "terminated"}


@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str) -> dict[str, Any]:
    """Get detailed agent status."""
    from niuma.api.main import _orchestrator

    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = _orchestrator.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": agent_id,
        "state": agent.state.name,
        "role": {
            "name": agent.role.name,
            "responsibilities": agent.role.responsibilities,
            "skills": agent.role.skills,
        },
    }
