"""Skill system manager for Niuma."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

if TYPE_CHECKING:
    from niuma.core.agent import AgentRuntime


@dataclass
class SkillStep:
    """A single step in a skill."""

    action: str  # tool_call, think, delegate, etc.
    params: dict[str, Any] = field(default_factory=dict)
    condition: str | None = None  # Optional condition to evaluate


@dataclass
class Skill:
    """A reusable skill - sequence of steps to accomplish a task."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: list[SkillStep] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_rate: float = 1.0
    tags: list[str] = field(default_factory=list)
    author: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [
                {"action": s.action, "params": s.params, "condition": s.condition}
                for s in self.steps
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "tags": self.tags,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Skill":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            steps=[
                SkillStep(
                    action=s["action"],
                    params=s.get("params", {}),
                    condition=s.get("condition"),
                )
                for s in data.get("steps", [])
            ],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 1.0),
            tags=data.get("tags", []),
            author=data.get("author", ""),
        )


@dataclass
class SkillExecutionResult:
    """Result of skill execution."""

    success: bool
    skill_name: str
    steps_completed: int = 0
    total_steps: int = 0
    output: Any = None
    error: str | None = None


class SkillManager:
    """Manager for skills - reusable operation sequences."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize skill manager.

        Args:
            storage_path: Path to store skill definitions.
        """
        self.storage_path = storage_path or Path(".niuma/skills")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._skills: dict[str, Skill] = {}
        self._builtins: dict[str, Skill] = {}

        # Load builtins
        self._register_builtin_skills()

    def _register_builtin_skills(self) -> None:
        """Register built-in skills."""
        # Code review skill
        self._builtins["code_review"] = Skill(
            name="code_review",
            description="Perform a comprehensive code review",
            steps=[
                SkillStep(action="think", params={"content": "Analyzing code structure"}),
                SkillStep(action="tool_call", params={"tool": "review", "check": "bugs"}),
                SkillStep(action="tool_call", params={"tool": "review", "check": "style"}),
                SkillStep(action="tool_call", params={"tool": "review", "check": "security"}),
                SkillStep(action="think", params={"content": "Consolidating review results"}),
            ],
            tags=["code", "review", "quality"],
        )

        # Research skill
        self._builtins["research"] = Skill(
            name="research",
            description="Research a topic thoroughly",
            steps=[
                SkillStep(action="think", params={"content": "Planning research approach"}),
                SkillStep(action="tool_call", params={"tool": "search", "scope": "web"}),
                SkillStep(action="tool_call", params={"tool": "read", "source": "top_results"}),
                SkillStep(action="think", params={"content": "Synthesizing findings"}),
            ],
            tags=["research", "information"],
        )

        # Refactoring skill
        self._builtins["refactor"] = Skill(
            name="refactor",
            description="Refactor code safely",
            steps=[
                SkillStep(action="tool_call", params={"tool": "analyze", "target": "code"}),
                SkillStep(action="think", params={"content": "Planning refactoring steps"}),
                SkillStep(action="tool_call", params={"tool": "modify", "backup": True}),
                SkillStep(action="tool_call", params={"tool": "test", "scope": "affected"}),
            ],
            tags=["code", "refactoring"],
        )

    def register(
        self,
        skill: Skill,
        save: bool = True,
    ) -> None:
        """Register a skill.

        Args:
            skill: Skill to register.
            save: Whether to save to disk.
        """
        self._skills[skill.name] = skill

        if save:
            self._save_skill(skill)

    def _save_skill(self, skill: Skill) -> None:
        """Save skill to disk."""
        file_path = self.storage_path / f"{skill.name}.json"
        file_path.write_text(json.dumps(skill.to_dict(), indent=2))

    def load(self, name: str) -> Skill | None:
        """Load a skill by name.

        First checks registered skills, then builtins, then disk.

        Args:
            name: Skill name.

        Returns:
            Skill or None if not found.
        """
        # Check registered
        if name in self._skills:
            return self._skills[name]

        # Check builtins
        if name in self._builtins:
            return self._builtins[name]

        # Check disk
        file_path = self.storage_path / f"{name}.json"
        if file_path.exists():
            data = json.loads(file_path.read_text())
            skill = Skill.from_dict(data)
            self._skills[name] = skill
            return skill

        return None

    def list_skills(
        self,
        include_builtins: bool = True,
        tags: list[str] | None = None,
    ) -> list[Skill]:
        """List available skills.

        Args:
            include_builtins: Include built-in skills.
            tags: Filter by tags.

        Returns:
            List of skills.
        """
        skills = list(self._skills.values())

        if include_builtins:
            skills.extend(
                s for s in self._builtins.values() if s.name not in self._skills
            )

        # Load from disk
        for file_path in self.storage_path.glob("*.json"):
            name = file_path.stem
            if name not in [s.name for s in skills]:
                skill = self.load(name)
                if skill:
                    skills.append(skill)

        if tags:
            skills = [
                s for s in skills if any(tag in s.tags for tag in tags)
            ]

        return sorted(skills, key=lambda s: s.name)

    def find_similar(self, description: str, top_k: int = 3) -> list[tuple[Skill, float]]:
        """Find skills similar to description.

        Simple keyword matching - in production, use embeddings.

        Args:
            description: Task description.
            top_k: Number of results.

        Returns:
            List of (skill, similarity) tuples.
        """
        keywords = set(re.findall(r"\w+", description.lower()))

        scored = []
        for skill in self.list_skills():
            skill_text = f"{skill.name} {skill.description} {' '.join(skill.tags)}"
            skill_keywords = set(re.findall(r"\w+", skill_text.lower()))

            overlap = len(keywords & skill_keywords)
            score = overlap / max(len(keywords), 1)

            scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def execute(
        self,
        skill_name: str,
        agent: AgentRuntime,
        context: dict[str, Any] | None = None,
    ) -> SkillExecutionResult:
        """Execute a skill.

        Args:
            skill_name: Name of skill to execute.
            agent: Agent to execute with.
            context: Execution context variables.

        Returns:
            Execution result.
        """
        skill = self.load(skill_name)
        if not skill:
            return SkillExecutionResult(
                success=False,
                skill_name=skill_name,
                error=f"Skill not found: {skill_name}",
            )

        context = context or {}
        completed = 0

        try:
            for step in skill.steps:
                # Evaluate condition if present
                if step.condition:
                    # Simple string substitution for now
                    condition = step.condition
                    for key, value in context.items():
                        condition = condition.replace(f"{{{key}}}", str(value))

                # Execute step (simplified)
                if step.action == "think":
                    # Internal reasoning - skip for now
                    pass

                elif step.action == "tool_call":
                    # Would integrate with tools
                    pass

                elif step.action == "delegate":
                    # Would delegate to another agent
                    pass

                completed += 1

            skill.usage_count += 1
            skill.success_rate = (
                skill.success_rate * (skill.usage_count - 1) + 1.0
            ) / skill.usage_count

            return SkillExecutionResult(
                success=True,
                skill_name=skill.name,
                steps_completed=completed,
                total_steps=len(skill.steps),
            )

        except Exception as e:
            skill.usage_count += 1
            skill.success_rate = (
                skill.success_rate * (skill.usage_count - 1) + 0.0
            ) / skill.usage_count

            return SkillExecutionResult(
                success=False,
                skill_name=skill.name,
                steps_completed=completed,
                total_steps=len(skill.steps),
                error=str(e),
            )

    def delete(self, name: str) -> bool:
        """Delete a skill.

        Args:
            name: Skill name.

        Returns:
            True if deleted, False if not found or builtin.
        """
        # Can't delete builtins
        if name in self._builtins:
            return False

        # Remove from registry
        if name in self._skills:
            del self._skills[name]

        # Delete file
        file_path = self.storage_path / f"{name}.json"
        if file_path.exists():
            file_path.unlink()
            return True

        return False

    def get_stats(self) -> dict[str, Any]:
        """Get skill manager statistics."""
        return {
            "registered": len(self._skills),
            "builtins": len(self._builtins),
            "storage_path": str(self.storage_path),
        }

    def create_skill_from_execution(
        self,
        name: str,
        description: str,
        actions: list[dict[str, Any]],
        infer_patterns: bool = True,
    ) -> Skill:
        """Create a skill from successful execution history.

        Args:
            name: Skill name.
            description: Skill description.
            actions: List of executed actions.
            infer_patterns: Whether to infer reusable patterns.

        Returns:
            Created skill.
        """
        steps = [
            SkillStep(
                action=a.get("type", "tool_call"),
                params=a.get("params", {}),
            )
            for a in actions
        ]

        skill = Skill(
            name=name,
            description=description,
            steps=steps,
            tags=["learned"] if infer_patterns else [],
        )

        self.register(skill)
        return skill
