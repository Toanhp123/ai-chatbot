"""Stable error contract exposed to outer adapters."""

from src.core.exceptions import AIEngineError, ConfigurationError, ErrorCode

__all__ = ["AIEngineError", "ConfigurationError", "ErrorCode"]
