"""Worktree isolation system for Niuma.

Provides task-level Git worktree isolation for safe concurrent execution.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from git import Repo

from niuma.config import get_settings


@dataclass
class WorktreeInfo:
    """Information about a worktree."""

    id: str
    path: Path
    task_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime | None = None
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "path": str(self.path),
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


class WorktreeManager:
    """Manages Git worktrees for task isolation."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize worktree manager.

        Args:
            base_path: Base directory for worktrees. If None, uses config.
        """
        settings = get_settings()
        self.base_path = base_path or settings.worktree.base_path
        self.max_worktrees = settings.worktree.max_worktrees
        self.auto_cleanup = settings.worktree.auto_cleanup

        self._worktrees: dict[str, WorktreeInfo] = {}
        self._repo: Repo | None = None
        self._lock_file = self.base_path / ".worktree_locks"

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_main_repo(self) -> Repo:
        """Get or find the main Git repository."""
        if self._repo is None:
            # Try to find repo from current directory
            try:
                self._repo = Repo(search_parent_directories=True)
            except Exception as e:
                raise RuntimeError("No Git repository found") from e

        return self._repo

    def create_worktree(
        self,
        task_id: str | None = None,
        branch: str | None = None,
        from_commit: str | None = None,
    ) -> WorktreeInfo:
        """Create a new worktree for task isolation.

        Args:
            task_id: Optional task ID to associate with worktree.
            branch: Branch to checkout. If None, creates detached HEAD.
            from_commit: Commit SHA to checkout from. Creates detached HEAD.

        Returns:
            WorktreeInfo for the created worktree.

        Raises:
            RuntimeError: If max worktrees exceeded or creation fails.
        """
        # Check limit
        active_count = sum(1 for wi in self._worktrees.values() if wi.is_active)
        if active_count >= self.max_worktrees:
            if self.auto_cleanup:
                self._cleanup_oldest_inactive()
            else:
                raise RuntimeError(f"Max worktrees ({self.max_worktrees}) exceeded")

        # Generate worktree ID
        worktree_id = str(uuid4())[:8]
        worktree_path = self.base_path / f"wt_{worktree_id}"

        # Create worktree using git command
        repo = self._get_main_repo()

        try:
            if branch:
                # Checkout existing or new branch
                cmd = ["git", "worktree", "add", str(worktree_path), branch]
            elif from_commit:
                # Detached HEAD at specific commit
                cmd = [
                    "git", "worktree", "add", "--detach",
                    str(worktree_path), from_commit,
                ]
            else:
                # Detached HEAD at current HEAD
                cmd = ["git", "worktree", "add", "--detach", str(worktree_path)]

            subprocess.run(
                cmd,
                cwd=repo.working_dir,
                check=True,
                capture_output=True,
                text=True,
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create worktree: {e.stderr}") from e

        # Create worktree info
        info = WorktreeInfo(
            id=worktree_id,
            path=worktree_path,
            task_id=task_id,
        )

        self._worktrees[worktree_id] = info

        # Add .gitignore to worktree
        gitignore_path = worktree_path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("# Niuma worktree\n.niuma/\n")

        return info

    def get_worktree(self, worktree_id: str) -> WorktreeInfo | None:
        """Get worktree by ID."""
        return self._worktrees.get(worktree_id)

    def get_worktree_for_task(self, task_id: str) -> WorktreeInfo | None:
        """Find worktree associated with a task."""
        for info in self._worktrees.values():
            if info.task_id == task_id:
                return info
        return None

    def list_worktrees(self, active_only: bool = False) -> list[WorktreeInfo]:
        """List all worktrees.

        Args:
            active_only: If True, only return active worktrees.

        Returns:
            List of worktree info objects.
        """
        worktrees = list(self._worktrees.values())
        if active_only:
            worktrees = [w for w in worktrees if w.is_active]
        return worktrees

    def mark_inactive(self, worktree_id: str) -> None:
        """Mark a worktree as inactive (task completed)."""
        info = self._worktrees.get(worktree_id)
        if info:
            info.is_active = False
            info.last_used = datetime.now()

            if self.auto_cleanup:
                self._cleanup_if_needed()

    def remove_worktree(self, worktree_id: str, force: bool = False) -> bool:
        """Remove a worktree.

        Args:
            worktree_id: ID of worktree to remove.
            force: If True, remove even if active.

        Returns:
            True if removed, False if not found or active (without force).
        """
        info = self._worktrees.get(worktree_id)
        if not info:
            return False

        if info.is_active and not force:
            return False

        try:
            # Remove worktree using git command
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(info.path)],
                cwd=self._get_main_repo().working_dir,
                check=True,
                capture_output=True,
            )

        except subprocess.CalledProcessError as e:
            # Fallback: manual cleanup
            if info.path.exists():
                shutil.rmtree(info.path, ignore_errors=True)

        del self._worktrees[worktree_id]
        return True

    def cleanup_all(self, force: bool = False) -> int:
        """Remove all worktrees.

        Args:
            force: If True, removes active worktrees too.

        Returns:
            Number of worktrees removed.
        """
        count = 0
        for worktree_id in list(self._worktrees.keys()):
            if self.remove_worktree(worktree_id, force=force):
                count += 1
        return count

    def _cleanup_oldest_inactive(self) -> None:
        """Remove oldest inactive worktree if over limit."""
        inactive = [
            wi for wi in self._worktrees.values()
            if not wi.is_active and wi.last_used
        ]

        if inactive:
            # Sort by last used, oldest first
            inactive.sort(key=lambda w: w.last_used or datetime.min)
            oldest = inactive[0]
            self.remove_worktree(oldest.id, force=False)

    def _cleanup_if_needed(self) -> None:
        """Cleanup worktrees if over limit."""
        while len(self._worktrees) > self.max_worktrees:
            self._cleanup_oldest_inactive()

    def write_file(
        self,
        worktree_id: str,
        relative_path: str,
        content: str,
    ) -> Path:
        """Write a file in the worktree.

        Args:
            worktree_id: Target worktree ID.
            relative_path: Path relative to worktree root.
            content: File content.

        Returns:
            Absolute path to written file.
        """
        info = self._worktrees.get(worktree_id)
        if not info:
            raise ValueError(f"Worktree {worktree_id} not found")

        file_path = info.path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

        return file_path

    def read_file(
        self,
        worktree_id: str,
        relative_path: str,
    ) -> str:
        """Read a file from the worktree.

        Args:
            worktree_id: Source worktree ID.
            relative_path: Path relative to worktree root.

        Returns:
            File content as string.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        info = self._worktrees.get(worktree_id)
        if not info:
            raise ValueError(f"Worktree {worktree_id} not found")

        file_path = info.path / relative_path
        return file_path.read_text()

    def list_files(
        self,
        worktree_id: str,
        pattern: str = "*",
    ) -> list[Path]:
        """List files in the worktree.

        Args:
            worktree_id: Target worktree ID.
            pattern: Glob pattern to match files.

        Returns:
            List of file paths (relative to worktree root).
        """
        info = self._worktrees.get(worktree_id)
        if not info:
            raise ValueError(f"Worktree {worktree_id} not found")

        files = info.path.rglob(pattern)
        return [f.relative_to(info.path) for f in files if f.is_file()]

    def get_status(self) -> dict[str, Any]:
        """Get worktree manager status."""
        active = sum(1 for w in self._worktrees.values() if w.is_active)
        inactive = len(self._worktrees) - active

        return {
            "total": len(self._worktrees),
            "active": active,
            "inactive": inactive,
            "max": self.max_worktrees,
            "base_path": str(self.base_path),
            "auto_cleanup": self.auto_cleanup,
        }

    def __enter__(self) -> WorktreeManager:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - cleanup if needed."""
        if self.auto_cleanup:
            self.cleanup_all(force=False)
