"""Long-term memory storage for Niuma."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from niuma.config import get_settings


@dataclass
class LongTermMemoryEntry:
    """A long-term memory entry."""

    key: str
    value: Any
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def touch(self) -> None:
        """Update access time."""
        self.access_count += 1
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
        }


class LongTermMemory:
    """SQLite-based long-term memory storage."""

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize long-term memory.

        Args:
            db_path: Path to SQLite database.
        """
        settings = get_settings()
        self.db_path = db_path or settings.memory.sqlite_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: sqlite3.Connection | None = None
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    async def initialize(self) -> None:
        """Initialize the database."""
        if self._initialized:
            return

        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON memories(category)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)
        """)

        conn.commit()
        self._initialized = True

    async def store(
        self,
        key: str,
        value: Any,
        category: str = "general",
        tags: list[str] | None = None,
    ) -> None:
        """Store a value in long-term memory.

        Args:
            key: Memory key.
            value: Value to store (will be JSON serialized).
            category: Memory category.
            tags: List of tags.
        """
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()
        now = datetime.now().isoformat()

        conn.execute(
            """
            INSERT INTO memories (key, value, category, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                tags = excluded.tags,
                updated_at = excluded.updated_at
            """,
            (key, json.dumps(value), category, json.dumps(tags or []), now, now),
        )
        conn.commit()

    async def retrieve(self, key: str) -> Any | None:
        """Retrieve a value from long-term memory.

        Args:
            key: Memory key.

        Returns:
            Stored value or None if not found.
        """
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()
        row = conn.execute(
            "SELECT value, access_count FROM memories WHERE key = ?",
            (key,),
        ).fetchone()

        if row:
            # Update access count
            conn.execute(
                "UPDATE memories SET access_count = ?, updated_at = ? WHERE key = ?",
                (row["access_count"] + 1, datetime.now().isoformat(), key),
            )
            conn.commit()
            return json.loads(row["value"])

        return None

    async def search_by_category(
        self,
        category: str,
        limit: int = 10,
    ) -> list[tuple[str, Any]]:
        """Search memories by category.

        Args:
            category: Category to search.
            limit: Maximum results.

        Returns:
            List of (key, value) tuples.
        """
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()
        rows = conn.execute(
            "SELECT key, value FROM memories WHERE category = ? ORDER BY updated_at DESC LIMIT ?",
            (category, limit),
        ).fetchall()

        return [(row["key"], json.loads(row["value"])) for row in rows]

    async def search_by_tag(
        self,
        tag: str,
        limit: int = 10,
    ) -> list[tuple[str, Any]]:
        """Search memories by tag.

        Args:
            tag: Tag to search.
            limit: Maximum results.

        Returns:
            List of (key, value) tuples.
        """
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()
        # SQLite doesn't have array search, so we use LIKE
        rows = conn.execute(
            "SELECT key, value FROM memories WHERE tags LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f'%"{tag}"%', limit),
        ).fetchall()

        return [(row["key"], json.loads(row["value"])) for row in rows]

    async def list_keys(
        self,
        category: str | None = None,
        prefix: str | None = None,
    ) -> list[str]:
        """List memory keys.

        Args:
            category: Filter by category.
            prefix: Filter by key prefix.

        Returns:
            List of keys.
        """
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()
        query = "SELECT key FROM memories WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if prefix:
            query += " AND key LIKE ?"
            params.append(f"{prefix}%")

        query += " ORDER BY updated_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [row["key"] for row in rows]

    async def delete(self, key: str) -> bool:
        """Delete a memory entry.

        Args:
            key: Key to delete.

        Returns:
            True if deleted, False if not found.
        """
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0

    async def clear(self, category: str | None = None) -> int:
        """Clear memory entries.

        Args:
            category: If specified, only clear this category.

        Returns:
            Number of entries cleared.
        """
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()

        if category:
            cursor = conn.execute(
                "DELETE FROM memories WHERE category = ?",
                (category,),
            )
        else:
            cursor = conn.execute("DELETE FROM memories")

        conn.commit()
        return cursor.rowcount

    async def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()

        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

        categories = conn.execute(
            "SELECT category, COUNT(*) FROM memories GROUP BY category"
        ).fetchall()

        return {
            "total_entries": total,
            "categories": {row[0]: row[1] for row in categories},
            "db_path": str(self.db_path),
        }

    async def export(self, file_path: Path) -> None:
        """Export memories to JSON file.

        Args:
            file_path: Export file path.
        """
        if not self._initialized:
            await self.initialize()

        conn = self._get_connection()
        rows = conn.execute(
            "SELECT key, value, category, tags, created_at, updated_at, access_count FROM memories"
        ).fetchall()

        data = [
            {
                "key": row["key"],
                "value": json.loads(row["value"]),
                "category": row["category"],
                "tags": json.loads(row["tags"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "access_count": row["access_count"],
            }
            for row in rows
        ]

        file_path.write_text(json.dumps(data, indent=2))

    async def import_(self, file_path: Path) -> int:
        """Import memories from JSON file.

        Args:
            file_path: Import file path.

        Returns:
            Number of entries imported.
        """
        if not self._initialized:
            await self.initialize()

        data = json.loads(file_path.read_text())

        count = 0
        for entry in data:
            await self.store(
                key=entry["key"],
                value=entry["value"],
                category=entry.get("category", "general"),
                tags=entry.get("tags", []),
            )
            count += 1

        return count
