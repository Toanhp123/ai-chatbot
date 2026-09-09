"""Application coordinator for starting one Web/interactive training run."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Callable, Optional, Protocol

from src.application.inference import InferenceTrainingHandoff
from src.core.config import EngineConfig
from src.training.api import capture_checkpoint_identity

from .contracts import TrainingCommand, TrainingPlan


class TrainingStarter(Protocol):
    def start_training(self, *, plan: TrainingPlan, admission_reserved: bool = False) -> None: ...


class InferenceTrainingCoordinator(Protocol):
    def prepare_for_training(self, target_device: str, /) -> InferenceTrainingHandoff: ...


class ConfigActivator(Protocol):
    def activate(self, config: EngineConfig, /) -> object: ...


class TrainingPlanner(Protocol):
    def plan(self, command: TrainingCommand) -> TrainingPlan: ...


ResumePathResolver = Callable[[str, str], str]


class TrainingLaunchApplicationService:
    """Coordinate planning, runtime handoff, background start and config commit."""

    def __init__(
        self,
        *,
        training_service: TrainingStarter,
        inference_service: InferenceTrainingCoordinator,
        config_service: ConfigActivator,
        training_application: Optional[TrainingPlanner] = None,
    ) -> None:
        self._training_service = training_service
        self._inference_service = inference_service
        self._config_service = config_service
        self._training_application = training_application

    @staticmethod
    def _capture_checkpoint_identity(path: str) -> tuple[int, int, int, int]:
        """Delegate revision pinning to the training capability filesystem boundary."""
        return capture_checkpoint_identity(path)

    def start_command(
        self,
        command: TrainingCommand,
        *,
        resume_checkpoint: Optional[str] = None,
        resume_path_resolver: Optional[ResumePathResolver] = None,
    ) -> TrainingPlan:
        """Plan and start one run so adapters do not mutate the planned use case."""
        if self._training_application is None:
            raise RuntimeError(
                "TrainingLaunchApplicationService cần TrainingApplicationService để start command."
            )
        plan = self._training_application.plan(command)
        if resume_checkpoint:
            checkpoint_path = (
                resume_path_resolver(
                    resume_checkpoint,
                    plan.requested_config.training.checkpoint_dir,
                )
                if resume_path_resolver is not None
                else resume_checkpoint
            )
            plan = replace(
                plan,
                resume_checkpoint=checkpoint_path,
                resume_checkpoint_identity=self._capture_checkpoint_identity(checkpoint_path),
            )
        self.start(plan)
        return plan

    def start(self, plan: TrainingPlan) -> None:
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
