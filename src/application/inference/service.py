"""Inference use-case orchestration.

Application owns preferences and cross-use-case policy. Concrete checkpoint,
model, generator, session, admission, resource and synchronization mechanics are
supplied through Application-owned ports by the composition root.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Optional

from src.application.config.service import ConfigurationService
from src.application.inference.contracts import (
    GenerationAdmissionPort,
    GenerationCommand,
    GenerationOverrides,
    GenerationStream,
    InferenceRuntimePort,
    InferenceTrainingHandoff,
)
from src.application.inference.preferences import InferencePreferences
from src.application.runtime import AcceleratorPort, SynchronizationPort, same_accelerator_family
from src.core.config import EngineConfig, GenerationConfig
from src.core.exceptions import GenerationNotReadyError
from src.core.logging import get_logger

logger = get_logger("InferenceService")


class InferenceService:
    """Stable Application gateway for inference use cases."""

    def __init__(
        self,
        *,
        runtime: InferenceRuntimePort,
        admission: GenerationAdmissionPort,
        synchronization: SynchronizationPort,
        engine_config: Optional[EngineConfig] = None,
        accelerator: Optional[AcceleratorPort] = None,
        config_service: Optional[ConfigurationService] = None,
        default_checkpoint: Optional[str] = None,
    ) -> None:
        initial_config = ConfigurationService.snapshot(engine_config or EngineConfig())
        self._preferences = InferencePreferences(initial_config, config_service=config_service)
        self._runtime = runtime
        self._admission = admission
        self._synchronization = synchronization
        self._accelerator = accelerator
        self._residency_device: Optional[str] = None

        checkpoint = default_checkpoint or self.configured_checkpoint_path
        try:
            self._runtime.load_tokenizer_if_present(self.vocab_path)
        except Exception as exc:
            logger.warning("Chưa thể nạp tokenizer từ %s: %s", self.vocab_path, exc)

        if self._runtime.path_exists(checkpoint):
            try:
                self.load_checkpoint(checkpoint)
            except Exception as exc:
                logger.warning("Chưa thể nạp checkpoint mặc định %s: %s", checkpoint, exc)

    @classmethod
    def from_engine_config(
        cls,
        config: EngineConfig,
        *,
        runtime: InferenceRuntimePort,
        admission: GenerationAdmissionPort,
        synchronization: SynchronizationPort,
        accelerator: Optional[AcceleratorPort] = None,
        config_service: Optional[ConfigurationService] = None,
    ) -> "InferenceService":
        return cls(
            runtime=runtime,
            admission=admission,
            synchronization=synchronization,
            engine_config=config,
            accelerator=accelerator,
            config_service=config_service,
            default_checkpoint=runtime.join_path(
                config.training.checkpoint_dir,
                config.training.checkpoint_name,
            ),
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

    @property
    def current_checkpoint_path(self) -> Optional[str]:
        return self._runtime.current_checkpoint_path

    @property
    def current_checkpoint_identity(self) -> Optional[tuple[int, int, int, int]]:
        return self._runtime.current_checkpoint_identity

    @property
    def device_str(self) -> str:
        return self._runtime.device

    @property
    def current_backend(self) -> str:
        return self._runtime.backend

    def apply_engine_config(self, config: EngineConfig) -> None:
        self._preferences.apply_engine_config(config)

    def get_engine_config(self) -> EngineConfig:
        return self._preferences.snapshot()

    def get_runtime_state(self) -> dict[str, object]:
        with self._synchronization.section():
            active_path = self.current_checkpoint_path
            active_identity = self.current_checkpoint_identity
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
        return self._runtime.join_path(self.checkpoint_dir, self.checkpoint_name)

    def resolve_checkpoint_path(self, path: str, *, filename_only: bool = False) -> str:
        return self._runtime.resolve_checkpoint_path_for_dir(
            self.checkpoint_dir,
            path,
            filename_only=filename_only,
        )

    def list_checkpoints(self) -> list[dict[str, object]]:
        return self._runtime.list_checkpoints(
            checkpoint_dir=self.checkpoint_dir,
            checkpoint_name=self.checkpoint_name,
        )

    def list_generators(self) -> list[str]:
        return self._runtime.list_generators()

    def list_models(self) -> list[str]:
        return self._runtime.list_models()

    def prepare_for_training(self, target_device: str) -> InferenceTrainingHandoff:
        """Coordinate a reversible inference-residency to training-ownership handoff."""
        with self._synchronization.section():
            if not same_accelerator_family(self.device_str, target_device):
                return InferenceTrainingHandoff()
            self._admission.ensure_idle(operation="prepare_training")
            if not self._runtime.ready:
                return InferenceTrainingHandoff()

            residency_device = self._residency_device
            runtime_handoff = self._runtime.prepare_training_handoff()
            if runtime_handoff is None:
                return InferenceTrainingHandoff()
            previous_device = runtime_handoff.previous_device
            transferred = False
            try:
                if residency_device is not None and self._accelerator is not None:
                    self._accelerator.transfer_inference_to_training(residency_device)
                    transferred = True
            except Exception:
                runtime_handoff.rollback()
                raise
            self._residency_device = None

            def rollback() -> None:
                with self._synchronization.section():
                    restored = False
                    if transferred and self._accelerator is not None:
                        self._accelerator.transfer_training_to_inference(previous_device)
                        restored = True
                    try:
                        runtime_handoff.rollback()
                    except Exception:
                        if restored and self._accelerator is not None:
                            self._accelerator.release_inference_residency(previous_device)
                        raise
                    self._residency_device = residency_device if restored else None

            return InferenceTrainingHandoff(
                training_admission_reserved=transferred,
                rollback_action=rollback,
            )

    def set_backend(self, backend: str) -> None:
        with self._synchronization.section():
            self._admission.ensure_idle(operation="set_backend")
            cleaned = self._runtime.set_backend(backend)
        logger.info("Đã chuyển đổi Generator backend sang: '%s'", cleaned)

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

    def begin_generation_command(self, command: GenerationCommand) -> GenerationStream:
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
        """Coordinate resource ownership around one atomic capability checkpoint swap."""
        with self._synchronization.section():
            if require_managed:
                checkpoint_path = self._runtime.resolve_checkpoint_path_for_dir(
                    self.checkpoint_dir,
                    checkpoint_path,
                )
            self._admission.ensure_idle(operation="load_checkpoint")
            target_backend = self.current_backend if backend is None else backend.lower().strip()
            target_backend = self._runtime.validate_backend(target_backend)
            target_device = self._runtime.resolve_device_name(self.configured_device)
            previous_residency = self._residency_device

            reserved_operation = False
            new_residency: Optional[str] = None
            residency_committed = False
            if self._accelerator is not None:
                self._accelerator.reserve_generation(target_device, operation="checkpoint_load")
                reserved_operation = True

            try:
                self._runtime.load_checkpoint(
                    checkpoint_path,
                    vocab_path=self.vocab_path,
                    configured_device=self.configured_device,
                    backend=target_backend,
                )

                next_residency: Optional[str] = None
                if same_accelerator_family(target_device, target_device):
                    if previous_residency is not None and same_accelerator_family(
                        previous_residency,
                        target_device,
                    ):
                        next_residency = previous_residency
                    elif self._accelerator is not None:
                        self._accelerator.reserve_inference_residency(target_device)
                        new_residency = target_device
                        next_residency = target_device

                self._residency_device = next_residency
                if (
                    previous_residency is not None
                    and previous_residency != next_residency
                    and self._accelerator is not None
                ):
                    self._accelerator.release_inference_residency(previous_residency)
                residency_committed = True
                logger.info(
                    "Đã nạp checkpoint thành công: %s trên %s (Backend: '%s')",
                    checkpoint_path,
                    self.device_str,
                    self.current_backend,
                )
            finally:
                if (
                    new_residency is not None
                    and not residency_committed
                    and self._accelerator is not None
                ):
                    self._accelerator.release_inference_residency(new_residency)
                if reserved_operation and self._accelerator is not None:
                    self._accelerator.release_generation(target_device)

    def delete_checkpoint(self, filename: str) -> bool:
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
        stop_words: Optional[list[str]] = None,
    ) -> GenerationStream:
        with self._synchronization.section():
            requested_backend = backend.lower().strip() if backend else self.current_backend
            requested_backend = self._runtime.validate_backend(requested_backend)
            if not self._runtime.ready:
                raise GenerationNotReadyError()
            release = self._admission.acquire(
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
        stop_words: Optional[list[str]] = None,
    ) -> Generator[dict[str, object], None, None]:
        session = self.begin_generation(prompt, config, backend=backend, stop_words=stop_words)
        try:
            yield from session.iter_events()
        finally:
            session.close()
