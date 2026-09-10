"""The single production composition root.

This is the only source module allowed to know outer adapters, Application services,
and concrete inner runtime implementations at the same time.
"""

from __future__ import annotations

from typing import Optional

from src.adapters.config import YamlConfigProvider
from src.adapters.diagnostics import DiagnosticsRuntimeAdapter
from src.adapters.filesystem import FilesystemResumeCheckpointAdapter
from src.application.config import ConfigGateway
from src.application.config.service import ConfigurationService
from src.application.diagnostics import DiagnosticsApplicationService
from src.application.explorer import ExplorerApplicationService
from src.application.inference.gateway import InferenceGateway
from src.application.inference.service import InferenceService
from src.application.services import ApplicationServices
from src.application.training import TrainingGateway
from src.application.training.background import TrainingService
from src.application.training.contracts import TrainingRuntimePort
from src.application.training.launch import TrainingLaunchApplicationService
from src.application.training.service import TrainingApplicationService
from src.core.accelerator import AcceleratorCoordinator
from src.core.concurrency import ThreadSynchronization
from src.core.config import EngineConfig, GenerationConfig
from src.inference.admission import GenerationAdmission
from src.inference.api import InferenceRuntime
from src.training.api import BackgroundExecution, TrainingEventHub

from .training_runtime import TrainingRuntimeAdapter


def _initial_inference_config(
    *,
    engine_config: Optional[EngineConfig],
    checkpoint_dir: str,
    vocab_path: str,
    device: str,
    checkpoint_name: str,
    generation_config: Optional[GenerationConfig],
) -> EngineConfig:
    if engine_config is not None:
        engine_config.validate()
        return ConfigurationService.snapshot(engine_config)
    base = EngineConfig()
    generation = (
        GenerationConfig.from_kwargs_safe(generation_config.to_dict())
        if generation_config is not None
        else GenerationConfig.from_kwargs_safe(base.generation.to_dict())
    )
    return ConfigurationService.snapshot(
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


def _build_inference_service(
    *,
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
    """Construct the inference gateway without leaking runtime construction into Application."""
    if max_generation_sessions <= 0:
        raise ValueError("max_generation_sessions phải > 0")
    config = _initial_inference_config(
        engine_config=engine_config,
        checkpoint_dir=checkpoint_dir,
        vocab_path=vocab_path,
        device=device,
        checkpoint_name=checkpoint_name,
        generation_config=generation_config,
    )
    accelerator = accelerator_coordinator
    runtime = InferenceRuntime(device=config.system.device, backend=backend)
    admission = GenerationAdmission(
        max_sessions=max_generation_sessions,
        accelerator_coordinator=accelerator,
    )
    return (
        InferenceService.from_engine_config(
            config,
            runtime=runtime,
            admission=admission,
            synchronization=ThreadSynchronization(),
            accelerator=accelerator,
            config_service=config_service,
        )
        if default_checkpoint is None
        else InferenceService(
            runtime=runtime,
            admission=admission,
            synchronization=ThreadSynchronization(),
            engine_config=config,
            accelerator=accelerator,
            config_service=config_service,
            default_checkpoint=default_checkpoint,
        )
    )


def _build_training_application(
    config_service: Optional[ConfigurationService] = None,
    *,
    runtime: Optional[TrainingRuntimePort] = None,
) -> TrainingApplicationService:
    runtime_port = runtime if runtime is not None else TrainingRuntimeAdapter()
    return TrainingApplicationService(
        runtime=runtime_port,
        config_service=config_service,
    )


def _build_training_service(
    *,
    accelerator_coordinator: Optional[AcceleratorCoordinator] = None,
    training_application: Optional[TrainingApplicationService] = None,
    execution: Optional[BackgroundExecution] = None,
    events: Optional[TrainingEventHub] = None,
) -> TrainingService:
    application = training_application or _build_training_application()
    return TrainingService(
        training_application=application,
        execution=execution or BackgroundExecution(),
        events=events or TrainingEventHub(queue_size=500),
        synchronization=ThreadSynchronization(),
        accelerator=accelerator_coordinator,
    )


def build_application_services(
    *,
    backend: str = "local",
    max_generation_sessions: int = 2,
) -> ApplicationServices:
    """Build the complete application graph for CLI or HTTP adapters."""
    provider = YamlConfigProvider()
    configuration = ConfigurationService(provider)

    accelerator = AcceleratorCoordinator()
    inference_service = _build_inference_service(
        engine_config=EngineConfig(),
        backend=backend,
        max_generation_sessions=max_generation_sessions,
        accelerator_coordinator=accelerator,
        config_service=configuration,
    )
    training_application = _build_training_application(configuration)
    training = _build_training_service(
        accelerator_coordinator=accelerator,
        training_application=training_application,
    )
    training_launch = TrainingLaunchApplicationService(
        training_service=training,
        inference_service=inference_service,
        config_service=configuration,
        training_application=training_application,
        checkpoint_port=FilesystemResumeCheckpointAdapter(),
    )
    diagnostics = DiagnosticsApplicationService(
        configuration,
        runtime_adapter=DiagnosticsRuntimeAdapter(),
    )
    explorer = ExplorerApplicationService(configuration)
    inference_gateway = InferenceGateway(inference_service)
    training_gateway = TrainingGateway(
        planner=training_application,
        launcher=training_launch,
        background=training,
    )
    return ApplicationServices(
        config=ConfigGateway(configuration),
        inference=inference_gateway,
        training=training_gateway,
        diagnostics=diagnostics,
        explorer=explorer,
    )


__all__ = ["build_application_services"]
