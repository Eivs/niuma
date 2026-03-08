"""Logging utilities for Niuma.

提供统一的日志配置和获取接口，支持:
- 控制台彩色输出
- 文件日志记录
- JSON 格式日志 (用于生产环境)
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON 格式日志格式化器."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": f"{record.pathname}:{record.lineno}",
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器."""

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        # Format: [TIME] [LEVEL] [NAME] MESSAGE
        parts = [
            f"\033[90m[{self.formatTime(record)}]\033[0m",  # Gray timestamp
            f"{color}[{record.levelname:8}]{reset}",
            f"\033[90m[{record.name}]\033[0m",  # Gray logger name
            record.getMessage(),
        ]

        result = " ".join(parts)
        if record.exc_info:
            result += "\n" + self.formatException(record.exc_info)

        return result

    def formatTime(self, record: logging.LogRecord) -> str:
        """Format timestamp."""
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.strftime("%H:%M:%S")


# Cache for loggers
_LOGGER_CACHE: dict[str, logging.Logger] = {}
_ROOT_LOGGER_CONFIGURED = False


def setup_logging(
    level: str = "INFO",
    log_format: str = "colored",
    log_file: str | Path | None = None,
    file_format: str = "json",
) -> None:
    """Setup global logging configuration.

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 控制台日志格式 (colored, simple, json)
        log_file: 日志文件路径 (可选)
        file_format: 文件日志格式 (json, text)
    """
    global _ROOT_LOGGER_CONFIGURED

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    elif log_format == "simple":
        console_handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
            )
        )
    else:  # colored
        console_handler.setFormatter(ColoredFormatter())

    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler for large logs
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)

        if file_format == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )

        root_logger.addHandler(file_handler)

    _ROOT_LOGGER_CONFIGURED = True

    # Log startup message
    logger = logging.getLogger("niuma.logging")
    logger.debug("Logging configured: level=%s, format=%s", level, log_format)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    推荐命名规范:
    - niuma: 根 logger
    - niuma.core: 核心模块
    - niuma.core.agent: Agent 运行时
    - niuma.agents.code: Code Agent
    - niuma.memory: 记忆系统
    - niuma.tools: 工具系统

    Args:
        name: Logger 名称，推荐使用点分隔的模块路径

    Returns:
        配置好的 Logger 实例
    """
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    logger = logging.getLogger(name)
    _LOGGER_CACHE[name] = logger
    return logger
