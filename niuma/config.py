"""Configuration management for Niuma using Pydantic Settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings - flat structure for env var compatibility."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================================================================
    # Application
    # =========================================================================
    app_name: str = "Niuma"
    app_version: str = "0.1.0"
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    data_dir: Path = Field(
        default=Path(".niuma"),
        description="Base directory for application data",
    )

    # =========================================================================
    # LLM Settings
    # =========================================================================
    llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        description="LLM provider to use",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use",
    )
    openai_base_url: str | None = Field(
        default=None,
        description="OpenAI API base URL (for custom endpoints)",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        description="Anthropic model to use",
    )
    anthropic_base_url: str | None = Field(
        default=None,
        description="Anthropic API base URL (for custom endpoints)",
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature",
    )
    llm_max_tokens: int | None = Field(
        default=None,
        description="Maximum tokens to generate",
    )
    llm_timeout: float = Field(
        default=60.0,
        ge=1.0,
        description="API request timeout in seconds",
    )
    llm_retry_count: int = Field(
        default=3,
        ge=0,
        description="Number of retries on API failure",
    )

    # =========================================================================
    # Memory Settings
    # =========================================================================
    memory_vector_store_path: Path = Field(
        default=Path(".niuma/vector_store"),
        description="Path to vector store database",
    )
    memory_sqlite_path: Path = Field(
        default=Path(".niuma/memory.db"),
        description="Path to SQLite database for long-term memory",
    )
    memory_stm_window_size: int = Field(
        default=10,
        ge=1,
        description="Short-term memory window size (number of turns)",
    )
    memory_stm_compression_threshold: int = Field(
        default=20,
        ge=1,
        description="Threshold for compressing short-term memory",
    )
    memory_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model for vector storage",
    )

    # =========================================================================
    # Logging Settings
    # =========================================================================
    log_format: Literal["colored", "simple", "json"] = Field(
        default="colored",
        description="Console log format",
    )
    log_file: str | None = Field(
        default=None,
        description="Path to log file (optional)",
    )
    log_file_format: Literal["json", "text"] = Field(
        default="json",
        description="File log format",
    )
    log_enable_rich: bool = Field(
        default=True,
        description="Enable rich formatting for console output",
    )

    # =========================================================================
    # Agent Settings
    # =========================================================================
    agent_max_concurrency: int = Field(
        default=5,
        ge=1,
        description="Maximum concurrent agents",
    )
    agent_default_timeout: int = Field(
        default=300,
        ge=30,
        description="Default task timeout in seconds",
    )
    agent_max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retries per task",
    )

    # =========================================================================
    # Worktree Settings
    # =========================================================================
    worktree_base_path: Path = Field(
        default=Path(".niuma/worktrees"),
        description="Base path for worktree isolation",
    )
    worktree_max_worktrees: int = Field(
        default=10,
        ge=1,
        description="Maximum number of active worktrees",
    )
    worktree_auto_cleanup: bool = Field(
        default=True,
        description="Automatically cleanup inactive worktrees",
    )

    @field_validator("data_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """Ensure data_dir is a Path object and create if needed."""
        return Path(v)

    @field_validator(
        "memory_vector_store_path",
        "memory_sqlite_path",
        "worktree_base_path",
        mode="before",
    )
    @classmethod
    def ensure_path_optional(cls, v: str | Path | None) -> Path | None:
        """Ensure path fields are Path objects."""
        if v is None:
            return None
        return Path(v)

    def ensure_directories(self) -> None:
        """Create all necessary directories."""
        directories = [
            self.data_dir,
            self.memory_vector_store_path,
            self.worktree_base_path,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    # Compatibility properties for accessing nested settings
    @property
    def llm(self) -> "LLMSettings":
        """Access LLM settings."""
        return LLMSettings(self)

    @property
    def memory(self) -> "MemorySettings":
        """Access memory settings."""
        return MemorySettings(self)

    @property
    def agent(self) -> "AgentSettings":
        """Access agent settings."""
        return AgentSettings(self)

    @property
    def worktree(self) -> "WorktreeSettings":
        """Access worktree settings."""
        return WorktreeSettings(self)
class LLMSettings:
    """LLM provider settings - compatibility wrapper."""

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def provider(self) -> str:
        return self._settings.llm_provider

    @property
    def openai_api_key(self) -> str | None:
        return self._settings.openai_api_key

    @property
    def openai_model(self) -> str:
        return self._settings.openai_model

    @property
    def openai_base_url(self) -> str | None:
        return self._settings.openai_base_url

    @property
    def anthropic_api_key(self) -> str | None:
        return self._settings.anthropic_api_key

    @property
    def anthropic_model(self) -> str:
        return self._settings.anthropic_model

    @property
    def anthropic_base_url(self) -> str | None:
        return self._settings.anthropic_base_url

    @property
    def temperature(self) -> float:
        return self._settings.llm_temperature

    @property
    def max_tokens(self) -> int | None:
        return self._settings.llm_max_tokens

    @property
    def timeout(self) -> float:
        return self._settings.llm_timeout

    @property
    def retry_count(self) -> int:
        return self._settings.llm_retry_count


class MemorySettings:
    """Memory system settings - compatibility wrapper."""

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def vector_store_path(self) -> Path:
        return self._settings.memory_vector_store_path

    @property
    def sqlite_path(self) -> Path:
        return self._settings.memory_sqlite_path

    @property
    def stm_window_size(self) -> int:
        return self._settings.memory_stm_window_size

    @property
    def stm_compression_threshold(self) -> int:
        return self._settings.memory_stm_compression_threshold

    @property
    def embedding_model(self) -> str:
        return self._settings.memory_embedding_model


class AgentSettings:
    """Agent runtime settings - compatibility wrapper."""

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def max_concurrency(self) -> int:
        return self._settings.agent_max_concurrency

    @property
    def default_timeout(self) -> int:
        return self._settings.agent_default_timeout

    @property
    def max_retries(self) -> int:
        return self._settings.agent_max_retries


class WorktreeSettings:
    """Worktree isolation settings - compatibility wrapper."""

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def base_path(self) -> Path:
        return self._settings.worktree_base_path

    @property
    def max_worktrees(self) -> int:
        return self._settings.worktree_max_worktrees

    @property
    def auto_cleanup(self) -> bool:
        return self._settings.worktree_auto_cleanup


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings


def reset_settings() -> None:
    """Reset global settings (useful for testing)."""
    global _settings
    _settings = None
