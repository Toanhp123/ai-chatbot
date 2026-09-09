"""Stable public facade for training capability mechanics and contracts."""

from src.training.checkpoints import capture_checkpoint_identity
from src.training.contracts import (
    BackgroundTask,
    CancellationSignal,
    NullTrainingObserver,
    PreparedTrainingRun,
    TrainingControl,
    TrainingObserver,
    TrainingPreparationAborted,
)
from src.training.events import TrainingEventHub
from src.training.execution import BackgroundExecution
from src.training.runtime import TrainingRunFactory
from src.training.trainer import TrainingTerminationReason, TrainOutput

__all__ = [
    "BackgroundExecution",
    "capture_checkpoint_identity",
    "BackgroundTask",
    "CancellationSignal",
    "NullTrainingObserver",
    "PreparedTrainingRun",
    "TrainOutput",
    "TrainingControl",
    "TrainingEventHub",
    "TrainingObserver",
    "TrainingPreparationAborted",
    "TrainingRunFactory",
    "TrainingTerminationReason",
]
