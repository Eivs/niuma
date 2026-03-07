"""Tests for memory systems."""

import pytest

from niuma.memory.short_term import ShortTermMemory, MemoryEntry
from niuma.memory.long_term import LongTermMemory


class TestShortTermMemory:
    """Test short-term memory."""

    def test_store_and_retrieve(self):
        """Test storing and retrieving."""
        stm = ShortTermMemory(window_size=5)

        stm.store("key1", "value1")
        assert stm.retrieve("key1") == "value1"

    def test_window_enforcement(self):
        """Test window size enforcement."""
        stm = ShortTermMemory(window_size=3)

        for i in range(5):
            stm.store(f"key{i}", f"value{i}")

        assert len(stm._entries) <= 3

    def test_recent_retrieval(self):
        """Test retrieving recent entries."""
        stm = ShortTermMemory()

        stm.store("key1", "value1")
        stm.store("key2", "value2")

        recent = stm.retrieve_recent(2)
        assert len(recent) == 2


class TestLongTermMemory:
    """Test long-term memory."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, tmp_path):
        """Test storing and retrieving."""
        ltm = LongTermMemory(db_path=tmp_path / "test_memory.db")
        await ltm.initialize()

        await ltm.store("key1", {"data": "value1"})
        result = await ltm.retrieve("key1")

        assert result == {"data": "value1"}
