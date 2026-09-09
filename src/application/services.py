"""Typed Application gateway exposed to outer adapters."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.config import ConfigGateway
from src.application.diagnostics import DiagnosticsApplicationService
from src.application.explorer import ExplorerApplicationService
from src.application.inference import InferenceGateway
from src.application.training import TrainingGateway


@dataclass(frozen=True)
class ApplicationServices:
    """Single typed gateway used by CLI/HTTP adapters.

    The container owns references only; construction stays in ``src.composition``.
    """

    config: ConfigGateway
    inference: InferenceGateway
    training: TrainingGateway
    diagnostics: DiagnosticsApplicationService
    explorer: ExplorerApplicationService


__all__ = ["ApplicationServices"]
