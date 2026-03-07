"""Team protocol definitions for multi-agent collaboration.

This will be expanded in Stage 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CommunicationProtocol(Enum):
    """Communication protocols for agent interaction."""

    MESSAGE_QUEUE = "message_queue"
    DIRECT = "direct"
    BROADCAST = "broadcast"


class CollaborationMode(Enum):
    """Collaboration modes for agent teams."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class AgentRole:
    """Definition of an agent role in the team."""

    name: str
    description: str = ""
    responsibilities: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    system_prompt: str = ""


@dataclass
class CommunicationConfig:
    """Configuration for team communication."""

    protocol: CommunicationProtocol = CommunicationProtocol.MESSAGE_QUEUE
    priority_levels: int = 3
    message_ttl: int = 300  # seconds
    max_queue_size: int = 1000


@dataclass
class CollaborationConfig:
    """Configuration for team collaboration."""

    mode: CollaborationMode = CollaborationMode.HYBRID
    max_agents: int = 5
    load_balancing: bool = True
    fault_tolerance: bool = True


@dataclass
class TeamProtocol:
    """Complete team protocol configuration."""

    name: str = "default"
    roles: list[AgentRole] = field(default_factory=list)
    communication: CommunicationConfig = field(default_factory=CommunicationConfig)
    collaboration: CollaborationConfig = field(default_factory=CollaborationConfig)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "roles": [
                {
                    "name": r.name,
                    "description": r.description,
                    "responsibilities": r.responsibilities,
                    "skills": r.skills,
                }
                for r in self.roles
            ],
            "communication": {
                "protocol": self.communication.protocol.value,
                "priority_levels": self.communication.priority_levels,
            },
            "collaboration": {
                "mode": self.collaboration.mode.value,
                "max_agents": self.collaboration.max_agents,
            },
        }
