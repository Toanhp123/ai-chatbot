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


class SpyInferenceRuntime:
    """Spy runtime that records calls and raises on any actual runtime operation."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._current_checkpoint_path: Optional[str] = None
        self._current_checkpoint_identity: Optional[tuple[int, int, int, int]] = None
        self._device: str = "cpu"
        self._backend: str = "local"
        self._ready: bool = False

    @property
    def current_checkpoint_path(self) -> Optional[str]:
        return self._current_checkpoint_path

    @property
    def current_checkpoint_identity(self) -> Optional[tuple[int, int, int, int]]:
        return self._current_checkpoint_identity

    @property
    def device(self) -> str:
        return self._device

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def ready(self) -> bool:
        return self._ready

    def path_exists(self, path: str) -> bool:
        self.calls.append(f"path_exists:{path}")
        return False

    def join_path(self, *parts: str) -> str:
        return "/".join(parts)

    def load_tokenizer_if_present(self, vocab_path: str) -> bool:
        self.calls.append(f"load_tokenizer_if_present:{vocab_path}")
        return False

    def resolve_checkpoint_path_for_dir(
        self, checkpoint_dir: str, path: str, *, filename_only: bool = False
    ) -> str:
        return path

    def list_checkpoints(self, *, checkpoint_dir: str, checkpoint_name: str) -> list:
        return []

    def delete_checkpoint(self, *, checkpoint_dir: str, checkpoint_name: str, filename: str) -> str:
        return filename

    def list_generators(self) -> list[str]:
        return []

    def list_models(self) -> list[str]:
        return []

    def validate_backend(self, backend: str) -> str:
        return backend

    def resolve_device_name(self, device: str) -> str:
        return device

    def set_backend(self, backend: str) -> str:
        return backend

    def load_checkpoint(
        self,
        checkpoint_path: str,
        *,
        vocab_path: str,
        configured_device: str,
        backend: str,
    ) -> tuple[int, int, int, int]:
        self.calls.append(f"load_checkpoint:{checkpoint_path}")
        raise FileNotFoundError(f"Spy: checkpoint not found: {checkpoint_path}")

    def prepare_training_handoff(self):
        return None

    def begin_generation(self, *, prompt, config, requested_backend, stop_words, release_admission):
        raise RuntimeError("Spy: begin_generation not expected")


class FakeAdmission:
    def __init__(self) -> None:
        self.calls: list[str] = []

    @property
    def active_sessions(self) -> int:
        return 0

    def ensure_idle(self, *, operation: str) -> None:
        self.calls.append(f"ensure_idle:{operation}")

    def acquire(self, *, prompt: str, config, device: str):
        self.calls.append(f"acquire:{device}")
        return lambda: None


class FakeSynchronization:
    from contextlib import contextmanager

    @contextmanager  # type: ignore[misc]
    def section(self):
        yield


class FakeAccelerator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def same_family(self, first: str, second: str) -> bool:
        return True

    def reserve_generation(self, device: str, *, operation: str) -> None:
        self.calls.append(f"reserve_generation:{device}:{operation}")

    def release_generation(self, device: str) -> None:
        self.calls.append(f"release_generation:{device}")

    def reserve_inference_residency(self, device: str) -> None:
        self.calls.append(f"reserve_inference_residency:{device}")

    def release_inference_residency(self, device: str) -> None:
        self.calls.append(f"release_inference_residency:{device}")

    def transfer_inference_to_training(self, device: str) -> None:
        self.calls.append(f"transfer_inference_to_training:{device}")

    def transfer_training_to_inference(self, device: str) -> None:
        self.calls.append(f"transfer_training_to_inference:{device}")

    def reserve_training(self, device: str) -> None:
        self.calls.append(f"reserve_training:{device}")

    def release_training(self, device: str) -> None:
        self.calls.append(f"release_training:{device}")


