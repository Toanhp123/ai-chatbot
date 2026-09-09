"""Training application use cases: resolve, preflight, prepare and execute."""

from __future__ import annotations

import time
import uuid
from typing import Callable, Optional

from src.application.config import ConfigRequest, ConfigurationService
from src.application.data_policy import prepare_application_dataset
from src.core.config import EngineConfig
from src.core.diagnostics import check_memory_feasibility
from src.core.runtime import ResolvedTrainingPlan, resolve_training_plan
from src.data.api import FALLBACK_CORPUS
from src.training.api import (
    PreparedTrainingRun,
    TrainingObserver,
    TrainingRunFactory,
    TrainOutput,
)

from .contracts import TrainingCommand, TrainingFeasibility, TrainingPlan


def generate_run_name() -> str:
    return f"kieu_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


class TrainingApplicationService:
    """Own training use-case policy while delegating runtime mechanics."""

    def __init__(
        self,
        config_service: Optional[ConfigurationService] = None,
        run_factory: Optional[TrainingRunFactory] = None,
    ) -> None:
        self.config_service = config_service
        # ``run_factory`` remains as a compatibility injection point, but its
        # implementation is capability-owned rather than Application-owned.
        self.run_factory = run_factory or TrainingRunFactory()

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
            resume_checkpoint_identity=command.resume_checkpoint_identity,
        )

    def prepare(
        self,
        plan: TrainingPlan,
        *,
        observer: Optional[TrainingObserver] = None,
        abort_check: Optional[Callable[[], bool]] = None,
        log_interval: int = 10,
    ) -> PreparedTrainingRun:
        """Apply data-selection policy, then delegate trainer mechanics."""
        if abort_check is not None and abort_check():
            from src.training.api import TrainingPreparationAborted

            raise TrainingPreparationAborted()

        effective = ConfigurationService.snapshot(plan.config)
        train_data, val_data, tokenizer = prepare_application_dataset(
            effective.data,
            block_size=effective.model.block_size,
            fallback_text=FALLBACK_CORPUS,
            persist_fallback=True,
        )
        if abort_check is not None and abort_check():
            from src.training.api import TrainingPreparationAborted

            raise TrainingPreparationAborted()

        return self.run_factory.prepare(
            config=effective,
            runtime_plan=plan.runtime_plan,
            train_data=train_data,
            val_data=val_data,
            tokenizer=tokenizer,
            observer=observer,
            abort_check=abort_check,
            log_interval=log_interval,
        )

    def execute(self, prepared: PreparedTrainingRun, plan: TrainingPlan) -> TrainOutput:
        """Execute a prepared capability run with Application-owned resume policy."""
        return self.run_factory.execute(
            prepared,
            resume_checkpoint=plan.resume_checkpoint,
            resume_checkpoint_identity=plan.resume_checkpoint_identity,
        )
