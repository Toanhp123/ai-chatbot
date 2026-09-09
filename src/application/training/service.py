"""Training application use cases: policy, planning and runtime delegation."""

from __future__ import annotations

import time
import uuid
from typing import Callable, Optional

from src.application.config import ConfigRequest
from src.application.config.service import ConfigurationService
from src.application.data_policy import prepare_application_dataset
from src.core.config import EngineConfig
from src.core.diagnostics import check_memory_feasibility
from src.core.exceptions import TrainingPreparationCancelled
from src.core.runtime import ResolvedTrainingPlan, resolve_training_plan
from src.data.api import FALLBACK_CORPUS

from .contracts import (
    PreparedTraining,
    TrainingCommand,
    TrainingExecutionResult,
    TrainingFeasibility,
    TrainingObserver,
    TrainingPlan,
    TrainingRuntimePort,
)


def generate_run_name() -> str:
    return f"kieu_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _termination_value(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


class TrainingApplicationService:
    """Own training use-case policy while delegating trainer mechanics through a port."""

    def __init__(
        self,
        *,
        runtime: TrainingRuntimePort,
        config_service: Optional[ConfigurationService] = None,
    ) -> None:
        self.config_service = config_service
        self._runtime = runtime

    def plan(
        self,
        command: TrainingCommand,
        *,
        config_snapshot: Optional[EngineConfig] = None,
        runtime_plan: Optional[ResolvedTrainingPlan] = None,
        assign_run_name: bool = True,
    ) -> TrainingPlan:
        if config_snapshot is not None:
            config = ConfigurationService.snapshot(config_snapshot)
        else:
            if self.config_service is None:
                raise RuntimeError(
                    "TrainingApplicationService cần ConfigurationService khi không có config snapshot."
                )
            config = self.config_service.resolve(
                ConfigRequest(source=command.config_path, overrides=command.overrides)
            )
        if assign_run_name and config.training.run_name is None:
            config = config.copy(training=config.training.copy(run_name=generate_run_name()))
        requested_config = ConfigurationService.snapshot(config)
        effective_runtime = runtime_plan or resolve_training_plan(config)
        feasible, message, budget = check_memory_feasibility(
            model_config=config.model,
            training_config=config.training,
            runtime_plan=effective_runtime,
        )
        if command.quick_check:
            config = config.copy(
                training=config.training.copy(max_iters=50, eval_interval=25, eval_iters=10)
            )
        return TrainingPlan(
            requested_config=requested_config,
            config=ConfigurationService.snapshot(config),
            runtime_plan=effective_runtime,
            feasibility=TrainingFeasibility(
                feasible=feasible,
                message=message,
                estimated_gb=float(budget.get("total_estimated_gb", 0.0)),
                estimated_mb=float(budget.get("total_estimated_mb", 0.0)),
            ),
            resume_checkpoint=command.resume_checkpoint,
        )

    def check_feasibility(self, command: TrainingCommand) -> TrainingFeasibility:
        return self.plan(command, assign_run_name=False).feasibility

    def prepare(
        self,
        plan: TrainingPlan,
        *,
        observer: Optional[TrainingObserver] = None,
        abort_check: Optional[Callable[[], bool]] = None,
        log_interval: int = 10,
    ) -> PreparedTraining:
        """Apply Application data-selection policy, then delegate trainer mechanics."""
        if abort_check is not None and abort_check():
            raise TrainingPreparationCancelled()

        effective = ConfigurationService.snapshot(plan.config)
        train_data, val_data, tokenizer = prepare_application_dataset(
            effective.data,
            block_size=effective.model.block_size,
            fallback_text=FALLBACK_CORPUS,
            persist_fallback=True,
        )
        if abort_check is not None and abort_check():
            raise TrainingPreparationCancelled()

        runtime_run = self._runtime.prepare(
            config=effective,
            runtime_plan=plan.runtime_plan,
            train_data=train_data,
            val_data=val_data,
            tokenizer=tokenizer,
            observer=observer,
            abort_check=abort_check,
            log_interval=log_interval,
        )
        return PreparedTraining(runtime_run=runtime_run, control=runtime_run.trainer)

    def execute(self, prepared: PreparedTraining, plan: TrainingPlan) -> TrainingExecutionResult:
        """Execute a prepared capability run with Application-owned resume policy."""
        output = self._runtime.execute(
            prepared.runtime_run,
            resume_checkpoint=plan.resume_checkpoint,
            resume_checkpoint_identity=plan.resume_checkpoint_identity,
        )
        return TrainingExecutionResult(
            interrupted=bool(output.interrupted),
            termination_reason=_termination_value(output.termination_reason),
        )

    def run(
        self,
        command: TrainingCommand,
        *,
        observer: Optional[TrainingObserver] = None,
        log_interval: int = 10,
    ) -> TrainingExecutionResult:
        """Synchronous training use case used by CLI adapters."""
        plan = self.plan(command)
        prepared = self.prepare(plan, observer=observer, log_interval=log_interval)
        return self.execute(prepared, plan)
