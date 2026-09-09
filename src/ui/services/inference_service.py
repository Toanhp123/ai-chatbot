"""Compatibility module alias for the application-owned inference service."""

from __future__ import annotations

import sys

from src.application.inference import service as _implementation

InferenceService = _implementation.InferenceService

__all__ = ["InferenceService"]

sys.modules[__name__] = _implementation
