"""Agent runtime for Niuma."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

from niuma.core.cognitive import Action, CognitiveCore, Perception, Thought
from niuma.core.task import Task, TaskResult, TaskStatus
from niuma.utils.logging import get_logger

if TYPE_CHECKING:
    from niuma.llm.client import LLMClient
    from niuma.memory.manager import MemoryManager
    from niuma.tools.registry import ToolRegistry

logger = get_logger("niuma.core.agent")


class AgentState(Enum):
    """Agent execution state."""

    INITIALIZING = auto()
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    TERMINATED = auto()


@dataclass
class AgentRole:
    """Agent role configuration."""

    name: str
    description: str
    responsibilities: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    system_prompt: str = ""


@dataclass
class Message:
    """Message for inter-agent communication."""

    sender: str
    receiver: str
    content: Any
    msg_type: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)


MessageHandler = Callable[[Message], None]


class Agent(ABC):
    """Abstract base class for Agents."""

    def __init__(
        self,
        agent_id: str | None = None,
        role: AgentRole | None = None,
    ) -> None:
        """Initialize agent."""
        self._id = agent_id or str(uuid4())
        self._role = role or AgentRole(name="generic", description="Generic agent")
        self._state = AgentState.INITIALIZING
        self._message_handlers: list[MessageHandler] = []

    @property
    def id(self) -> str:
        """Agent unique ID."""
        return self._id

    @property
    def role(self) -> AgentRole:
        """Agent role."""
        return self._role

    @property
    def state(self) -> AgentState:
        """Current state."""
        return self._state

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize agent with configuration."""
        pass

    @abstractmethod
    async def run(self, task: Task) -> TaskResult:
        """Execute a task."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Pause execution."""
        pass

    @abstractmethod
    def resume(self) -> None:
        """Resume execution."""
        pass

    @abstractmethod
    async def terminate(self) -> None:
        """Terminate agent."""
        pass

    def send_message(self, to: str, content: Any, msg_type: str = "default") -> None:
        """Send a message to another agent."""
        message = Message(
            sender=self._id,
            receiver=to,
            content=content,
            msg_type=msg_type,
        )
        # Message delivery would be handled by a message bus/coordinator
        # For now, this is a placeholder

    def on_message(self, handler: MessageHandler) -> None:
        """Register a message handler."""
        self._message_handlers.append(handler)

    def handle_message(self, message: Message) -> None:
        """Handle incoming message."""
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception:
                pass  # Log error but continue


class AgentRuntime(Agent):
    """Runtime for executing Agent with cognitive capabilities."""

    def __init__(
        self,
        agent_id: str | None = None,
        role: AgentRole | None = None,
        llm_client: LLMClient | None = None,
        tools: "ToolRegistry | None" = None,
        memory: "MemoryManager | None" = None,
    ) -> None:
        """Initialize agent runtime."""
        super().__init__(agent_id, role)
        self.llm = llm_client
        self.tools = tools
        self.memory = memory
        self.cognitive_core = CognitiveCore(llm_client) if llm_client else None

        # Runtime state
        self._state = AgentState.IDLE
        self._current_task: Task | None = None
        self._task_future: asyncio.Future | None = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start not paused

        # Execution tracking
        self._actions_taken: list[Action] = []
        self._results: list[Any] = []
        self._max_iterations = 50  # Prevent infinite loops

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the runtime."""
        self._state = AgentState.INITIALIZING

        # Initialize components
        if self.tools and hasattr(self.tools, "initialize"):
            await self.tools.initialize(config.get("tools", {}))

        if self.memory and hasattr(self.memory, "initialize"):
            await self.memory.initialize(config.get("memory", {}))

        self._state = AgentState.IDLE

    async def run(self, task: Task) -> TaskResult:
        """Execute a task using the cognitive loop."""
        if self._state == AgentState.TERMINATED:
            return TaskResult(
                success=False,
                error="Agent has been terminated",
            )

        self._current_task = task
        self._state = AgentState.RUNNING
        task.mark_started()

        if not self.cognitive_core:
            # No cognitive capabilities - simple execution
            return await self._simple_execute(task)

        try:
            # Main cognitive loop: Perceive -> Think -> Act -> Reflect
            for iteration in range(self._max_iterations):
                # Wait if paused
                await self._pause_event.wait()

                # Check if terminated
                if self._state == AgentState.TERMINATED:
                    return TaskResult(
                        success=False,
                        error="Agent was terminated during execution",
                    )

                # 1. Perceive
                perception = await self._perceive()

                # 2. Think
                thought = await self.cognitive_core.think(perception)

                # 3. Act
                if not thought.proposed_actions:
                    # No more actions needed
                    break

                action = thought.proposed_actions[0]
                result = await self._execute_action(action)

                self._actions_taken.append(action)
                self._results.append(result)

                # Check for completion
                if action.type == "complete":
                    return TaskResult(
                        success=True,
                        output=result,
                        metadata={
                            "iterations": iteration + 1,
                            "actions_count": len(self._actions_taken),
                        },
                    )

                # 4. Reflect (every few iterations or on failure)
                if iteration % 5 == 0 or not result:
                    evaluation = await self.cognitive_core.evaluate_progress(
                        goal=task.goal or task.description,
                        current_state=str(result)[:500],  # Limit size
                        actions_taken=self._actions_taken,
                        results=self._results,
                    )

                    if not evaluation.is_on_track and evaluation.deviation_score > 0.7:
                        # Significant deviation - might need to adjust
                        pass  # Strategy adjustment handled in next think cycle

            # Max iterations reached
            return TaskResult(
                success=False,
                error=f"Max iterations ({self._max_iterations}) reached",
                metadata={
                    "actions_count": len(self._actions_taken),
                },
            )

        except asyncio.TimeoutError:
            return TaskResult(
                success=False,
                error=f"Task timed out after {task.timeout}s",
            )

        except Exception as e:
            return TaskResult(
                success=False,
                error=str(e),
                metadata={
                    "actions_count": len(self._actions_taken),
                },
            )

        finally:
            self._state = AgentState.IDLE
            self._current_task = None

    async def _simple_execute(self, task: Task) -> TaskResult:
        """Simple execution without cognitive capabilities."""
        # Basic implementation - subclass should override
        return TaskResult(
            success=False,
            error="No cognitive core or LLM client configured",
        )

    async def _perceive(self) -> Perception:
        """Perceive the current state."""
        available_tools = []
        if self.tools:
            available_tools = [
                tool_name
                for tool_name in dir(self.tools)
                if not tool_name.startswith("_")
            ]

        context = {}
        if self.memory:
            # Could retrieve relevant context from memory
            pass

        return Perception(
            task_description=self._current_task.description if self._current_task else "",
            current_state=str(self._results[-1]) if self._results else "Starting",
            available_tools=available_tools,
            previous_actions=self._actions_taken[-5:],  # Last 5
            context=context,
        )

    async def _execute_action(self, action: Action) -> Any:
        """Execute a single action."""
        if action.type == "think":
            # Internal thinking - just return the thought
            return action.params.get("thought", "")

        elif action.type == "complete":
            # Task completion
            return action.params.get("result", "")

        elif action.type == "tool":
            # Execute tool
            if not self.tools:
                return "Error: No tools available"

            tool_name = action.params.get("tool_name")
            tool_input = action.params.get("tool_input", {})

            try:
                # This assumes tools have async execute methods
                tool = getattr(self.tools, tool_name, None)
                if tool and callable(tool):
                    return await tool(**tool_input)
                return f"Error: Tool '{tool_name}' not found"
            except Exception as e:
                return f"Error executing tool: {e}"

        elif action.type == "delegate":
            # Delegate to another agent (would need orchestrator)
            return "Delegation not yet implemented"

        else:
            return f"Unknown action type: {action.type}"

    def pause(self) -> None:
        """Pause execution."""
        if self._state == AgentState.RUNNING:
            self._state = AgentState.PAUSED
            self._pause_event.clear()

    def resume(self) -> None:
        """Resume execution."""
        if self._state == AgentState.PAUSED:
            self._state = AgentState.RUNNING
            self._pause_event.set()

    async def terminate(self) -> None:
        """Terminate the agent."""
        self._state = AgentState.TERMINATED
        self._pause_event.set()  # Release any paused waits

        if self._current_task and self._current_task.status == TaskStatus.IN_PROGRESS:
            self._current_task.mark_cancelled()

        # Cleanup
        if self.tools and hasattr(self.tools, "cleanup"):
            await self.tools.cleanup()

        if self.memory and hasattr(self.memory, "cleanup"):
            await self.memory.cleanup()

    def reset(self) -> None:
        """Reset agent for new task."""
        self._actions_taken.clear()
        self._results.clear()
        if self.cognitive_core:
            self.cognitive_core.clear_memory()
        self._state = AgentState.IDLE
