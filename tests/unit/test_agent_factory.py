"""Tests for agent factory."""

import pytest

from niuma.agents.factory import AgentFactory
from niuma.agents import CodeAgent, ResearchAgent


class TestAgentFactory:
    """Test agent factory."""

    def test_available_types(self):
        """Test listing available agent types."""
        factory = AgentFactory()
        types = factory.get_available_types()

        assert "code" in types
        assert "research" in types
        assert "test" in types
        assert "review" in types

    def test_create_agent(self):
        """Test creating an agent."""
        factory = AgentFactory()
        agent = factory.create("code")

        assert agent.role.name == "code"
        assert agent is not None

    def test_create_research_agent(self):
        """Test creating research agent."""
        factory = AgentFactory()
        agent = factory.create("research")

        assert agent.role.name == "research"
        assert "research" in agent.role.responsibilities[0].lower()

    def test_create_team(self):
        """Test creating a team."""
        factory = AgentFactory()
        team = factory.create_team(["research", "code", "test"])

        assert len(team) == 3
        assert all(a.role.name in ["research", "code", "test"] for a in team.values())
