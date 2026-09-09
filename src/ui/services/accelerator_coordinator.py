"""Compatibility module alias for the application-owned accelerator coordinator."""

from __future__ import annotations

import sys

from src.application.runtime import accelerator as _implementation

AcceleratorCoordinator = _implementation.AcceleratorCoordinator

__all__ = ["AcceleratorCoordinator"]

sys.modules[__name__] = _implementation
