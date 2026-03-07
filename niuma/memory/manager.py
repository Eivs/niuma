"""Memory manager for Niuma - unified interface for all memory types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from niuma.config import get_settings
from niuma.memory.long_term import LongTermMemory
from niuma.memory.short_term import ShortTermMemory
from niuma.memory.vector_store import SemanticMemory, VectorStore


@dataclass
class MemoryContext:
    """Context information from all memory layers."""

    short_term: dict[str, Any] = field(default_factory=dict)
    long_term: dict[str, Any] = field(default_factory=dict)
    semantic: list[dict[str, Any]] = field(default_factory=list)

    def to_prompt_context(self, max_semantic: int = 3) -> str:
        """Convert to a context string for LLM prompts."""
        parts = []

        if self.short_term:
            parts.append("Recent Context:")
            for key, value in self.short_term.items():
                parts.append(f"  {key}: {value}")

        if self.long_term:
            parts.append("\nRelevant Knowledge:")
            for key, value in self.long_term.items():
                parts.append(f"  {key}: {value}")

        if self.semantic:
            parts.append(f"\nTop {max_semantic} Related Memories:")
            for mem in self.semantic[:max_semantic]:
                parts.append(f"  - {mem.get('content', '')}")

        return "\n".join(parts) if parts else ""


class MemoryManager:
    """Unified memory manager for all memory types."""

    def __init__(
        self,
        short_term: ShortTermMemory | None = None,
        long_term: LongTermMemory | None = None,
        semantic: SemanticMemory | None = None,
    ) -> None:
        """Initialize memory manager.

        Args:
            short_term: Short-term memory instance.
            long_term: Long-term memory instance.
            semantic: Semantic memory instance.
        """
        self.short_term = short_term or ShortTermMemory()
        self.long_term = long_term or LongTermMemory()
        self.semantic = semantic or SemanticMemory()

        self._initialized = False

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize all memory systems."""
        if self._initialized:
            return

        # Initialize each memory system
        await self.long_term.initialize()
        await self.semantic.vector_store.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close and cleanup memory systems."""
        # LongTermMemory uses SQLite, no explicit close needed
        self._initialized = False

    async def store(
        self,
        key: str,
        value: Any,
        memory_type: str = "auto",
        importance: float = 0.5,
        category: str = "general",
        tags: list[str] | None = None,
    ) -> str | None:
        """Store a value in memory.

        Args:
            key: Memory key.
            value: Value to store.
            memory_type: Type of memory (short_term, long_term, semantic, auto).
            importance: Importance score (0.0-1.0).
            category: Category for long-term storage.
            tags: Tags for semantic search.

        Returns:
            Memory ID if stored in semantic memory.
        """
        if memory_type == "auto":
            # Auto-select based on importance
            if importance >= 0.8:
                memory_type = "semantic"
            elif importance >= 0.5:
                memory_type = "long_term"
            else:
                memory_type = "short_term"

        if memory_type == "short_term":
            self.short_term.store(key, value, importance=importance)
            return None

        elif memory_type == "long_term":
            await self.long_term.store(key, value, category=category, tags=tags)
            return key

        elif memory_type == "semantic":
            # Convert value to string for semantic storage
            content = str(value)
            return await self.semantic.remember(content, category=category, tags=tags)

        return None

    async def retrieve(
        self,
        key: str,
        memory_type: str = "short_term",
    ) -> Any:
        """Retrieve a value from memory.

        Args:
            key: Memory key.
            memory_type: Type of memory to search.

        Returns:
            Stored value or None if not found.
        """
        if memory_type == "short_term":
            return self.short_term.retrieve(key)

        elif memory_type == "long_term":
            return await self.long_term.retrieve(key)

        elif memory_type == "semantic":
            results = await self.semantic.vector_store.get([key])
            return results[0] if results else None

        return None

    async def search(
        self,
        query: str,
        memory_type: str = "semantic",
        n_results: int = 5,
        category: str | None = None,
    ) -> list[tuple[str, Any]] | list[dict[str, Any]]:
        """Search memory.

        Args:
            query: Search query.
            memory_type: Type of memory to search.
            n_results: Number of results.
            category: Filter by category.

        Returns:
            List of search results.
        """
        if memory_type == "semantic":
            return await self.semantic.recall(query, category=category, n_results=n_results)

        elif memory_type == "long_term":
            # Search by category
            return await self.long_term.search_by_category(category or "general", limit=n_results)

        return []

    async def get_context(
        self,
        query: str | None = None,
        n_semantic: int = 3,
    ) -> MemoryContext:
        """Get context from all memory layers.

        Args:
            query: Optional query for semantic search.
            n_semantic: Number of semantic results.

        Returns:
            MemoryContext with combined information.
        """
        context = MemoryContext()

        # Get recent short-term memories
        recent = self.short_term.retrieve_recent(5)
        context.short_term = {k: v for k, v in recent}

        # Get long-term context (important memories)
        important = self.short_term.retrieve_important(3)
        for key, value in important:
            context.short_term[key] = value

        # Semantic search if query provided
        if query:
            context.semantic = await self.semantic.recall(query, n_results=n_semantic)

        return context

    async def consolidate(
        self,
        keys: list[str] | None = None,
    ) -> str | None:
        """Consolidate short-term memories into long-term.

        Args:
            keys: Specific keys to consolidate (None for all important).

        Returns:
            Consolidated memory ID or None.
        """
        if keys is None:
            # Select important short-term memories
            entries = self.short_term.retrieve_important(3)
            keys = [k for k, _ in entries]

        if not keys:
            return None

        # Build consolidation content
        parts = []
        for key in keys:
            value = self.short_term.retrieve(key)
            if value:
                parts.append(f"{key}: {value}")

        if not parts:
            return None

        content = "\n".join(parts)

        # Store in semantic memory
        memory_id = await self.semantic.remember(
            content=content,
            category="consolidated",
            tags=["auto_consolidated"],
        )

        # Remove from short-term
        for key in keys:
            self.short_term.remove(key)

        return memory_id

    async def forget(
        self,
        key: str,
        memory_type: str = "short_term",
    ) -> bool:
        """Remove a memory.

        Args:
            key: Memory key.
            memory_type: Type of memory.

        Returns:
            True if removed.
        """
        if memory_type == "short_term":
            return self.short_term.remove(key)

        elif memory_type == "long_term":
            return await self.long_term.delete(key)

        elif memory_type == "semantic":
            return await self.semantic.forget(key)

        return False

    async def clear(self, memory_type: str = "all") -> None:
        """Clear memories.

        Args:
            memory_type: Which memory to clear (all, short_term, long_term, semantic).
        """
        if memory_type in ("all", "short_term"):
            self.short_term.clear()

        if memory_type in ("all", "long_term"):
            await self.long_term.clear()

        if memory_type in ("all", "semantic"):
            await self.semantic.vector_store.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "short_term": self.short_term.get_stats(),
            "initialized": self._initialized,
        }
