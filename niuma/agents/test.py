"""Test agent for writing and running tests."""

from typing import Any

from niuma.core.agent import AgentRole, AgentRuntime
from niuma.llm.client import LLMClient


class TestAgent(AgentRuntime):
    """Specialized agent for testing tasks."""

    ROLE = AgentRole(
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
        system_prompt="""You are a testing specialist. Write thorough test cases
        that cover edge cases, verify functionality, and ensure code correctness.
        Report bugs clearly with reproduction steps and expected vs actual behavior.""",
    )

    def __init__(
        self,
        agent_id: str | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        """Initialize test agent."""
        super().__init__(
            agent_id=agent_id,
            role=self.ROLE,
            llm_client=llm_client,
        )

    async def write_tests(
        self,
        code: str,
        language: str,
        framework: str | None = None,
        coverage_target: str = "high",
    ) -> str:
        """Write tests for code.

        Args:
            code: Code to test.
            language: Programming language.
            framework: Test framework (optional).
            coverage_target: Coverage level target.

        Returns:
            Generated test code.
        """
        framework_hint = f" using {framework}" if framework else ""

        prompt = f"""Write comprehensive tests{framework_hint} for the following code:

```
{code}
```

Requirements:
- Target coverage: {coverage_target}
- Include positive and negative test cases
- Test edge cases and boundary conditions
- Use descriptive test names
- Follow {language} testing best practices

Provide only the test code."""

        try:
            return await self.llm.complete(prompt)
        except Exception as e:
            return f"# Test generation failed: {e}"

    async def analyze_coverage(
        self,
        code: str,
        tests: str,
        language: str,
    ) -> dict[str, Any]:
        """Analyze test coverage gaps.

        Args:
            code: Code being tested.
            tests: Existing tests.
            language: Programming language.

        Returns:
            Coverage analysis with gaps.
        """
        prompt = f"""Analyze test coverage for the following {language} code.

Code:
```
{code}
```

Tests:
```
{tests}
```

Identify:
1. What's being tested
2. What's NOT being tested (gaps)
3. Missing edge cases
4. Suggested additional tests

Return as JSON."""

        try:
            response = await self.llm.complete(prompt)
            import json
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {"error": "Analysis failed", "gaps": []}

    async def report_bug(
        self,
        code: str,
        observed_behavior: str,
        expected_behavior: str,
    ) -> dict[str, Any]:
        """Create a structured bug report.

        Args:
            code: Code with the bug.
            observed_behavior: What actually happens.
            expected_behavior: What should happen.

        Returns:
            Structured bug report.
        """
        prompt = f"""Analyze this bug and create a structured report.

Code:
```
{code}
```

Observed: {observed_behavior}
Expected: {expected_behavior}

Provide:
1. Bug severity (critical/high/medium/low)
2. Root cause analysis
3. Suggested fix
4. Prevention recommendations

Return as JSON."""

        try:
            response = await self.llm.complete(prompt)
            import json
            import re

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {
            "severity": "unknown",
            "description": observed_behavior,
            "expected": expected_behavior,
        }
