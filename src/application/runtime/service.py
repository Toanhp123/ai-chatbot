"""Process/runtime application concerns shared by CLI and other outer adapters."""

from __future__ import annotations

from src.core.config import EngineConfig
from src.core.logging import configure_logging_from_system


class ApplicationRuntimeService:
    """Apply process-level runtime concerns from a canonical config snapshot."""

    @staticmethod
    def configure_logging(config: EngineConfig, *, name: str = "ai-train"):
        return configure_logging_from_system(config.system, name=name)
