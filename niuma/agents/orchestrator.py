"""Orchestrator agent for coordinating multiple agents.

Manages agent lifecycle, task delegation, and result aggregation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from niuma.agents.factory import AgentFactory
from niuma.core.agent import AgentRole
from niuma.core.background import BackgroundTaskManager
from niuma.core.messaging import MessageBus, MessagePriority, MessageType
from niuma.core.task import Task, TaskResult
from niuma.isolation.worktree import WorktreeManager

if TYPE_CHECKING:
    from niuma.core.agent import AgentRuntime


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""

    max_sub_agents: int = 5
    enable_parallel: bool = True
    default_timeout: int = 300
    auto_decompose: bool = True
    use_worktree_isolation: bool = True


class Orchestrator:
    """Orchestrator for managing multiple agents."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        """Initialize orchestrator."""
        self.config = config or OrchestratorConfig()
        self.id = str(uuid4())

        # Agent management
        self._agents: dict[str, AgentRuntime] = {}
        self._agent_factory = AgentFactory()

        # Worktree and task management
        self._worktree_manager = WorktreeManager()
        self._background_manager: BackgroundTaskManager | None = None
        if self.config.use_worktree_isolation:
            self._background_manager = BackgroundTaskManager(
                worktree_manager=self._worktree_manager,
                max_concurrent=self.config.max_sub_agents,
            )

        # Communication
        self._message_bus = MessageBus()

        # State
        self._initialized = False
        self._running_tasks: dict[str, Task] = {}

    async def initialize(self) -> None:
        """Initialize the orchestrator."""
        if self._initialized:
            return

        # Start message bus
        await self._message_bus.start()

        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the orchestrator."""
        if not self._initialized:
            return

        # Stop message bus
        await self._message_bus.stop()

        # Cleanup agents
        for agent in self._agents.values():
            await agent.terminate()
        self._agents.clear()

        # Cleanup worktrees
        self._worktree_manager.cleanup_all(force=False)

        self._initialized = False

    def create_agent(
        self,
        agent_type: str | None = None,
        custom_role: AgentRole | None = None,
        agent_id: str | None = None,
    ) -> str:
        """Create a new sub-agent.

        Args:
            agent_type: Type of agent to create.
            custom_role: Optional custom role.
            agent_id: Optional custom ID.

        Returns:
            Agent ID.
        """
        agent = self._agent_factory.create(
            agent_type=agent_type or "assistant",
            agent_id=agent_id,
            custom_role=custom_role,
        )

        self._agents[agent.id] = agent

        # Register with message bus
        self._message_bus.register_agent(agent.id)

        return agent.id

    def get_agent(self, agent_id: str) -> AgentRuntime | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """List all managed agent IDs."""
        return list(self._agents.keys())

    def terminate_agent(self, agent_id: str) -> bool:
        """Terminate an agent.

        Args:
            agent_id: Agent to terminate.

        Returns:
            True if terminated, False if not found.
        """
        agent = self._agents.pop(agent_id, None)
        if agent:
            asyncio.create_task(agent.terminate())
            self._message_bus.unregister_agent(agent_id)
            return True
        return False

    async def execute(
        self,
        task_description: str,
        agent_type: str = "assistant",
        use_background: bool = False,
    ) -> TaskResult | str:
        """Execute a task.

        Args:
            task_description: What to do.
            agent_type: Type of agent to use.
            use_background: Run in background.

        Returns:
            Task result or background task ID.
        """
        # Create agent if needed
        if agent_type not in [self._agent_factory.get_role(a).name for a in self.list_agents()]:
            agent_id = self.create_agent(agent_type)
        else:
            # Find existing agent of this type
            agent_id = next(
                (aid for aid, agent in self._agents.items()
                 if agent.role.name == agent_type),
                None,
            )
            if not agent_id:
                agent_id = self.create_agent(agent_type)

        agent = self._agents[agent_id]

        # Create task
        task = Task(
            description=task_description,
            goal=task_description,
            assigned_to=agent_id,
            timeout=self.config.default_timeout,
        )

        if use_background and self._background_manager:
            # Run in background with worktree isolation
            bg_task = await self._background_manager.submit(
                task=task,
                agent_factory=lambda: agent,
                use_worktree=True,
            )
            return bg_task.id

        # Run directly
        return await agent.run(task)

    async def execute_parallel(
        self,
        tasks: list[tuple[str, str]],  # (description, agent_type)
        return_results: bool = True,
    ) -> list[TaskResult] | list[str]:
        """Execute multiple tasks in parallel.

        Args:
            tasks: List of (description, agent_type) tuples.
            return_results: If True, wait for and return results.

        Returns:
            List of results or task IDs.
        """
        if self.config.enable_parallel:
            # Run truly in parallel
            coros = [
                self.execute(desc, agent_type, use_background=not return_results)
                for desc, agent_type in tasks
            ]
            results = await asyncio.gather(*coros, return_exceptions=True)

            # Convert exceptions to failed results
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append(
                        TaskResult(success=False, error=str(result))
                    )
                else:
                    processed_results.append(result)

            return processed_results

        # Sequential execution
        results = []
        for desc, agent_type in tasks:
            result = await self.execute(desc, agent_type, use_background=not return_results)
            results.append(result)
        return results

    async def delegate(
        self,
        subtasks: list[dict[str, Any]],  # {description, agent_type, dependencies}
    ) -> dict[str, TaskResult]:
        """Delegate subtasks to appropriate agents.

        Args:
            subtasks: List of subtask specifications.

        Returns:
            Map of subtask descriptions to results.
        """
        results = {}

        # Group by dependencies
        independent = [st for st in subtasks if not st.get("dependencies")]
        dependent = [st for st in subtasks if st.get("dependencies")]

        # Execute independent tasks first
        if independent:
            descriptions = [(st["description"], st.get("agent_type", "assistant"))
                           for st in independent]
            parallel_results = await self.execute_parallel(descriptions)

            for st, result in zip(independent, parallel_results):
                results[st["description"]] = result

        # Execute dependent tasks
        for subtask in dependent:
            # Check dependencies
            deps_satisfied = all(
                results.get(dep) and getattr(results.get(dep), "success", False)
                for dep in subtask.get("dependencies", [])
            )

            if deps_satisfied:
                result = await self.execute(
                    subtask["description"],
                    subtask.get("agent_type", "assistant"),
                )
                results[subtask["description"]] = result
            else:
                results[subtask["description"]] = TaskResult(
                    success=False,
                    error="Dependencies not satisfied",
                )

        return results

    async def send_message(
        self,
        from_agent: str,
        to_agent: str | None,  # None = broadcast
        content: Any,
        msg_type: MessageType = MessageType.NOTIFY,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> bool:
        """Send a message between agents.

        Args:
            from_agent: Sender agent ID.
            to_agent: Receiver agent ID (None for broadcast).
            content: Message content.
            msg_type: Type of message.
            priority: Message priority.

        Returns:
            True if sent successfully.
        """
        return await self._message_bus.send_immediate(
            sender=from_agent,
            receiver=to_agent,
            content=content,
            msg_type=msg_type,
            priority=priority,
        )

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status."""
        return {
            "id": self.id,
            "initialized": self._initialized,
            "agents": len(self._agents),
            "agent_types": list(set(a.role.name for a in self._agents.values())),
            "worktrees": self._worktree_manager.get_status(),
            "messaging": self._message_bus.get_stats(),
        }
