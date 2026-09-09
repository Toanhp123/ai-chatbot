"""Compatibility module alias for application-owned background training lifecycle."""

from __future__ import annotations

import sys

from src.application.training import background as _implementation

TrainingService = _implementation.TrainingService

__all__ = ["TrainingService"]

sys.modules[__name__] = _implementation
