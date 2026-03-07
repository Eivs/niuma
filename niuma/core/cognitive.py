"""Cognitive engine for Niuma - Chain of Thought and Reflection."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from niuma.llm.client import LLMClient


@dataclass
class ReasoningResult:
    """Result of chain-of-thought reasoning."""

    subtasks: list[str]
    plan: str
    confidence: float
    reasoning: str = ""


@dataclass
class Evaluation:
    """Evaluation of current state vs goal."""

    is_on_track: bool
    deviation_score: float  # 0.0 = perfect, 1.0 = completely off track
    suggestions: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)


@dataclass
class Strategy:
    """Strategy adjustment based on reflection."""

    next_actions: list[str]
    adjusted_plan: str | None = None
    priority_changes: dict[str, int] = field(default_factory=dict)


@dataclass
class SubTask:
    """A subtask generated from task decomposition."""

    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    estimated_difficulty: int = 1  # 1-10
    tools_needed: list[str] = field(default_factory=list)


@dataclass
class Action:
    """An action to be executed."""

    type: str  # tool, think, complete, delegate
    params: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class Perception:
    """What the agent perceives from the environment."""

    task_description: str = ""
    current_state: str = ""
    available_tools: list[str] = field(default_factory=list)
    previous_actions: list[Action] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class Thought:
    """Agent's thinking process."""

    analysis: str = ""
    reasoning: str = ""
    proposed_actions: list[Action] = field(default_factory=list)
    confidence: float = 0.5


class ChainOfThought:
    """Chain of Thought reasoning for task decomposition and planning."""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize with LLM client."""
        self.llm = llm_client

    async def decompose(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> list[SubTask]:
        """Decompose a complex task into subtasks."""
        context_str = json.dumps(context, indent=2) if context else "None"

        prompt = f"""Analyze and decompose the following task into clear, actionable subtasks.

Task: {task}

Context: {context_str}

Requirements:
1. Break down into 2-8 subtasks based on complexity
2. Each subtask should be atomic and self-contained
3. Identify dependencies between subtasks
4. Estimate difficulty (1-10 scale)
5. List tools that might be needed

Respond in the following JSON format:
{{
    "reasoning": "<explain your decomposition approach>",
    "subtasks": [
        {{
            "id": "subtask_1",
            "description": "<clear description>",
            "dependencies": ["<ids of prerequisite subtasks>"],
            "estimated_difficulty": <1-10>,
            "tools_needed": ["<tool names>"]
        }}
    ]
}}

If the task is simple and atomic, return a single subtask with the task description."""

        response = await self.llm.complete(prompt)

        try:
            # Try to extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            subtasks = []
            for i, st_data in enumerate(data.get("subtasks", [])):
                subtasks.append(
                    SubTask(
                        id=st_data.get("id", f"subtask_{i}"),
                        description=st_data["description"],
                        dependencies=st_data.get("dependencies", []),
                        estimated_difficulty=st_data.get("estimated_difficulty", 5),
                        tools_needed=st_data.get("tools_needed", []),
                    )
                )
            return subtasks

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: create single subtask
            return [
                SubTask(
                    id="subtask_1",
                    description=task,
                    dependencies=[],
                    estimated_difficulty=5,
                    tools_needed=[],
                )
            ]

    async def plan(
        self,
        subtasks: list[SubTask],
        goal: str,
    ) -> str:
        """Create an execution plan for subtasks."""
        subtasks_str = ""
        for st in subtasks:
            subtasks_str += f"- {st.id}: {st.description} (difficulty: {st.estimated_difficulty}, deps: {st.dependencies})\n"  # noqa: E501

        prompt = f"""Create an optimal execution plan for the following subtasks.

Goal: {goal}

Subtasks:
{subtasks_str}

Consider:
1. Execute independent subtasks in parallel when possible
2. Respect dependency order
3. Balance workload across stages
4. Identify critical path

Provide a concise execution plan with steps and reasoning."""

        return await self.llm.complete(prompt)

    async def reason(
        self,
        perception: Perception,
    ) -> Thought:
        """Reason about what to do next."""
        tools_str = ", ".join(perception.available_tools)
        prev_actions_str = ""
        for action in perception.previous_actions[-3:]:  # Last 3 actions
            prev_actions_str += f"- {action.type}: {action.params}\n"

        prompt = f"""You are an AI Agent. Based on your perception, decide what to do next.

## Task
{perception.task_description}

## Current State
{perception.current_state}

## Available Tools
{tools_str}

## Recent Actions
{prev_actions_str}

## Instructions
1. Analyze the current situation
2. Reason about what needs to be done
3. Propose the next action(s)

Respond in JSON format:
{{
    "analysis": "<current situation analysis>",
    "reasoning": "<detailed reasoning for next steps>",
    "proposed_actions": [
        {{
            "type": "<tool|think|complete|delegate>",
            "params": {{<action parameters>}},
            "reasoning": "<why this action>"
        }}
    ],
    "confidence": <0.0-1.0>
}}

Action types:
- tool: Use a tool (params: tool_name, tool_input)
- think: Internal reasoning/thinking (params: thought)
- complete: Mark task as complete (params: result)
- delegate: Assign to another agent (params: agent_type, subtask)"""

        response = await self.llm.complete(prompt)

        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            actions = [
                Action(
                    type=a["type"],
                    params=a.get("params", {}),
                    reasoning=a.get("reasoning", ""),
                )
                for a in data.get("proposed_actions", [])
            ]

            return Thought(
                analysis=data.get("analysis", ""),
                reasoning=data.get("reasoning", ""),
                proposed_actions=actions,
                confidence=data.get("confidence", 0.5),
            )

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: simple thought
            return Thought(
                analysis="Unable to parse reasoning",
                reasoning=str(e),
                proposed_actions=[Action(type="think", params={"error": str(e)})],
                confidence=0.1,
            )

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that may contain markdown or other content."""
        # Try finding JSON block
        match = re.search(r"```json\s*(\{.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        # Try finding JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        return text


class Reflection:
    """Reflection mechanism for self-improvement."""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize with LLM client."""
        self.llm = llm_client

    async def evaluate(
        self,
        goal: str,
        current_state: str,
        actions_taken: list[Action],
        results: list[Any],
    ) -> Evaluation:
        """Evaluate progress towards the goal."""
        actions_str = ""
        for i, action in enumerate(actions_taken[-5:]):  # Last 5 actions
            actions_str += f"{i + 1}. {action.type}: {action.params}\n"
        results_str = ""
        for i, result in enumerate(results[-5:]):
            results_str += f"{i + 1}. {result}\n"

        prompt = f"""Evaluate the progress towards the goal.
## Goal
{goal}

## Current State
{current_state}

## Actions Taken (last 5)
{actions_str}

## Results
{results_str}

## Evaluation Criteria
1. Are we making progress towards the goal?
2. Is the current approach working?
3. Are there any issues or concerns?
4. What adjustments might be needed?

Respond in JSON format:
{{
    "is_on_track": <true|false>,
    "deviation_score": <0.0-1.0>,
    "suggestions": ["<suggestion 1>", "<suggestion 2>"],
    "concerns": ["<concern 1>", "<concern 2>"]
}}"""

        response = await self.llm.complete(prompt)

        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            return Evaluation(
                is_on_track=data.get("is_on_track", True),
                deviation_score=data.get("deviation_score", 0.0),
                suggestions=data.get("suggestions", []),
                concerns=data.get("concerns", []),
            )

        except (json.JSONDecodeError, KeyError):
            return Evaluation(
                is_on_track=True,
                deviation_score=0.0,
                suggestions=[],
                concerns=[],
            )

    async def detect_deviation(
        self,
        planned: str,
        actual: str,
    ) -> list[str]:
        """Detect deviations between planned and actual execution."""
        prompt = f"""Compare the planned execution with the actual execution.

## Planned
{planned}

## Actual
{actual}

Identify any deviations and explain why they occurred.

Respond with a list of deviations in JSON format:
{{
    "deviations": ["<deviation 1>", "<deviation 2>"]
}}"""

        response = await self.llm.complete(prompt)

        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            return data.get("deviations", [])
        except (json.JSONDecodeError, KeyError):
            return []

    async def adjust_strategy(
        self,
        evaluation: Evaluation,
        current_plan: str,
    ) -> Strategy:
        """Adjust strategy based on evaluation."""
        suggestions_str = ""
        for s in evaluation.suggestions:
            suggestions_str += f"- {s}\n"

        concerns_str = ""
        for c in evaluation.concerns:
            concerns_str += f"- {c}\n"

        if evaluation.is_on_track and not evaluation.suggestions:
            # No change needed
            return Strategy(
                next_actions=["continue with current plan"],
                adjusted_plan=None,
            )

        prompt = f"""Based on the evaluation, adjust the strategy.

## Current Plan
{current_plan}

## Evaluation
On track: {evaluation.is_on_track}
Deviation score: {evaluation.deviation_score}

## Suggestions
{suggestions_str}

## Concerns
{concerns_str}

Respond in JSON format:
{{
    "next_actions": ["<action 1>", "<action 2>"],
    "adjusted_plan": "<if needed, describe the adjusted plan, otherwise null>",
    "priority_changes": {{"<task_id>": <new_priority>}}
}}"""

        response = await self.llm.complete(prompt)

        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            return Strategy(
                next_actions=data.get("next_actions", []),
                adjusted_plan=data.get("adjusted_plan"),
                priority_changes=data.get("priority_changes", {}),
            )

        except (json.JSONDecodeError, KeyError):
            return Strategy(
                next_actions=["continue with current plan"],
                adjusted_plan=None,
            )

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text."""
        match = re.search(r"```json\s*(\{.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        return text


class CognitiveCore:
    """Core cognitive engine combining CoT and Reflection."""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize cognitive core."""
        self.llm = llm_client
        self.cot = ChainOfThought(llm_client)
        self.reflection = Reflection(llm_client)

        # Working memory
        self.working_memory: dict[str, Any] = {}
        self.reasoning_history: list[Thought] = []
        self.evaluation_history: list[Evaluation] = []

    def remember(self, key: str, value: Any) -> None:
        """Store in working memory."""
        self.working_memory[key] = value

    def recall(self, key: str) -> Any:
        """Retrieve from working memory."""
        return self.working_memory.get(key)

    def clear_memory(self) -> None:
        """Clear working memory."""
        self.working_memory.clear()
        self.reasoning_history.clear()
        self.evaluation_history.clear()

    async def think(
        self,
        perception: Perception,
    ) -> Thought:
        """Think about what to do next."""
        thought = await self.cot.reason(perception)
        self.reasoning_history.append(thought)
        return thought

    async def evaluate_progress(
        self,
        goal: str,
        current_state: str,
        actions_taken: list[Action],
        results: list[Any],
    ) -> Evaluation:
        """Evaluate current progress."""
        evaluation = await self.reflection.evaluate(goal, current_state, actions_taken, results)
        self.evaluation_history.append(evaluation)
        return evaluation

    async def decompose_task(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> list[SubTask]:
        """Decompose a complex task."""
        return await self.cot.decompose(task, context)
