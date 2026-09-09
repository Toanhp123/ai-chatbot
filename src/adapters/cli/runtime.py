"""CLI process-runtime adapter."""

from __future__ import annotations

from src.core.config import EngineConfig
from src.core.logging import configure_logging_from_system


def configure_cli_logging(config: EngineConfig, *, name: str = "ai-train"):
    """Apply logging as a process/CLI concern from a canonical config snapshot."""
    return configure_logging_from_system(config.system, name=name)


__all__ = ["configure_cli_logging"]
