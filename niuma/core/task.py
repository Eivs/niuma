"""Task model for Niuma."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
from uuid import uuid4


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    BLOCKED = auto()
    CANCELLED = auto()
    RETRYING = auto()


class TaskType(Enum):
    """Task type classification."""

    ATOMIC = auto()
    COMPOSITE = auto()
    SUBTASK = auto()


@dataclass
class TaskResult:
    """Result of a task execution."""

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Task definition and state."""

    # Identity
    id: str = field(default_factory=lambda: str(uuid4()))
    type: TaskType = TaskType.ATOMIC
    status: TaskStatus = TaskStatus.PENDING

    # Content
    description: str = ""
    goal: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)

    # Hierarchy
    parent_id: str | None = None
    subtask_ids: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    # Execution
    assigned_to: str | None = None
    tools: list[str] = field(default_factory=list)
    timeout: int = 300
    max_retries: int = 3
    current_retry: int = 0

    # Timing
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    result: TaskResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_started(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def mark_completed(self, result: TaskResult) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        self.result = result
        self.completed_at = datetime.now()

    def mark_blocked(self) -> None:
        """Mark task as blocked (dependencies not met)."""
        self.status = TaskStatus.BLOCKED

    def mark_retrying(self) -> None:
        """Mark task as retrying."""
        self.status = TaskStatus.RETRYING
        self.current_retry += 1

    def mark_cancelled(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()

    def is_ready(self, completed_ids: set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        return set(self.dependencies).issubset(completed_ids)

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.current_retry < self.max_retries and not self.is_terminal()

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "type": self.type.name,
            "status": self.status.name,
            "description": self.description,
            "goal": self.goal,
            "acceptance_criteria": self.acceptance_criteria,
            "parent_id": self.parent_id,
            "subtask_ids": self.subtask_ids,
            "dependencies": self.dependencies,
            "assigned_to": self.assigned_to,
            "tools": self.tools,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "current_retry": self.current_retry,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": {
                "success": self.result.success,
                "output": str(self.result.output) if self.result.output else None,
                "error": self.result.error,
            } if self.result else None,
            "metadata": self.metadata,
        }
