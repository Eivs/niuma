"""Niuma - A cognitive multi-agent AI system."""

__version__ = "0.1.0"
__author__ = "Niuma Team"

from niuma.core.agent import Agent, AgentState
from niuma.core.task import Task, TaskStatus
from niuma.config import Settings

__all__ = [
    "Agent",
    "AgentState",
    "Task",
    "TaskStatus",
    "Settings",
]
