"""Inference application use cases.

Application owns preferences, admission and cross-capability ownership policy.
Concrete checkpoint/model/generation mechanics are delegated to ``src.inference.api``.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Generator, List, Optional

from src.application.config import ConfigurationService
from src.application.inference.contracts import (
    GenerationCommand,
    GenerationOverrides,
    InferenceTrainingHandoff,
)
from src.application.inference.generation_admission import GenerationAdmissionManager
from src.application.inference.preferences import InferencePreferences
from src.application.runtime.accelerator import (
    AcceleratorCoordinator,
    same_accelerator_family,
)
from src.core.config import EngineConfig, GenerationConfig
from src.core.logging import get_logger
from src.inference.api import GenerationSession, InferenceRuntime
from src.inference.api import (
    load_generator_from_checkpoint as runtime_load_generator_from_checkpoint,
)

logger = get_logger("InferenceService")


class InferenceService:
    """Coordinate inference use cases without owning runtime implementation mechanics."""

    def __init__(
        self,
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
        runtime: Optional[InferenceRuntime] = None,
    ) -> None:
        if max_generation_sessions <= 0:
            raise ValueError("max_generation_sessions phải > 0")
        if engine_config is not None:
            engine_config.validate()
            initial_config = ConfigurationService.snapshot(engine_config)
        else:
            base_config = EngineConfig()
            canonical_generation = (
                GenerationConfig.from_kwargs_safe(generation_config.to_dict())
                if generation_config is not None
                else GenerationConfig.from_kwargs_safe(base_config.generation.to_dict())
            )
            initial_config = ConfigurationService.snapshot(
                base_config.copy(
                    data=base_config.data.copy(vocab_file=vocab_path),
                    training=base_config.training.copy(
                        checkpoint_dir=checkpoint_dir,
                        checkpoint_name=checkpoint_name,
                    ),
                    system=base_config.system.copy(device=device),
                    generation=canonical_generation,
                )
            )
        self._preferences = InferencePreferences(initial_config, config_service=config_service)
        self._runtime = runtime or InferenceRuntime(device=self.configured_device, backend=backend)
        self._accelerator_coordinator = accelerator_coordinator
        self._residency_device: Optional[str] = None
        self._lock = threading.RLock()
        self._generation_admission = GenerationAdmissionManager(
            max_sessions=max_generation_sessions,
            accelerator_coordinator=accelerator_coordinator,
        )

        if default_checkpoint is None:
            default_checkpoint = self.configured_checkpoint_path

        try:
            self._runtime.load_tokenizer_if_present(self.vocab_path)
        except Exception as exc:
            logger.warning("Chưa thể nạp tokenizer từ %s: %s", self.vocab_path, exc)

        if self._runtime.path_exists(default_checkpoint):
            try:
                self.load_checkpoint(default_checkpoint)
            except Exception as exc:
                logger.warning("Chưa thể nạp checkpoint mặc định %s: %s", default_checkpoint, exc)

    @classmethod
    def from_engine_config(
        cls,
        config: EngineConfig,
        *,
        backend: str = "local",
        max_generation_sessions: int = 2,
        accelerator_coordinator: Optional[AcceleratorCoordinator] = None,
        config_service: Optional[ConfigurationService] = None,
    ) -> "InferenceService":
        return cls(
            default_checkpoint=InferenceRuntime.join_path(
                config.training.checkpoint_dir,
                config.training.checkpoint_name,
            ),
            backend=backend,
            max_generation_sessions=max_generation_sessions,
            accelerator_coordinator=accelerator_coordinator,
            config_service=config_service,
            engine_config=config,
        )

    @property
    def checkpoint_dir(self) -> str:
        return self._preferences.checkpoint_dir

    @checkpoint_dir.setter
    def checkpoint_dir(self, value: str) -> None:
        self._preferences.checkpoint_dir = value

    @property
    def checkpoint_name(self) -> str:
        return self._preferences.checkpoint_name

    @checkpoint_name.setter
    def checkpoint_name(self, value: str) -> None:
        self._preferences.checkpoint_name = value

    @property
    def vocab_path(self) -> str:
        return self._preferences.vocab_path

    @vocab_path.setter
    def vocab_path(self, value: str) -> None:
        self._preferences.vocab_path = value

    @property
    def configured_device(self) -> str:
        return self._preferences.configured_device

    @configured_device.setter
    def configured_device(self, value: str) -> None:
        self._preferences.configured_device = value

    @property
    def default_generation_config(self) -> GenerationConfig:
        return self._preferences.default_generation_config

    @default_generation_config.setter
    def default_generation_config(self, value: GenerationConfig) -> None:
        self._preferences.default_generation_config = value

    # Compatibility/public observation properties. State ownership remains in InferenceRuntime.
    @property
    def current_checkpoint_path(self) -> Optional[str]:
        return self._runtime.current_checkpoint_path

    @current_checkpoint_path.setter
    def current_checkpoint_path(self, value: Optional[str]) -> None:
        self._runtime.current_checkpoint_path = value

    @property
    def _current_checkpoint_identity(self) -> Optional[tuple[int, int, int, int]]:
        return self._runtime.current_checkpoint_identity

    @_current_checkpoint_identity.setter
    def _current_checkpoint_identity(self, value: Optional[tuple[int, int, int, int]]) -> None:
        self._runtime.current_checkpoint_identity = value

    @property
    def device_str(self) -> str:
        return self._runtime.device

    @device_str.setter
    def device_str(self, value: str) -> None:
        self._runtime.device = value

    @property
    def current_backend(self) -> str:
        return self._runtime.backend

    @current_backend.setter
    def current_backend(self, value: str) -> None:
        self._runtime.backend = value

    @property
    def tokenizer(self) -> Any:
        return self._runtime.tokenizer

    @tokenizer.setter
    def tokenizer(self, value: Any) -> None:
        self._runtime.tokenizer = value

    @property
    def model(self) -> Any:
        return self._runtime.model

    @model.setter
    def model(self, value: Any) -> None:
        self._runtime.model = value

    @property
    def generator(self) -> Any:
        return self._runtime.generator

    @generator.setter
    def generator(self, value: Any) -> None:
        self._runtime.generator = value

    @property
    def _generation_lock(self):
        return self._runtime._generation_lock

    def apply_engine_config(self, config: EngineConfig) -> None:
        self._preferences.apply_engine_config(config)

    def get_engine_config(self) -> EngineConfig:
        return self._preferences.snapshot()

    @staticmethod
    def _identity_from_stat(stat_result: Any) -> tuple[int, int, int, int]:
        return InferenceRuntime.identity_from_stat(stat_result)

    @staticmethod
    def _checkpoint_identity(path: str) -> tuple[int, int, int, int]:
        return InferenceRuntime.checkpoint_identity(path)

    @staticmethod
    def _resolve_checkpoint_path_for_dir(
        checkpoint_dir: str,
        path: str,
        *,
        filename_only: bool = False,
    ) -> str:
        return InferenceRuntime.resolve_checkpoint_path_for_dir(
            checkpoint_dir,
            path,
            filename_only=filename_only,
        )

    def get_runtime_state(self) -> Dict[str, Any]:
        with self._lock:
            active_path = self.current_checkpoint_path
            active_identity = self._current_checkpoint_identity
            return {
                "current_checkpoint": active_path.replace("\\", "/") if active_path else None,
                "current_checkpoint_revision": (
                    ":".join(str(part) for part in active_identity) if active_identity else None
                ),
                "current_backend": self.current_backend,
                "checkpoint_dir": self.checkpoint_dir.replace("\\", "/"),
                "checkpoint_name": self.checkpoint_name,
                "vocab_path": self.vocab_path.replace("\\", "/"),
                "configured_device": self.configured_device,
                "active_device": self.device_str,
                "generation": self.default_generation_config.to_dict(),
            }

    def set_checkpoint_dir(self, checkpoint_dir: str) -> None:
        self.checkpoint_dir = checkpoint_dir

    def set_vocab_path(self, vocab_path: str) -> None:
        self.vocab_path = vocab_path

    @property
    def configured_checkpoint_path(self) -> str:
        return InferenceRuntime.join_path(self.checkpoint_dir, self.checkpoint_name)

    def resolve_checkpoint_path(self, path: str, *, filename_only: bool = False) -> str:
        with self._lock:
            checkpoint_dir = self.checkpoint_dir
        return self._runtime.resolve_checkpoint_path_for_dir(
            checkpoint_dir,
            path,
            filename_only=filename_only,
        )

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        with self._lock:
            checkpoint_dir = self.checkpoint_dir
            checkpoint_name = self.checkpoint_name
        return self._runtime.list_checkpoints(
            checkpoint_dir=checkpoint_dir,
            checkpoint_name=checkpoint_name,
        )

    def list_generators(self) -> List[str]:
        return self._runtime.list_generators()

    def prepare_for_training(self, target_device: str) -> InferenceTrainingHandoff:
        """Coordinate a reversible inference-residency to training-ownership handoff."""
        with self._lock:
            if not same_accelerator_family(self.device_str, target_device):
                return InferenceTrainingHandoff()
            self._generation_admission.ensure_idle(operation="prepare_training")
            if self.model is None or self.tokenizer is None:
                return InferenceTrainingHandoff()

            residency_device = self._residency_device
            runtime_handoff = self._runtime.prepare_training_handoff()
            if runtime_handoff is None:
                return InferenceTrainingHandoff()
            previous_device = runtime_handoff.previous_device
            admission_transferred = False
            try:
                if residency_device is not None and self._accelerator_coordinator is not None:
                    self._accelerator_coordinator.transfer_inference_to_training(residency_device)
                    admission_transferred = True
            except Exception:
                runtime_handoff.rollback()
                raise
            self._residency_device = None

            def rollback() -> None:
                with self._lock:
                    restored_residency = False
                    if admission_transferred and self._accelerator_coordinator is not None:
                        self._accelerator_coordinator.transfer_training_to_inference(
                            previous_device
                        )
                        restored_residency = True
                    try:
                        runtime_handoff.rollback()
                    except Exception:
                        if restored_residency and self._accelerator_coordinator is not None:
                            self._accelerator_coordinator.release_inference_residency(
                                previous_device
                            )
                        raise
                    self._residency_device = residency_device if restored_residency else None

            return InferenceTrainingHandoff(
                training_admission_reserved=admission_transferred,
                rollback=rollback,
            )

    def set_backend(self, backend: str) -> None:
        with self._lock:
            self._generation_admission.ensure_idle(operation="set_backend")
            cleaned = self._runtime.set_backend(backend)
        logger.info("Đã chuyển đổi Generator backend sang: '%s'", cleaned)

    def list_models(self) -> List[str]:
        return self._runtime.list_models()

    def resolve_generation_config(self, overrides: GenerationOverrides) -> GenerationConfig:
        defaults = self.default_generation_config
        temperature = (
            defaults.temperature if overrides.temperature is None else overrides.temperature
        )
        do_sample = defaults.do_sample if overrides.greedy is None else not overrides.greedy
        effective_temperature = 0.0 if overrides.greedy is True else temperature
        return defaults.copy(
            max_new_tokens=(
                defaults.max_new_tokens
                if overrides.max_new_tokens is None
                else overrides.max_new_tokens
            ),
            temperature=effective_temperature,
            top_k=defaults.top_k if overrides.top_k is None else overrides.top_k,
            top_p=defaults.top_p if overrides.top_p is None else overrides.top_p,
            min_p=defaults.min_p if overrides.min_p is None else overrides.min_p,
            repetition_penalty=(
                defaults.repetition_penalty
                if overrides.repetition_penalty is None
                else overrides.repetition_penalty
            ),
            do_sample=do_sample,
            use_cache=defaults.use_cache if overrides.use_cache is None else overrides.use_cache,
        )

    def begin_generation_command(self, command: GenerationCommand) -> GenerationSession:
        return self.begin_generation(
            command.prompt,
            self.resolve_generation_config(command.overrides),
            backend=command.backend,
            stop_words=list(command.stop_words) if command.stop_words is not None else None,
        )

    def load_checkpoint(
        self,
        checkpoint_path: str,
        backend: Optional[str] = None,
        *,
        require_managed: bool = False,
    ) -> None:
        """Coordinate ownership around one atomic capability checkpoint swap."""
        with self._lock:
            if require_managed:
                checkpoint_path = self._runtime.resolve_checkpoint_path_for_dir(
                    self.checkpoint_dir,
                    checkpoint_path,
                )
            self._generation_admission.ensure_idle(operation="load_checkpoint")
            target_backend = self.current_backend if backend is None else backend.lower().strip()
            target_backend = self._runtime.validate_backend(target_backend)
            target_device = self._runtime.resolve_device_name(self.configured_device)
            previous_residency_device = self._residency_device

            reserved_operation = False
            new_residency_acquired: Optional[str] = None
            residency_committed = False
            if self._accelerator_coordinator is not None:
                self._accelerator_coordinator.reserve_generation(
                    target_device,
                    operation="checkpoint_load",
                )
                reserved_operation = True

            try:
                self._runtime.load_checkpoint(
                    checkpoint_path,
                    vocab_path=self.vocab_path,
                    configured_device=self.configured_device,
                    backend=target_backend,
                )

                next_residency_device: Optional[str] = None
                if same_accelerator_family(target_device, target_device):
                    if previous_residency_device is not None and same_accelerator_family(
                        previous_residency_device,
                        target_device,
                    ):
                        next_residency_device = previous_residency_device
                    elif self._accelerator_coordinator is not None:
                        self._accelerator_coordinator.reserve_inference_residency(target_device)
                        new_residency_acquired = target_device
                        next_residency_device = target_device

                self._residency_device = next_residency_device
                if (
                    previous_residency_device is not None
                    and previous_residency_device != next_residency_device
                    and self._accelerator_coordinator is not None
                ):
                    self._accelerator_coordinator.release_inference_residency(
                        previous_residency_device
                    )
                residency_committed = True
                logger.info(
                    "Đã nạp checkpoint thành công: %s trên %s (Backend: '%s')",
                    checkpoint_path,
                    self.device_str,
                    self.current_backend,
                )
            finally:
                if (
                    new_residency_acquired is not None
                    and not residency_committed
                    and self._accelerator_coordinator is not None
                ):
                    self._accelerator_coordinator.release_inference_residency(
                        new_residency_acquired
                    )
                if reserved_operation and self._accelerator_coordinator is not None:
                    self._accelerator_coordinator.release_generation(target_device)

    def delete_checkpoint(self, filename: str) -> bool:
        with self._lock:
            safe_filename = self._runtime.delete_checkpoint(
                checkpoint_dir=self.checkpoint_dir,
                checkpoint_name=self.checkpoint_name,
                filename=filename,
            )
        logger.info("🗑️ Đã xóa checkpoint: %s", safe_filename)
        return True

    def begin_generation(
        self,
        prompt: str,
        config: GenerationConfig,
        backend: Optional[str] = None,
        stop_words: Optional[List[str]] = None,
    ) -> GenerationSession:
        with self._lock:
            requested_backend = backend.lower().strip() if backend else self.current_backend
            requested_backend = self._runtime.validate_backend(requested_backend)
            if self.generator is None or self.tokenizer is None:
                # Preserve admission semantics: not-ready requests never consume a slot.
                from src.core.exceptions import GenerationNotReadyError

                raise GenerationNotReadyError()
            release = self._generation_admission.acquire(
                prompt=prompt,
                config=config,
                device=self.device_str,
            )
            try:
                return self._runtime.begin_generation(
                    prompt=prompt,
                    config=config,
                    requested_backend=requested_backend,
                    stop_words=stop_words,
                    release_admission=release,
                )
            except Exception:
                release()
                raise

    def stream_generate(
        self,
        prompt: str,
        config: GenerationConfig,
        backend: Optional[str] = None,
        stop_words: Optional[List[str]] = None,
    ) -> Generator[dict[str, object], None, None]:
        session = self.begin_generation(prompt, config, backend=backend, stop_words=stop_words)
        try:
            yield from session.iter_events()
        finally:
            session.close()


def load_generator_from_checkpoint(
    checkpoint_path: str,
    vocab_path: str,
    device: str = "auto",
    backend: str = "local",
):
    """Application compatibility facade over the stable inference capability API."""
    return runtime_load_generator_from_checkpoint(
        checkpoint_path,
        vocab_path,
        device=device,
        backend=backend,
    )
