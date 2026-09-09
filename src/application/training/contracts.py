"""Transport-neutral training use-case contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from src.core.config import EngineConfig
from src.core.runtime import ResolvedTrainingPlan
from src.training.trainer import Trainer


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


@dataclass
class PreparedTrainingRun:
    config: EngineConfig
    runtime_plan: ResolvedTrainingPlan
    trainer: Trainer


class TrainingObserver(Protocol):
    def on_step(self, *, step: int, loss: float, lr: float, elapsed: float, emit: bool) -> None: ...

    def on_eval(self, *, step: int, train_loss: float, val_loss: float, lr: float) -> None: ...

    def on_sample(self, *, step: int, text: str) -> None: ...


class NullTrainingObserver:
    def on_step(self, **kwargs) -> None:
        del kwargs

    def on_eval(self, **kwargs) -> None:
        del kwargs

    def on_sample(self, **kwargs) -> None:
        del kwargs


class TrainingPreparationAborted(RuntimeError):
    """Internal control signal when a caller cancels preparation safely."""
