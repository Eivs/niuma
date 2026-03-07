"""Short-term memory management for Niuma."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from niuma.config import get_settings


@dataclass
class MemoryEntry:
    """A single memory entry."""

    key: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 1.0  # 0.0 to 1.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
        }


class ShortTermMemory:
    """Short-term memory with sliding window and compression."""

    def __init__(
        self,
        window_size: int | None = None,
        compression_threshold: int | None = None,
    ) -> None:
        """Initialize short-term memory.

        Args:
            window_size: Maximum number of entries to keep.
            compression_threshold: When to trigger compression.
        """
        settings = get_settings()
        self.window_size = window_size or settings.memory.stm_window_size
        self.compression_threshold = (
            compression_threshold or settings.memory.stm_compression_threshold
        )

        self._entries: dict[str, MemoryEntry] = {}
        self._access_order: deque[str] = deque(maxlen=self.window_size * 2)
        self._compressed_summary: str | None = None

    def store(
        self,
        key: str,
        value: Any,
        importance: float = 1.0,
    ) -> None:
        """Store a value in short-term memory.

        Args:
            key: Memory key.
            value: Value to store.
            importance: Importance score (0.0-1.0).
        """
        # Check if we need to compress
        if len(self._entries) >= self.compression_threshold:
            self._compress()

        # Remove old entry if exists
        if key in self._entries:
            self._access_order.remove(key)

        # Add new entry
        entry = MemoryEntry(
            key=key,
            value=value,
            importance=importance,
        )
        self._entries[key] = entry
        self._access_order.append(key)

        # Enforce window size
        self._enforce_window()

    def retrieve(self, key: str) -> Any | None:
        """Retrieve a value from short-term memory.

        Args:
            key: Memory key.

        Returns:
            Stored value or None if not found.
        """
        entry = self._entries.get(key)
        if entry:
            entry.touch()
            return entry.value
        return None

    def retrieve_recent(self, n: int = 5) -> list[tuple[str, Any]]:
        """Retrieve the n most recent entries.

        Args:
            n: Number of entries to retrieve.

        Returns:
            List of (key, value) tuples, most recent first.
        """
        recent_keys = list(self._access_order)[-n:]
        return [
            (key, self._entries[key].value)
            for key in reversed(recent_keys)
            if key in self._entries
        ]

    def retrieve_important(self, n: int = 5) -> list[tuple[str, Any]]:
        """Retrieve the n most important entries.

        Args:
            n: Number of entries to retrieve.

        Returns:
            List of (key, value) tuples, sorted by importance.
        """
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: (e.importance, e.access_count),
            reverse=True,
        )
        return [(e.key, e.value) for e in sorted_entries[:n]]

    def update_importance(self, key: str, importance: float) -> bool:
        """Update the importance of an entry.

        Args:
            key: Memory key.
            importance: New importance value.

        Returns:
            True if updated, False if not found.
        """
        entry = self._entries.get(key)
        if entry:
            entry.importance = max(0.0, min(1.0, importance))
            return True
        return False

    def has(self, key: str) -> bool:
        """Check if a key exists in memory."""
        return key in self._entries

    def remove(self, key: str) -> bool:
        """Remove an entry from memory.

        Args:
            key: Memory key.

        Returns:
            True if removed, False if not found.
        """
        if key in self._entries:
            del self._entries[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._access_order.clear()
        self._compressed_summary = None

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "entries": len(self._entries),
            "window_size": self.window_size,
            "compression_threshold": self.compression_threshold,
            "compressed_summary": self._compressed_summary is not None,
        }

    def _enforce_window(self) -> None:
        """Enforce window size by removing oldest entries."""
        while len(self._entries) > self.window_size:
            # Remove oldest entry
            oldest_key = self._access_order.popleft()
            if oldest_key in self._entries:
                del self._entries[oldest_key]

    def _compress(self) -> None:
        """Compress old entries into a summary.

        In a full implementation, this would use an LLM to generate
        a summary of old memories.
        """
        # For now, just mark that compression would happen
        # In production, use LLM to summarize old entries
        old_entries = sorted(
            self._entries.values(),
            key=lambda e: e.last_accessed,
        )[: len(self._entries) // 2]

        if old_entries:
            # Remove old entries
            for entry in old_entries:
                if entry.key in self._entries:
                    del self._entries[entry.key]
                if entry.key in self._access_order:
                    self._access_order.remove(entry.key)

            # Store compression indicator
            self._compressed_summary = f"Compressed {len(old_entries)} entries"

    def to_context_string(self, max_entries: int = 10) -> str:
        """Convert recent memories to a context string.

        Args:
            max_entries: Maximum entries to include.

        Returns:
            Formatted context string.
        """
        entries = self.retrieve_recent(max_entries)
        if not entries:
            return ""

        parts = ["Recent context:"]
        for key, value in entries:
            parts.append(f"  - {key}: {value}")

        return "\n".join(parts)


class ConversationalMemory(ShortTermMemory):
    """Short-term memory specialized for conversation tracking."""

    def add_turn(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a conversation turn.

        Args:
            role: Speaker role (user/assistant/system).
            content: Message content.
            metadata: Additional metadata.
        """
        turn_number = len(self._entries) + 1
        key = f"turn_{turn_number:04d}"
        value = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        self.store(key, value, importance=0.8)

    def get_conversation_history(
        self,
        n: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get conversation history.

        Args:
            n: Number of turns (None for all).

        Returns:
            List of conversation turns.
        """
        entries = self.retrieve_recent(n or len(self._entries))
        return [entry[1] for entry in reversed(entries)]

    def to_messages(self, n: int | None = None) -> list[dict[str, str]]:
        """Convert to LLM message format.

        Args:
            n: Number of turns.

        Returns:
            List of message dictionaries.
        """
        history = self.get_conversation_history(n)
        return [
            {"role": turn["role"], "content": turn["content"]}
            for turn in history
        ]
