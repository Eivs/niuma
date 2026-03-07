"""Task scheduler for Niuma."""

from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from niuma.core.task import Task, TaskResult, TaskStatus

if TYPE_CHECKING:
    from niuma.core.agent import Agent


@dataclass(order=True)
class PrioritizedTask:
    """Task with priority for the queue."""

    priority: int
    sequence: int
    task: Task = field(compare=False)


class DependencyGraph:
    """Manages task dependencies."""

    def __init__(self) -> None:
        """Initialize empty dependency graph."""
        self._graph: dict[str, set[str]] = {}  # task_id -> dependencies
        self._reverse: dict[str, set[str]] = {}  # task_id -> dependents

    def add_task(self, task_id: str, dependencies: list[str]) -> None:
        """Add a task with its dependencies."""
        self._graph[task_id] = set(dependencies)
        for dep in dependencies:
            if dep not in self._reverse:
                self._reverse[dep] = set()
            self._reverse[dep].add(task_id)

    def is_ready(self, task_id: str, completed: set[str]) -> bool:
        """Check if task dependencies are satisfied."""
        return self._graph.get(task_id, set()).issubset(completed)

    def get_dependents(self, task_id: str) -> set[str]:
        """Get tasks that depend on the given task."""
        return self._reverse.get(task_id, set())

    def topological_sort(self) -> list[str]:
        """Return tasks in topological order."""
        in_degree = {task: len(deps) for task, deps in self._graph.items()}
        queue = [task for task, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            task = queue.pop(0)
            result.append(task)
            for dependent in self._reverse.get(task, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result


class TaskScheduler:
    """Schedules and executes tasks with dependency management."""

    def __init__(self, max_concurrency: int = 5) -> None:
        """Initialize the scheduler."""
        self._queue: list[PrioritizedTask] = []
        self._running: dict[str, Task] = {}
        self._completed: set[str] = set()
        self._failed: dict[str, Exception] = {}
        self._dependency_graph = DependencyGraph()
        self._tasks: dict[str, Task] = {}
        self.max_concurrency = max_concurrency
        self._sequence = 0
        self._lock = asyncio.Lock()
        self._running_flag = False

    def add_task(self, task: Task) -> None:
        """Add a task to the scheduler."""
        self._dependency_graph.add_task(task.id, task.dependencies)
        self._tasks[task.id] = task
        self._sequence += 1
        prioritized = PrioritizedTask(
            priority=task.priority,
            sequence=self._sequence,
            task=task,
        )
        heapq.heappush(self._queue, prioritized)

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_ready_tasks(self) -> list[Task]:
        """Get tasks that are ready to execute."""
        ready = []
        for pt in self._queue:
            if self._dependency_graph.is_ready(pt.task.id, self._completed):
                ready.append(pt.task)
        return ready

    async def schedule(self, task: Task, agent: Agent | None = None) -> TaskResult:
        """Schedule and execute a single task."""
        self.add_task(task)
        return await self._execute_task(task, agent)

    async def run(self, agents: dict[str, Agent] | None = None) -> dict[str, Task]:
        """Run the scheduler until all tasks complete."""
        self._running_flag = True

        while self._queue or self._running:
            if not self._running_flag:
                break

            async with self._lock:
                # Start ready tasks up to max concurrency
                while len(self._running) < self.max_concurrency and self._queue:
                    ready_pts = [
                        pt for pt in self._queue
                        if self._dependency_graph.is_ready(pt.task.id, self._completed)
                        and pt.task.id not in self._running
                    ]

                    if not ready_pts:
                        break

                    # Get highest priority ready task
                    ready_pts.sort()
                    prioritized = ready_pts[0]
                    self._queue.remove(prioritized)

                    # Start task execution
                    task = prioritized.task
                    self._running[task.id] = task

                    # Get agent for task (use assigned agent or default)
                    agent = None
                    if agents and task.assigned_to:
                        agent = agents.get(task.assigned_to)

                    # Create task execution
                    asyncio.create_task(self._execute_and_cleanup(task, agent))

            await asyncio.sleep(0.1)

        return self._tasks

    async def _execute_and_cleanup(self, task: Task, agent: Agent | None) -> None:
        """Execute task and clean up."""
        try:
            await self._execute_task(task, agent)
        finally:
            async with self._lock:
                if task.id in self._running:
                    del self._running[task.id]

    async def _execute_task(
        self,
        task: Task,
        agent: Agent | None,
    ) -> TaskResult:
        """Execute a single task."""
        task.mark_started()

        try:
            if agent is None:
                # No agent available - task fails
                result = TaskResult(
                    success=False,
                    error="No agent available to execute task",
                )
            else:
                # Run the task with the agent
                result = await agent.run(task)

            task.mark_completed(result)

            if result.success:
                self._completed.add(task.id)
            else:
                self._failed[task.id] = Exception(result.error or "Unknown error")

        except asyncio.TimeoutError:
            result = TaskResult(success=False, error=f"Task timed out after {task.timeout}s")
            task.mark_completed(result)
            self._failed[task.id] = Exception("Timeout")

        except Exception as e:
            result = TaskResult(success=False, error=str(e))
            task.mark_completed(result)
            self._failed[task.id] = e

        return result

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running_flag = False

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "queued": len(self._queue),
            "running": len(self._running),
            "completed": len(self._completed),
            "failed": len(self._failed),
        }
