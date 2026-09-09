"""Test-only concrete wiring helpers for Application port unit tests."""

from __future__ import annotations

from typing import Optional, cast

from src.application.config.service import ConfigurationService
from src.application.inference.service import InferenceService
from src.application.training.background import TrainingService
from src.application.training.service import TrainingApplicationService
from src.composition.training_runtime import TrainingRuntimeAdapter
from src.core.accelerator import AcceleratorCoordinator
from src.core.concurrency import ThreadSynchronization
from src.core.config import EngineConfig, GenerationConfig
from src.inference.admission import GenerationAdmission
from src.inference.api import InferenceRuntime
from src.training.api import BackgroundExecution, TrainingEventHub


def concrete_inference_runtime(service: InferenceService) -> InferenceRuntime:
    """Expose concrete inference mechanics only to integration-style tests."""
    return cast(InferenceRuntime, service._runtime)


def make_inference_service(
    checkpoint_dir: str = "checkpoints",
    default_checkpoint: Optional[str] = None,
    vocab_path: str = "data/vocab.json",
    device: str = "auto",
    backend: str = "local",
    max_generation_sessions: int = 2,
    checkpoint_name: str = "best_model.pt",
    generation_config: Optional[GenerationConfig] = None,
    accelerator_coordinator: Optional[AcceleratorCoordinator] = None,
    config_service: Optional[ConfigurationService] = None,
    engine_config: Optional[EngineConfig] = None,
) -> InferenceService:
    if engine_config is not None:
        initial = ConfigurationService.snapshot(engine_config)
    else:
        base = EngineConfig()
        generation = (
            GenerationConfig.from_kwargs_safe(generation_config.to_dict())
            if generation_config is not None
            else GenerationConfig.from_kwargs_safe(base.generation.to_dict())
        )
        initial = ConfigurationService.snapshot(
            base.copy(
                data=base.data.copy(vocab_file=vocab_path),
                training=base.training.copy(
                    checkpoint_dir=checkpoint_dir,
                    checkpoint_name=checkpoint_name,
                ),
                system=base.system.copy(device=device),
                generation=generation,
            )
        )
    accelerator = accelerator_coordinator
    runtime = InferenceRuntime(device=initial.system.device, backend=backend)
    admission = GenerationAdmission(
        max_sessions=max_generation_sessions,
        accelerator_coordinator=accelerator,
    )
    return InferenceService(
        runtime=runtime,
        admission=admission,
        synchronization=ThreadSynchronization(),
        engine_config=initial,
        accelerator=accelerator,
        config_service=config_service,
        default_checkpoint=default_checkpoint,
    )


def make_inference_service_from_config(
    config: EngineConfig,
    *,
    backend: str = "local",
    max_generation_sessions: int = 2,
    accelerator_coordinator: Optional[AcceleratorCoordinator] = None,
    config_service: Optional[ConfigurationService] = None,
) -> InferenceService:
    accelerator = accelerator_coordinator
    runtime = InferenceRuntime(device=config.system.device, backend=backend)
    admission = GenerationAdmission(
        max_sessions=max_generation_sessions,
        accelerator_coordinator=accelerator,
    )
    return InferenceService.from_engine_config(
        config,
        runtime=runtime,
        admission=admission,
        synchronization=ThreadSynchronization(),
        accelerator=accelerator,
        config_service=config_service,
    )


def make_training_application(
    config_service: Optional[ConfigurationService] = None,
) -> TrainingApplicationService:
    return TrainingApplicationService(
        runtime=TrainingRuntimeAdapter(),
        config_service=config_service,
    )


def make_training_service(
    accelerator_coordinator: Optional[AcceleratorCoordinator] = None,
    training_application: Optional[TrainingApplicationService] = None,
    execution: Optional[BackgroundExecution] = None,
) -> TrainingService:
    application = training_application or make_training_application()
    return TrainingService(
        training_application=application,
        execution=execution or BackgroundExecution(),
        events=TrainingEventHub(queue_size=500),
        synchronization=ThreadSynchronization(),
        accelerator=accelerator_coordinator,
    )
