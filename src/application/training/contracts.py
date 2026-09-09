"""Transport-neutral training use-case contracts.

Capability-owned runtime/control contracts are imported only through
``src.training.api`` so Application does not bind to trainer implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.core.config import EngineConfig
from src.core.runtime import ResolvedTrainingPlan
from src.training.api import (
    NullTrainingObserver,
    PreparedTrainingRun,
    TrainingObserver,
    TrainingPreparationAborted,
)


@dataclass(frozen=True)
class TrainingCommand:
    config_path: Optional[str] = None
    overrides: tuple[str, ...] = ()
    quick_check: bool = False
    resume_checkpoint: Optional[str] = None
    resume_checkpoint_identity: Optional[tuple[int, int, int, int]] = None


@dataclass(frozen=True)
class TrainingFeasibility:
    feasible: bool
    message: str
    estimated_gb: float
    estimated_mb: float


@dataclass(frozen=True)
class TrainingPlan:
    requested_config: EngineConfig
    config: EngineConfig
    runtime_plan: ResolvedTrainingPlan
    feasibility: TrainingFeasibility
    resume_checkpoint: Optional[str] = None
    resume_checkpoint_identity: Optional[tuple[int, int, int, int]] = None


__all__ = [
    "NullTrainingObserver",
    "PreparedTrainingRun",
    "TrainingCommand",
    "TrainingFeasibility",
    "TrainingObserver",
    "TrainingPlan",
    "TrainingPreparationAborted",
]
