"""Research agent for information gathering."""

from dataclasses import dataclass
from typing import Any

from niuma.core.agent import AgentRole, AgentRuntime
from niuma.llm.client import LLMClient


@dataclass
class ResearchResult:
    """Result of research."""

    query: str
    findings: list[str]
    sources: list[str]
    summary: str
    confidence: float = 0.8


class ResearchAgent(AgentRuntime):
    """Specialized agent for research tasks."""

    ROLE = AgentRole(
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
        analyze, and synthesize information. Be thorough in your research,
        verify sources when possible, provide clear summaries, and note any
        uncertainties or gaps in information.""",
    )

    def __init__(
        self,
        agent_id: str | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        """Initialize research agent."""
        super().__init__(
            agent_id=agent_id,
            role=self.ROLE,
            llm_client=llm_client,
        )

    async def research(
        self,
        query: str,
        context: str | None = None,
        depth: str = "medium",  # shallow, medium, deep
    ) -> ResearchResult:
        """Perform research on a topic.

        Args:
            query: Research query.
            context: Additional context.
            depth: Research depth.

        Returns:
            Research results.
        """
        # This is a simplified implementation
        # In production, would integrate with search APIs, document readers, etc.

        prompt = f"""Research the following topic in detail:

Query: {query}

Context: {context or "None provided"}

Research depth: {depth}

Please provide:
1. Key findings (3-5 bullet points)
2. Relevant sources you would consult
3. A concise summary
4. Confidence level (0.0-1.0)

Format as JSON:
{{
    "findings": ["...", "..."],
    "sources": ["...", "..."],
    "summary": "...",
    "confidence": 0.8
}}"""

        try:
            response = await self.llm.complete(prompt)
            # Parse response
            import json
            import re

            # Try to extract JSON
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return ResearchResult(
                    query=query,
                    findings=data.get("findings", []),
                    sources=data.get("sources", []),
                    summary=data.get("summary", ""),
                    confidence=data.get("confidence", 0.8),
                )
        except Exception:
            pass

        # Fallback
        return ResearchResult(
            query=query,
            findings=["Research completed with basic information"],
            sources=[],
            summary="Research on " + query,
            confidence=0.5,
        )

    async def summarize(
        self,
        content: str,
        max_length: int = 200,
    ) -> str:
        """Summarize content.

        Args:
            content: Content to summarize.
            max_length: Maximum length of summary.

        Returns:
            Summarized content.
        """
        prompt = f"""Summarize the following content in {max_length} characters or less:

{content}

Summary:"""

        try:
            return await self.llm.complete(prompt)
        except Exception as e:
            return f"Summary failed: {e}"

    async def analyze(
        self,
        content: str,
        aspects: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze content.

        Args:
            content: Content to analyze.
            aspects: Aspects to analyze.

        Returns:
            Analysis results.
        """
        aspects = aspects or ["key points", "sentiment", "topics"]

        prompt = f"""Analyze the following content for these aspects: {', '.join(aspects)}

Content:
{content}

Provide analysis as JSON."""

        try:
            response = await self.llm.complete(prompt)
            import json
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {"error": "Analysis failed"}
