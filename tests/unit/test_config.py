"""Tests for configuration module."""

import pytest
from pathlib import Path

from niuma.config import Settings, get_settings, reset_settings


class TestSettings:
    """Test settings management."""

    def test_default_settings(self):
        """Test default settings values."""
        reset_settings()
        settings = get_settings()

        assert settings.app_name == "Niuma"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False

    def test_llm_settings(self):
        """Test LLM settings."""
        settings = get_settings()

        assert settings.llm.provider in ["openai", "anthropic"]
        assert settings.llm.temperature >= 0.0
        assert settings.llm.temperature <= 2.0

    def test_memory_settings(self):
        """Test memory settings."""
        settings = get_settings()

        assert settings.memory.stm_window_size > 0
        assert settings.memory.stm_compression_threshold > 0

    def test_directories_created(self):
        """Test that directories are created."""
        reset_settings()
        settings = get_settings()

        assert settings.data_dir.exists()
