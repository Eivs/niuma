"""Tests for task module."""

import pytest

from niuma.core.task import Task, TaskResult, TaskStatus, TaskType


class TestTask:
    """Test task model."""

    def test_task_creation(self):
        """Test creating a task."""
        task = Task(description="Test task")

        assert task.description == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.type == TaskType.ATOMIC

    def test_task_status_transitions(self):
        """Test task status transitions."""
        task = Task(description="Test task")

        # Start task
        task.mark_started()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None

        # Complete task
        result = TaskResult(success=True, output="done")
        task.mark_completed(result)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.result == result

    def test_task_dependencies(self):
        """Test task dependency checking."""
        task = Task(description="Test", dependencies=["dep1", "dep2"])

        assert not task.is_ready(set())
        assert not task.is_ready({"dep1"})
        assert task.is_ready({"dep1", "dep2"})

    def test_terminal_states(self):
        """Test terminal state detection."""
        task = Task(description="Test")

        assert not task.is_terminal()

        task.mark_completed(TaskResult(success=True))
        assert task.is_terminal()
