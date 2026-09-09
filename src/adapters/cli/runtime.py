"""CLI-owned process logging mechanics."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import List

from src.application.config import LoggingSettings

_MANAGED_HANDLERS: List[logging.Handler] = []


class _ConsoleFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="[%(asctime)s] [%(levelname)-7s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class _FileFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def _build_console_handler(level: int) -> logging.Handler:
    try:
        from rich.logging import RichHandler

        handler: logging.Handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
            markup=True,
        )
    except ImportError:
        handler = logging.StreamHandler()
        handler.setFormatter(_ConsoleFormatter())
    handler.setLevel(level)
    return handler


def _configure_process_logging(settings: LoggingSettings, *, name: str) -> logging.Logger:
    level = getattr(logging, settings.level.upper(), logging.INFO)
    root = logging.getLogger()

    for handler in list(_MANAGED_HANDLERS):
        if handler in root.handlers:
            root.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass
    _MANAGED_HANDLERS.clear()

    console = _build_console_handler(level)
    root.addHandler(console)
    _MANAGED_HANDLERS.append(console)

    if settings.file:
        path = os.path.abspath(settings.file)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file_handler = RotatingFileHandler(
            path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_FileFormatter())
        root.addHandler(file_handler)
        _MANAGED_HANDLERS.append(file_handler)

    root.setLevel(logging.DEBUG)
    return logging.getLogger(name)


def configure_cli_logging(settings: LoggingSettings, *, name: str = "ai-train") -> logging.Logger:
    """Apply Application-owned logging settings at the outer CLI boundary."""
    return _configure_process_logging(settings, name=name)


__all__ = ["configure_cli_logging"]
