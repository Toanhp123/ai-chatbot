"""Application coordinator for starting one interactive/background training run."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Optional, Protocol

from src.application.inference.contracts import InferenceTrainingHandoff
from src.core.config import EngineConfig

from .contracts import ResumeCheckpointPort, TrainingCommand, TrainingPlan, TrainingStartResult


class TrainingStarter(Protocol):
    def start_training(self, *, plan: TrainingPlan, admission_reserved: bool = False) -> None: ...


class InferenceTrainingCoordinator(Protocol):
    def prepare_for_training(self, target_device: str, /) -> InferenceTrainingHandoff: ...


class ConfigActivator(Protocol):
    def activate(self, config: EngineConfig, /) -> object: ...


class TrainingPlanner(Protocol):
    def plan(self, command: TrainingCommand) -> TrainingPlan: ...


class TrainingLaunchApplicationService:
    """Coordinate planning, checkpoint pinning, runtime handoff, start and config commit."""

    def __init__(
        self,
        *,
        training_service: TrainingStarter,
        inference_service: InferenceTrainingCoordinator,
        config_service: ConfigActivator,
        training_application: Optional[TrainingPlanner] = None,
        checkpoint_port: Optional[ResumeCheckpointPort] = None,
    ) -> None:
        self._training_service = training_service
        self._inference_service = inference_service
        self._config_service = config_service
        self._training_application = training_application
        self._checkpoint_port = checkpoint_port

    def start_command(self, command: TrainingCommand) -> TrainingStartResult:
        """Plan and start one run so adapters cannot mutate the planned use case."""
        if self._training_application is None:
            raise RuntimeError("Training command planning port chưa được cấu hình.")
        plan = self._training_application.plan(command)
        if command.resume_checkpoint:
            if self._checkpoint_port is None:
                raise RuntimeError("Resume checkpoint cần checkpoint port trong composition root.")
            checkpoint_path = self._checkpoint_port.resolve(
                command.resume_checkpoint,
                plan.requested_config.training.checkpoint_dir,
            )
            plan = replace(
                plan,
                resume_checkpoint=checkpoint_path,
                resume_checkpoint_identity=self._checkpoint_port.capture_identity(checkpoint_path),
            )
        self._start_plan(plan)
        return TrainingStartResult(feasibility=plan.feasibility)

    def start(self, plan: TrainingPlan) -> None:
        """Commit an already-planned run as one reversible Application transaction."""
        self._start_plan(plan)

    def _start_plan(self, plan: TrainingPlan) -> None:
        """Commit a preplanned run only after reversible runtime handoff succeeds."""
        handoff = self._inference_service.prepare_for_training(plan.runtime_plan.device)
        try:
            self._training_service.start_training(
                plan=plan,
                admission_reserved=handoff.training_admission_reserved,
            )
        except Exception:
            try:
                handoff.rollback()
            except Exception:
                logging.getLogger(__name__).exception(
                    "Không thể rollback inference sau khi training start thất bại."
                )
            raise
        self._config_service.activate(plan.requested_config)
