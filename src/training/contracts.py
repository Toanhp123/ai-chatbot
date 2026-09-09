"""Stable contracts exposed by the training capability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

from src.core.config import EngineConfig
from src.core.exceptions import TrainingPreparationCancelled
from src.core.runtime import ResolvedTrainingPlan


class TrainingControl(Protocol):
    """Minimal control surface Application needs from a prepared run."""

    def request_stop(self) -> None: ...

    def train(
        self,
        resume_checkpoint: Optional[str] = None,
        resume_checkpoint_identity: Optional[tuple[int, int, int, int]] = None,
    ) -> Any: ...


@dataclass
class PreparedTrainingRun:
    config: EngineConfig
    runtime_plan: ResolvedTrainingPlan
    trainer: TrainingControl


class TrainingObserver(Protocol):
    def on_step(self, *, step: int, loss: float, lr: float, elapsed: float, emit: bool) -> None: ...

    def on_eval(self, *, step: int, train_loss: float, val_loss: float, lr: float) -> None: ...

    def on_sample(self, *, step: int, text: str) -> None: ...


class NullTrainingObserver:
    def on_step(self, **kwargs: Any) -> None:
        del kwargs

    def on_eval(self, **kwargs: Any) -> None:
        del kwargs

    def on_sample(self, **kwargs: Any) -> None:
        del kwargs


class CancellationSignal(Protocol):
    def set(self) -> None: ...
    def clear(self) -> None: ...
    def is_set(self) -> bool: ...


class BackgroundTask(Protocol):
    def start(self) -> None: ...
    def join(self, timeout: Optional[float] = None) -> None: ...
    def is_alive(self) -> bool: ...


BackgroundTarget = Callable[[], None]


__all__ = [
    "BackgroundTarget",
    "BackgroundTask",
    "CancellationSignal",
    "NullTrainingObserver",
    "PreparedTrainingRun",
    "TrainingControl",
    "TrainingObserver",
    "TrainingPreparationCancelled",
]
