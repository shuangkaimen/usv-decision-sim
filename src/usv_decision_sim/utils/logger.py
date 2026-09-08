"""Logging helpers used by the simulator and its experiments.

The module deliberately wraps the standard-library :mod:`logging` package
instead of introducing a project-wide logging dependency.  ``setup_logger``
is safe to call more than once: handlers created by this module are replaced,
while handlers owned by application code are left untouched.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

DEFAULT_LOGGER_NAME: Final[str] = "usv_decision_sim"
DEFAULT_LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_HANDLER_MARKER: Final[str] = "_usv_decision_sim_handler"


def _normalize_level(level: int | str) -> int:
    """兼容标准库支持的字符串级别与整数级别，同时拒绝含义模糊的类型。"""
    if isinstance(level, bool):
        raise TypeError("level must be a logging level name or an integer")
    if isinstance(level, str):
        level_number = logging.getLevelNamesMapping().get(level.upper())
        if level_number is None:
            raise ValueError(f"unknown logging level: {level}")
        return level_number
    if isinstance(level, int):
        return level
    raise TypeError("level must be a logging level name or an integer")


def _remove_managed_handlers(logger: logging.Logger) -> None:
    """仅替换本工具创建的 handler，避免破坏调用方自行添加的日志出口。"""
    for handler in logger.handlers[:]:
        if getattr(handler, _HANDLER_MARKER, False):
            logger.removeHandler(handler)
            handler.close()


def _mark_handler(handler: logging.Handler) -> logging.Handler:
    """为工具自有 handler 添加轻量标记，以支持安全的重复配置。"""
    setattr(handler, _HANDLER_MARKER, True)
    return handler


def setup_logger(
    name: str = DEFAULT_LOGGER_NAME,
    *,
    level: int | str = logging.INFO,
    log_file: str | Path | None = None,
    console: bool = True,
    log_format: str = DEFAULT_LOG_FORMAT,
) -> logging.Logger:
    """Create or reconfigure a project logger.

    Args:
        name: Logger name, normally a module's ``__name__``.
        level: Numeric level or standard name such as ``"DEBUG"``.
        log_file: Optional path for an UTF-8 append-only file handler. Parent
            directories are created when necessary.
        console: Whether to attach a ``StreamHandler`` for console output.
        log_format: Standard ``logging`` format string.

    Returns:
        The configured :class:`logging.Logger` instance.

    ``setup_logger`` only manages handlers it created itself, so callers may
    attach their own handlers without them being removed on reconfiguration.
    Propagation is disabled to prevent duplicate output through the root logger.
    """
    if not name or not isinstance(name, str):
        raise ValueError("name must be a non-empty string")
    level_number = _normalize_level(level)
    if not isinstance(log_format, str) or not log_format:
        raise ValueError("log_format must be a non-empty string")

    logger = logging.getLogger(name)
    logger.setLevel(level_number)
    logger.propagate = False
    _remove_managed_handlers(logger)

    formatter = logging.Formatter(log_format)
    if console:
        console_handler = _mark_handler(logging.StreamHandler())
        console_handler.setLevel(level_number)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file is not None:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = _mark_handler(logging.FileHandler(file_path, encoding="utf-8"))
        file_handler.setLevel(level_number)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """Return a configured logger, creating the default console setup once."""
    logger = logging.getLogger(name)
    if not any(getattr(handler, _HANDLER_MARKER, False) for handler in logger.handlers):
        setup_logger(name)
    return logger


__all__ = [
    "DEFAULT_LOGGER_NAME",
    "DEFAULT_LOG_FORMAT",
    "get_logger",
    "setup_logger",
]
