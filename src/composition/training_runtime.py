"""Composition-owned bridge from the training capability into Application ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.application.training.contracts import (
    RuntimePreparedRun,
    RuntimeTrainResult,
    TrainingControl,
    TrainingObserver,
)
from src.core.config import EngineConfig
from src.core.runtime import ResolvedTrainingPlan
from src.training.api import TrainingRunFactory
from src.training.contracts import PreparedTrainingRun


@dataclass(frozen=True)
class _PreparedTrainingHandle:
    """Opaque Application-facing handle around a capability-owned prepared run."""

    inner: PreparedTrainingRun

    @property
    def trainer(self) -> TrainingControl:
        return self.inner.trainer


@dataclass(frozen=True)
class _TrainingResult:
    interrupted: bool
    termination_reason: object


class TrainingRuntimeAdapter:
    """Adapt concrete training mechanics to the Application-owned runtime contract."""

    def __init__(self, factory: Optional[TrainingRunFactory] = None) -> None:
        self._factory = factory or TrainingRunFactory()

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
    ) -> RuntimePreparedRun:
        prepared = self._factory.prepare(
            config=config,
            runtime_plan=runtime_plan,
            train_data=train_data,
            val_data=val_data,
            tokenizer=tokenizer,
            observer=observer,
            abort_check=abort_check,
            log_interval=log_interval,
        )
        return _PreparedTrainingHandle(prepared)

    def execute(
        self,
        prepared: RuntimePreparedRun,
        *,
        resume_checkpoint: Optional[str] = None,
        resume_checkpoint_identity: Optional[tuple[int, int, int, int]] = None,
    ) -> RuntimeTrainResult:
        if not isinstance(prepared, _PreparedTrainingHandle):
            raise TypeError("Prepared training handle không thuộc TrainingRuntimeAdapter này.")
        output = self._factory.execute(
            prepared.inner,
            resume_checkpoint=resume_checkpoint,
            resume_checkpoint_identity=resume_checkpoint_identity,
        )
        return _TrainingResult(
            interrupted=bool(output.interrupted),
            termination_reason=output.termination_reason,
        )


__all__ = ["TrainingRuntimeAdapter"]
