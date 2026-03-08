"""Code agent for writing and modifying code."""

from typing import Any

from niuma.core.agent import AgentRole, AgentRuntime
from niuma.llm.client import LLMClient
from niuma.utils.logging import get_logger

logger = get_logger("niuma.agents.code")


class CodeAgent(AgentRuntime):
    """Specialized agent for code tasks."""

    ROLE = AgentRole(
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
        system_prompt="""You are a code specialist. Write clean, maintainable code
        following best practices. Consider edge cases, write appropriate comments,
        and ensure the code is correct and efficient.""",
    )

    def __init__(
        self,
        agent_id: str | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        """Initialize code agent."""
        super().__init__(
            agent_id=agent_id,
            role=self.ROLE,
            llm_client=llm_client,
        )

    async def write_code(
        self,
        description: str,
        language: str,
        existing_code: str | None = None,
        tests: str | None = None,
    ) -> str:
        """Write code based on description.

        Args:
            description: What the code should do.
            language: Programming language.
            existing_code: Existing code context.
            tests: Test cases to satisfy.

        Returns:
            Generated code.
        """
        prompt = f"""Write {language} code for the following:

Description: {description}

{self._format_context(existing_code, tests)}

Requirements:
- Write clean, well-commented code
- Follow {language} best practices
- Handle edge cases appropriately
- Include docstrings/comments

Provide only the code (no explanations outside comments)."""

        try:
            return await self.llm.complete(prompt)
        except Exception as e:
            return f"# Error generating code: {e}\n# Please try again with more specific requirements"

    async def refactor(
        self,
        code: str,
        instructions: str,
        language: str,
    ) -> str:
        """Refactor code according to instructions.

        Args:
            code: Code to refactor.
            instructions: Refactoring instructions.
            language: Programming language.

        Returns:
            Refactored code.
        """
        prompt = f"""Refactor the following {language} code:

Instructions: {instructions}

Original code:
```
{code}
```

Provide only the refactored code."""

        try:
            return await self.llm.complete(prompt)
        except Exception as e:
            return f"# Refactoring failed: {e}\n{code}"

    async def review(
        self,
        code: str,
        language: str,
    ) -> dict[str, Any]:
        """Review code for issues.

        Args:
            code: Code to review.
            language: Programming language.

        Returns:
            Review results with issues and suggestions.
        """
        prompt = f"""Review the following {language} code:

```
{code}
```

Analyze for:
1. Bugs or logic errors
2. Code smells
3. Performance issues
4. Security concerns
5. Style violations

Return JSON format:
{{
    "issues": [{{"type": "bug|smell|performance|security|style", "line": N, "description": "..."}}],
    "suggestions": ["..."],
    "overall_score": 0-100
}}"""

        try:
            response = await self.llm.complete(prompt)
            import json
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {"error": "Review failed", "issues": [], "suggestions": []}

    async def explain(
        self,
        code: str,
        language: str | None = None,
    ) -> str:
        """Explain what code does.

        Args:
            code: Code to explain.
            language: Programming language (optional).

        Returns:
            Explanation of the code.
        """
        lang_hint = f" ({language})" if language else ""

        prompt = f"""Explain what the following code{lang_hint} does:

```
{code}
```

Provide a clear, concise explanation suitable for someone familiar with programming
but who may not know this specific codebase."""

        try:
            return await self.llm.complete(prompt)
        except Exception as e:
            return f"Explanation failed: {e}"

    def _format_context(
        self,
        existing_code: str | None,
        tests: str | None,
    ) -> str:
        """Format context section."""
        parts = []
        if existing_code:
            parts.append(f"Existing code:\n{existing_code}")
        if tests:
            parts.append(f"Test cases:\n{tests}")
        return "\n\n".join(parts) if parts else ""
