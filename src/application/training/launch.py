"""Application coordinator for starting one Web/interactive training run."""

from __future__ import annotations

from typing import Protocol

from src.core.config import EngineConfig

from .contracts import TrainingPlan


class TrainingStarter(Protocol):
    def start_training(self, *, plan: TrainingPlan) -> None: ...


class InferenceTrainingCoordinator(Protocol):
    def prepare_for_training(self, target_device: str, /) -> object: ...


class ConfigActivator(Protocol):
    def activate(self, config: EngineConfig, /) -> object: ...


class TrainingLaunchApplicationService:
    """Coordinate runtime handoff, background start, and active config commit.

    The transport adapter calls one use case. Configuration becomes active only after
    the background training lifecycle accepts the run.
    """

    def __init__(
        self,
        *,
        training_service: TrainingStarter,
        inference_service: InferenceTrainingCoordinator,
        config_service: ConfigActivator,
    ) -> None:
        self._training_service = training_service
        self._inference_service = inference_service
        self._config_service = config_service

    def start(self, plan: TrainingPlan) -> None:
        self._inference_service.prepare_for_training(plan.runtime_plan.device)
        self._training_service.start_training(plan=plan)
        self._config_service.activate(plan.requested_config)
