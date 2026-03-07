"""Background task support for Niuma.

Provides async background task execution with Worktree isolation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

from niuma.core.task import Task, TaskResult, TaskStatus

if TYPE_CHECKING:
    from niuma.core.agent import Agent
    from niuma.isolation.worktree import WorktreeInfo, WorktreeManager


class BackgroundTaskState(Enum):
    """State of a background task."""

    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class BackgroundTask:
    """A background task with execution context."""

    id: str = field(default_factory=lambda: str(uuid4()))
    task: Task | None = None
    agent_factory: Callable[[], "Agent"] | None = None
    worktree_info: "WorktreeInfo | None" = None

    # Execution state
    state: BackgroundTaskState = BackgroundTaskState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    result: TaskResult | None = None
    error: str | None = None

    # Progress tracking
    progress: float = 0.0  # 0.0 to 1.0
    current_step: str = ""
    logs: list[str] = field(default_factory=list)

    # Callbacks
    on_progress: list[Callable[[float, str], None]] = field(default_factory=list)
    on_complete: list[Callable[[TaskResult], None]] = field(default_factory=list)
    on_error: list[Callable[[str], None]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task.id if self.task else None,
            "state": self.state.name,
            "progress": self.progress,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": {
                "success": self.result.success,
                "output": self.result.output if self.result else None,
                "error": self.result.error if self.result else None,
            } if self.result else None,
            "error": self.error,
        }

    def update_progress(self, progress: float, step: str) -> None:
        """Update task progress."""
        self.progress = min(max(progress, 0.0), 1.0)
        self.current_step = step
        for callback in self.on_progress:
            try:
                callback(self.progress, step)
            except Exception:
                pass

    def add_log(self, message: str) -> None:
        """Add a log entry."""
        timestamp = datetime.now().isoformat()
        self.logs.append(f"[{timestamp}] {message}")


class BackgroundTaskManager:
    """Manages background task execution with Worktree isolation."""

    def __init__(
        self,
        worktree_manager: "WorktreeManager | None" = None,
        max_concurrent: int = 5,
    ) -> None:
        """Initialize background task manager.

        Args:
            worktree_manager: Optional worktree manager for isolation.
            max_concurrent: Maximum concurrent tasks.
        """
        self.worktree_manager = worktree_manager
        self.max_concurrent = max_concurrent

        self._tasks: dict[str, BackgroundTask] = {}
        self._running: dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._shutdown = False

    async def submit(
        self,
        task: Task,
        agent_factory: Callable[[], "Agent"],
        use_worktree: bool = True,
        worktree_branch: str | None = None,
    ) -> BackgroundTask:
        """Submit a task for background execution.

        Args:
            task: The task to execute.
            agent_factory: Factory function to create an agent.
            use_worktree: Whether to use worktree isolation.
            worktree_branch: Branch to checkout in worktree.

        Returns:
            BackgroundTask handle.
        """
        bg_task = BackgroundTask(
            task=task,
            agent_factory=agent_factory,
        )

        # Create worktree if needed
        if use_worktree and self.worktree_manager:
            worktree_info = self.worktree_manager.create_worktree(
                task_id=task.id,
                branch=worktree_branch,
            )
            bg_task.worktree_info = worktree_info

        self._tasks[bg_task.id] = bg_task

        # Start execution
        asyncio.create_task(self._execute(bg_task))

        return bg_task

    async def _execute(self, bg_task: BackgroundTask) -> None:
        """Execute a background task."""
        async with self._semaphore:
            if self._shutdown:
                bg_task.state = BackgroundTaskState.CANCELLED
                return

            bg_task.state = BackgroundTaskState.RUNNING
            bg_task.started_at = datetime.now()

            try:
                # Create agent
                agent = bg_task.agent_factory()

                # Initialize agent
                await agent.initialize({})

                # Update task worktree context if applicable
                if bg_task.worktree_info:
                    if bg_task.task.metadata is None:
                        bg_task.task.metadata = {}
                    bg_task.task.metadata["worktree_id"] = bg_task.worktree_info.id
                    bg_task.task.metadata["worktree_path"] = str(
                        bg_task.worktree_info.path
                    )

                # Execute task
                bg_task.update_progress(0.1, "Starting execution")
                result = await agent.run(bg_task.task)

                # Store result
                bg_task.result = result
                bg_task.completed_at = datetime.now()

                if result.success:
                    bg_task.state = BackgroundTaskState.COMPLETED
                    bg_task.update_progress(1.0, "Completed")
                    for callback in bg_task.on_complete:
                        try:
                            callback(result)
                        except Exception:
                            pass
                else:
                    bg_task.state = BackgroundTaskState.FAILED
                    bg_task.error = result.error
                    for callback in bg_task.on_error:
                        try:
                            callback(result.error or "Unknown error")
                        except Exception:
                            pass

                # Cleanup agent
                await agent.terminate()

            except asyncio.CancelledError:
                bg_task.state = BackgroundTaskState.CANCELLED
                bg_task.error = "Task was cancelled"

            except Exception as e:
                bg_task.state = BackgroundTaskState.FAILED
                bg_task.error = str(e)
                for callback in bg_task.on_error:
                    try:
                        callback(str(e))
                    except Exception:
                        pass

            finally:
                # Mark worktree inactive
                if bg_task.worktree_info and self.worktree_manager:
                    self.worktree_manager.mark_inactive(bg_task.worktree_info.id)

                # Remove from running
                if bg_task.id in self._running:
                    del self._running[bg_task.id]

    def get_task(self, task_id: str) -> BackgroundTask | None:
        """Get background task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        state: BackgroundTaskState | None = None,
    ) -> list[BackgroundTask]:
        """List background tasks.

        Args:
            state: Filter by state. If None, returns all tasks.

        Returns:
            List of background tasks.
        """
        tasks = list(self._tasks.values())
        if state:
            tasks = [t for t in tasks if t.state == state]
        return tasks

    def cancel(self, task_id: str) -> bool:
        """Cancel a background task.

        Args:
            task_id: ID of task to cancel.

        Returns:
            True if cancelled, False if not found or already complete.
        """
        bg_task = self._tasks.get(task_id)
        if not bg_task:
            return False

        if bg_task.state in (
            BackgroundTaskState.COMPLETED,
            BackgroundTaskState.FAILED,
            BackgroundTaskState.CANCELLED,
        ):
            return False

        # Cancel running asyncio task
        if task_id in self._running:
            self._running[task_id].cancel()

        bg_task.state = BackgroundTaskState.CANCELLED
        bg_task.completed_at = datetime.now()
        return True

    async def wait_for(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> BackgroundTask:
        """Wait for a task to complete.

        Args:
            task_id: ID of task to wait for.
            timeout: Maximum time to wait.

        Returns:
            The completed background task.

        Raises:
            TimeoutError: If timeout is reached.
        """
        bg_task = self._tasks.get(task_id)
        if not bg_task:
            raise ValueError(f"Task {task_id} not found")

        # If already done, return immediately
        if bg_task.state in (
            BackgroundTaskState.COMPLETED,
            BackgroundTaskState.FAILED,
            BackgroundTaskState.CANCELLED,
        ):
            return bg_task

        # Wait for completion
        start = datetime.now()
        while bg_task.state not in (
            BackgroundTaskState.COMPLETED,
            BackgroundTaskState.FAILED,
            BackgroundTaskState.CANCELLED,
        ):
            await asyncio.sleep(0.1)

            if timeout:
                elapsed = (datetime.now() - start).total_seconds()
                if elapsed >= timeout:
                    raise TimeoutError(f"Timeout waiting for task {task_id}")

        return bg_task

    def get_status(self) -> dict[str, Any]:
        """Get manager status."""
        states = {s.name: 0 for s in BackgroundTaskState}
        for task in self._tasks.values():
            states[task.state.name] += 1

        return {
            "total_tasks": len(self._tasks),
            "running_tasks": len(self._running),
            "max_concurrent": self.max_concurrent,
            "states": states,
        }

    async def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """Shutdown the manager.

        Args:
            wait: If True, wait for running tasks to complete.
            timeout: Maximum time to wait for tasks.
        """
        self._shutdown = True

        if wait and self._running:
            start = datetime.now()
            while self._running:
                elapsed = (datetime.now() - start).total_seconds()
                if elapsed >= timeout:
                    break
                await asyncio.sleep(0.1)

        # Cancel remaining tasks
        for task_id in list(self._running.keys()):
            self._running[task_id].cancel()

        # Clean up worktrees
        if self.worktree_manager:
            self.worktree_manager.cleanup_all(force=False)
