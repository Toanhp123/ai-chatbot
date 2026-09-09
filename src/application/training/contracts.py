"""Application-owned training use-case contracts and inner ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generator, Optional, Protocol

from src.core.config import EngineConfig
from src.core.runtime import ResolvedTrainingPlan


@dataclass(frozen=True)
class TrainingCommand:
    config_path: Optional[str] = None
    overrides: tuple[str, ...] = ()
    quick_check: bool = False
    resume_checkpoint: Optional[str] = None


@dataclass(frozen=True)
class TrainingFeasibility:
    feasible: bool
    message: str
    estimated_gb: float
    estimated_mb: float


@dataclass(frozen=True)
class TrainingPlan:
    """Private-to-Application execution plan; adapters consume result DTOs instead."""

    requested_config: EngineConfig
    config: EngineConfig
    runtime_plan: ResolvedTrainingPlan
    feasibility: TrainingFeasibility
    resume_checkpoint: Optional[str] = None
    resume_checkpoint_identity: Optional[tuple[int, int, int, int]] = None


class TrainingObserver(Protocol):
    def on_step(self, *, step: int, loss: float, lr: float, elapsed: float, emit: bool) -> None: ...
    def on_eval(self, *, step: int, train_loss: float, val_loss: float, lr: float) -> None: ...
    def on_sample(self, *, step: int, text: str) -> None: ...


class TrainingControl(Protocol):
    def request_stop(self) -> None: ...


class RuntimePreparedRun(Protocol):
    @property
    def trainer(self) -> TrainingControl: ...


class RuntimeTrainResult(Protocol):
    @property
    def interrupted(self) -> bool: ...

    @property
    def termination_reason(self) -> object: ...


class TrainingRuntimePort(Protocol):
    def prepare(
        self,
        *,
        config: EngineConfig,
        runtime_plan: ResolvedTrainingPlan,
        train_data: Any,
        val_data: Any,
        tokenizer: Any,
        observer: Optional[TrainingObserver] = None,
        abort_check: Optional[Callable[[], bool]] = None,
        log_interval: int = 10,
    ) -> RuntimePreparedRun: ...

    def execute(
        self,
        prepared: RuntimePreparedRun,
        *,
        resume_checkpoint: Optional[str] = None,
        resume_checkpoint_identity: Optional[tuple[int, int, int, int]] = None,
    ) -> RuntimeTrainResult: ...


@dataclass
class PreparedTraining:
    runtime_run: RuntimePreparedRun
    control: TrainingControl


@dataclass(frozen=True)
class TrainingExecutionResult:
    interrupted: bool
    termination_reason: str


@dataclass(frozen=True)
class TrainingStartResult:
    """Transport-neutral result returned after a background start is committed."""

    feasibility: TrainingFeasibility


class CancellationSignalPort(Protocol):
    def set(self) -> None: ...
    def clear(self) -> None: ...
    def is_set(self) -> bool: ...


class BackgroundTaskPort(Protocol):
    def start(self) -> None: ...
    def join(self, timeout: Optional[float] = None) -> None: ...
    def is_alive(self) -> bool: ...


class BackgroundExecutionPort(Protocol):
    def create_task(self, target: Callable[[], None]) -> BackgroundTaskPort: ...
    def create_cancellation_signal(self) -> CancellationSignalPort: ...
    def is_current_task(self, task: BackgroundTaskPort) -> bool: ...
    def cleanup_accelerator_cache(self) -> None: ...


class TrainingEventPort(Protocol):
    def publish(self, event: dict[str, Any]) -> None: ...
    def iter_events(
        self,
        snapshot: Callable[[], dict[str, Any]],
        *,
        heartbeat_seconds: float = 1.0,
    ) -> Generator[dict[str, Any], None, None]: ...


class ResumeCheckpointPort(Protocol):
    def resolve(self, path: str, checkpoint_dir: str) -> str: ...
    def capture_identity(self, path: str) -> tuple[int, int, int, int]: ...


class NullTrainingObserver:
    def on_step(self, **kwargs: Any) -> None:
        del kwargs

    def on_eval(self, **kwargs: Any) -> None:
        del kwargs

    def on_sample(self, **kwargs: Any) -> None:
        del kwargs


__all__ = [
    "BackgroundExecutionPort",
    "BackgroundTaskPort",
    "CancellationSignalPort",
    "NullTrainingObserver",
    "PreparedTraining",
    "ResumeCheckpointPort",
    "RuntimePreparedRun",
    "RuntimeTrainResult",
    "TrainingCommand",
    "TrainingControl",
    "TrainingEventPort",
    "TrainingExecutionResult",
    "TrainingFeasibility",
    "TrainingObserver",
    "TrainingPlan",
    "TrainingRuntimePort",
    "TrainingStartResult",
]
