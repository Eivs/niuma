"""Agent factory for creating specialized agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from niuma.core.agent import AgentRole, AgentRuntime
from niuma.llm.client import LLMClient
from niuma.utils.logging import get_logger

if TYPE_CHECKING:
    from niuma.memory.manager import MemoryManager
    from niuma.protocol.team import TeamProtocol
    from niuma.tools.registry import ToolRegistry

logger = get_logger("niuma.agents.factory")


class AgentFactory:
    """Factory for creating different types of agents."""

    # Predefined roles for different agent types
    ROLES = {
        "research": AgentRole(
            name="research",
            description="Information gathering and analysis specialist",
            responsibilities=[
                "Search and gather information",
                "Read and analyze documents",
                "Summarize findings",
                "Identify relevant sources",
            ],
            skills=[
                "web_search",
                "document_reading",
                "data_extraction",
                "source_verification",
            ],
            system_prompt="""You are a research specialist. Your role is to gather,
            analyze, and synthesize information. You should:
            - Be thorough in your research
            - Verify sources when possible
            - Provide clear summaries
            - Note any uncertainties or gaps in information""",
        ),
        "code": AgentRole(
            name="code",
            description="Code writing and modification specialist",
            responsibilities=[
                "Write new code",
                "Modify existing code",
                "Refactor and optimize",
                "Implement features",
            ],
            skills=[
                "code_generation",
                "code_refactoring",
                "debugging",
                "testing",
            ],
            system_prompt="""You are a code specialist. Your role is to write,
            modify, and improve code. You should:
            - Write clean, maintainable code
            - Follow best practices and conventions
            - Consider edge cases
            - Write appropriate comments""",
        ),
        "test": AgentRole(
            name="test",
            description="Testing and validation specialist",
            responsibilities=[
                "Write unit tests",
                "Run test suites",
                "Identify bugs",
                "Verify functionality",
            ],
            skills=[
                "unit_testing",
                "integration_testing",
                "test_coverage",
                "bug_reporting",
            ],
            system_prompt="""You are a testing specialist. Your role is to ensure
            code quality through comprehensive testing. You should:
            - Write thorough test cases
            - Cover edge cases
            - Report bugs clearly
            - Verify fixes work correctly""",
        ),
        "review": AgentRole(
            name="review",
            description="Code review and quality analysis specialist",
            responsibilities=[
                "Review code changes",
                "Identify issues",
                "Suggest improvements",
                "Enforce standards",
            ],
            skills=[
                "code_review",
                "static_analysis",
                "security_review",
                "performance_analysis",
            ],
            system_prompt="""You are a code review specialist. Your role is to
            analyze code for quality, security, and best practices. You should:
            - Identify potential bugs
            - Suggest improvements
            - Check for security issues
            - Ensure consistency with standards""",
        ),
        "plan": AgentRole(
            name="plan",
            description="Architecture and planning specialist",
            responsibilities=[
                "Design system architecture",
                "Create implementation plans",
                "Analyze dependencies",
                "Estimate effort",
            ],
            skills=[
                "system_design",
                "dependency_analysis",
                "architecture_patterns",
                "effort_estimation",
            ],
            system_prompt="""You are a planning specialist. Your role is to design
            systems and create implementation plans. You should:
            - Consider scalability and maintainability
            - Identify dependencies and risks
            - Break down complex problems
            - Provide clear, actionable plans""",
        ),
        "explore": AgentRole(
            name="explore",
            description="Codebase exploration and understanding specialist",
            responsibilities=[
                "Explore codebases",
                "Find relevant files",
                "Understand dependencies",
                "Map code structure",
            ],
            skills=[
                "code_search",
                "dependency_tracking",
                "code_navigation",
                "pattern_recognition",
            ],
            system_prompt="""You are an exploration specialist. Your role is to
            understand and navigate codebases efficiently. You should:
            - Map out code structure
            - Identify key components
            - Find relevant files quickly
            - Understand relationships between components""",
        ),
        "assistant": AgentRole(
            name="assistant",
            description="General purpose assistant",
            responsibilities=[
                "Handle general tasks",
                "Coordinate with specialists",
                "Provide summaries",
                "Answer questions",
            ],
            skills=[
                "general_assistance",
                "summarization",
                "coordination",
            ],
            system_prompt="""You are a general purpose assistant. You should:
            - Be helpful and accurate
            - Delegate to specialists when appropriate
            - Provide clear, concise responses
            - Ask clarifying questions when needed""",
        ),
    }

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        tools: "ToolRegistry | None" = None,
        memory: "MemoryManager | None" = None,
    ) -> None:
        """Initialize the agent factory.

        Args:
            llm_client: Shared LLM client for all agents.
            tools: Shared tool registry.
            memory: Shared memory manager.
        """
        self.llm_client = llm_client
        self.tools = tools
        self.memory = memory
        self._custom_roles: dict[str, AgentRole] = {}

    def create(
        self,
        agent_type: str,
        agent_id: str | None = None,
        custom_role: AgentRole | None = None,
    ) -> AgentRuntime:
        """Create an agent of the specified type.

        Args:
            agent_type: Type of agent to create.
            agent_id: Optional custom agent ID.
            custom_role: Optional custom role configuration.

        Returns:
            Configured AgentRuntime instance.

        Raises:
            ValueError: If agent_type is not recognized.
        """
        # Get role
        if custom_role:
            role = custom_role
        elif agent_type in self.ROLES:
            role = self.ROLES[agent_type]
        elif agent_type in self._custom_roles:
            role = self._custom_roles[agent_type]
        else:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available: {list(self.ROLES.keys()) + list(self._custom_roles.keys())}"
            )

        # Create LLM client if not shared
        llm = self.llm_client
        if llm is None:
            llm = LLMClient()

        # Create agent
        return AgentRuntime(
            agent_id=agent_id,
            role=role,
            llm_client=llm,
            tools=self.tools,
            memory=self.memory,
        )

    def create_team(
        self,
        agent_types: list[str],
        protocol: "TeamProtocol | None" = None,
    ) -> dict[str, AgentRuntime]:
        """Create a team of agents.

        Args:
            agent_types: List of agent types to create.
            protocol: Optional team protocol configuration.

        Returns:
            Dictionary mapping agent IDs to agents.
        """
        team: dict[str, AgentRuntime] = {}

        for agent_type in agent_types:
            agent = self.create(agent_type)
            team[agent.id] = agent

        return team

    def register_role(self, name: str, role: AgentRole) -> None:
        """Register a custom agent role.

        Args:
            name: Role identifier.
            role: Role configuration.
        """
        self._custom_roles[name] = role

    def get_available_types(self) -> list[str]:
        """Get list of available agent types."""
        return list(self.ROLES.keys()) + list(self._custom_roles.keys())

    def get_role(self, agent_type: str) -> AgentRole | None:
        """Get the role definition for an agent type."""
        if agent_type in self.ROLES:
            return self.ROLES[agent_type]
        return self._custom_roles.get(agent_type)
