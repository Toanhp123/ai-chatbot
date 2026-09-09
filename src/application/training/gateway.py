"""Single public training gateway for outer adapters."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Optional, Protocol

from .contracts import (
    TrainingCommand,
    TrainingExecutionResult,
    TrainingFeasibility,
    TrainingObserver,
    TrainingStartResult,
)


class TrainingPlannerPort(Protocol):
    def check_feasibility(self, command: TrainingCommand) -> TrainingFeasibility: ...
    def run(
        self,
        command: TrainingCommand,
        *,
        observer: Optional[TrainingObserver] = None,
        log_interval: int = 10,
    ) -> TrainingExecutionResult: ...


class TrainingLaunchPort(Protocol):
    def start_command(self, command: TrainingCommand) -> TrainingStartResult: ...


class BackgroundTrainingPort(Protocol):
    def stop_training(self) -> None: ...
    def clear_state(self) -> None: ...
    def get_state(self) -> dict[str, Any]: ...
    def iter_events(self) -> Generator[dict[str, Any], None, None]: ...


class TrainingGateway:
    """Expose training use cases without leaking plans, runtime objects or lifecycle mechanics."""

    def __init__(
        self,
        *,
        planner: TrainingPlannerPort,
        launcher: TrainingLaunchPort,
        background: BackgroundTrainingPort,
    ) -> None:
        self._planner = planner
        self._launcher = launcher
        self._background = background

    def check_feasibility(self, command: TrainingCommand) -> TrainingFeasibility:
        return self._planner.check_feasibility(command)

    def start(self, command: TrainingCommand) -> TrainingStartResult:
        return self._launcher.start_command(command)

    def run(
        self,
        command: TrainingCommand,
        *,
        observer: Optional[TrainingObserver] = None,
        log_interval: int = 10,
    ) -> TrainingExecutionResult:
        return self._planner.run(command, observer=observer, log_interval=log_interval)

    def stop(self) -> None:
        self._background.stop_training()

    def clear(self) -> None:
        self._background.clear_state()

    def get_state(self) -> dict[str, Any]:
        return self._background.get_state()

    def iter_events(self) -> Generator[dict[str, Any], None, None]:
        return self._background.iter_events()


__all__ = ["TrainingGateway"]
