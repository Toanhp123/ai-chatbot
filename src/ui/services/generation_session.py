"""Compatibility module alias for the application-owned generation session."""

from __future__ import annotations

import sys

from src.application.inference import session as _implementation

GenerationSession = _implementation.GenerationSession

__all__ = ["GenerationSession"]

sys.modules[__name__] = _implementation
