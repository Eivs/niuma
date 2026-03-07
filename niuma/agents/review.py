"""Review agent for code review."""

from typing import Any

from niuma.core.agent import AgentRole, AgentRuntime
from niuma.llm.client import LLMClient


class ReviewAgent(AgentRuntime):
    """Specialized agent for code review."""

    ROLE = AgentRole(
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
        system_prompt="""You are a code review specialist. Analyze code for quality,
        security, and best practices. Be thorough but constructive. Identify potential
        bugs, suggest improvements, check for security issues, and ensure consistency.""",
    )

    def __init__(
        self,
        agent_id: str | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        """Initialize review agent."""
        super().__init__(
            agent_id=agent_id,
            role=self.ROLE,
            llm_client=llm_client,
        )

    async def review_code(
        self,
        code: str,
        language: str,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Perform comprehensive code review.

        Args:
            code: Code to review.
            language: Programming language.
            context: Additional context.

        Returns:
            Review results.
        """
        prompt = f"""Perform a comprehensive code review for the following {language} code.

{context if context else ""}

Code:
```
{code}
```

Review for:
1. Bugs/Logic errors
2. Code style/consistency
3. Performance issues
4. Security vulnerabilities
5. Documentation/comments
6. Maintainability

Return JSON format:
{{
    "summary": "brief overall assessment",
    "issues": [
        {{
            "type": "bug|style|performance|security|maintainability",
            "severity": "critical|high|medium|low",
            "line": line_number,
            "description": "detailed description",
            "suggestion": "how to fix"
        }}
    ],
    "praise": ["positive aspects"],
    "overall_score": 0-100
}}"""

        try:
            response = await self.llm.complete(prompt)
            import json
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                result = json.loads(match.group())
                return result
        except Exception:
            pass

        return {
            "summary": "Review failed",
            "issues": [],
            "praise": [],
            "overall_score": 0,
        }

    async def check_security(
        self,
        code: str,
        language: str,
    ) -> dict[str, Any]:
        """Security-focused review.

        Args:
            code: Code to check.
            language: Programming language.

        Returns:
            Security analysis.
        """
        prompt = f"""Perform a security review of this {language} code:

```
{code}
```

Check for:
- Input validation issues
- Injection vulnerabilities
- Authentication/authorization flaws
- Sensitive data exposure
- Cryptographic misuses
- Other security anti-patterns

Return security findings as JSON."""

        try:
            response = await self.llm.complete(prompt)
            import json
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {"vulnerabilities": [], "risk_level": "unknown"}

    async def check_performance(
        self,
        code: str,
        language: str,
    ) -> dict[str, Any]:
        """Performance-focused review.

        Args:
            code: Code to check.
            language: Programming language.

        Returns:
            Performance analysis.
        """
        prompt = f"""Analyze the performance characteristics of this {language} code:

```
{code}
```

Check for:
- Algorithmic complexity issues
- Unnecessary computations
- Memory efficiency
- I/O bottlenecks
- Concurrency issues

Return performance analysis as JSON."""

        try:
            response = await self.llm.complete(prompt)
            import json
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {"issues": [], "optimizations": []}
