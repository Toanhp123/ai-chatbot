"""
Inference Service: Quản lý nạp mô hình, hoán đổi checkpoint và điều phối sinh văn bản theo luồng (Streaming).
"""

import os
import threading
from typing import Any, Dict, Generator, List, Optional

import torch

from src.application.config import ConfigurationService
from src.application.inference.checkpoint_catalog import (
    checkpoint_identity as catalog_checkpoint_identity,
)
from src.application.inference.checkpoint_catalog import (
    delete_checkpoint as catalog_delete_checkpoint,
)
from src.application.inference.checkpoint_catalog import (
    identity_from_stat as catalog_identity_from_stat,
)
from src.application.inference.checkpoint_catalog import (
    list_checkpoints as catalog_list_checkpoints,
)
from src.application.inference.checkpoint_catalog import (
    resolve_checkpoint_path as catalog_resolve_checkpoint_path,
)
from src.application.inference.checkpoint_loader import load_checkpoint_artifacts
from src.application.inference.contracts import (
    GenerationCommand,
    GenerationOverrides,
    InferenceTrainingHandoff,
)
from src.application.inference.generation_admission import GenerationAdmissionManager
from src.application.inference.preferences import InferencePreferences
from src.application.inference.session import GenerationSession
from src.application.runtime.accelerator import (
    AcceleratorCoordinator,
    same_accelerator_family,
)
from src.core.config import EngineConfig, GenerationConfig
from src.core.logging import get_logger
from src.data.tokenizers import BaseTokenizer, load_tokenizer
from src.generation import (
    BaseGenerator,
    GeneratorRegistry,
)
from src.models.base import BaseModel
from src.models.registry import ModelRegistry
from src.utils.device import resolve_device

logger = get_logger("InferenceService")


class InferenceService:
    """Service singleton phục vụ suy luận văn bản và quản lý checkpoints cho Web UI."""

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
        self._preferences = InferencePreferences(
            initial_config,
            config_service=config_service,
        )

        self.current_checkpoint_path: Optional[str] = None
        self._current_checkpoint_identity: Optional[tuple[int, int, int, int]] = None
        self.device_str = resolve_device(self.configured_device)
        self.current_backend: str = backend
        self._accelerator_coordinator = accelerator_coordinator
        self._residency_device: Optional[str] = None
        self.tokenizer: Optional[BaseTokenizer] = None
        self.model: Optional[BaseModel] = None
        self.generator: Optional[BaseGenerator] = None
        self._lock = threading.Lock()
        self._generation_admission = GenerationAdmissionManager(
            max_sessions=max_generation_sessions,
            accelerator_coordinator=accelerator_coordinator,
        )
        # Model instances own mutable KV-cache state, so workers execute one at a time.
        self._generation_lock = threading.Lock()

        if default_checkpoint is None:
            default_checkpoint = self.configured_checkpoint_path

        # Nạp mặc định nếu checkpoint và từ vựng tồn tại
        if os.path.exists(self.vocab_path):
            try:
                self.tokenizer = load_tokenizer(self.vocab_path)
            except Exception as e:
                logger.warning(f"Chưa thể nạp tokenizer từ {self.vocab_path}: {e}")

        if os.path.exists(default_checkpoint):
            try:
                self.load_checkpoint(default_checkpoint)
            except Exception as e:
                logger.warning(f"Chưa thể nạp checkpoint mặc định {default_checkpoint}: {e}")

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
        """Build inference preferences from the same canonical EngineConfig used by training."""
        return cls(
            default_checkpoint=os.path.join(
                config.training.checkpoint_dir, config.training.checkpoint_name
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

    def apply_engine_config(self, config: EngineConfig) -> None:
        """Activate canonical preferences without mutating loaded runtime artifacts."""
        self._preferences.apply_engine_config(config)

    def get_engine_config(self) -> EngineConfig:
        return self._preferences.snapshot()

    @staticmethod
    def _identity_from_stat(stat_result: os.stat_result) -> tuple[int, int, int, int]:
        return catalog_identity_from_stat(stat_result)

    @staticmethod
    def _checkpoint_identity(path: str) -> tuple[int, int, int, int]:
        return catalog_checkpoint_identity(path)

    @staticmethod
    def _resolve_checkpoint_path_for_dir(
        checkpoint_dir: str, path: str, *, filename_only: bool = False
    ) -> str:
        return catalog_resolve_checkpoint_path(checkpoint_dir, path, filename_only=filename_only)

    def get_runtime_state(self) -> Dict[str, Any]:
        """Return authoritative inference preferences and the loaded artifact revision."""
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
        """Update the canonical checkpoint directory used by future inference operations."""
        self.checkpoint_dir = checkpoint_dir

    def set_vocab_path(self, vocab_path: str) -> None:
        """Update the canonical vocab source without disturbing the active model."""
        self.vocab_path = vocab_path

    @property
    def configured_checkpoint_path(self) -> str:
        """Return the canonical configured checkpoint artifact path."""
        return os.path.join(self.checkpoint_dir, self.checkpoint_name)

    def resolve_checkpoint_path(self, path: str, *, filename_only: bool = False) -> str:
        """Resolve a managed checkpoint path without allowing traversal or symlink escape."""
        with self._lock:
            checkpoint_dir = self.checkpoint_dir
        return self._resolve_checkpoint_path_for_dir(
            checkpoint_dir, path, filename_only=filename_only
        )

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """Return checkpoint metadata from one coherent runtime/config snapshot."""
        with self._lock:
            return catalog_list_checkpoints(
                checkpoint_dir=self.checkpoint_dir,
                checkpoint_name=self.checkpoint_name,
                active_path=self.current_checkpoint_path,
                active_identity=self._current_checkpoint_identity,
            )

    def list_generators(self) -> List[str]:
        """Danh sách tất cả các generator backend đã đăng ký trong GeneratorRegistry."""
        return GeneratorRegistry.list_generators()

    @staticmethod
    def _empty_accelerator_cache(device: str) -> None:
        """Best-effort allocator cleanup after moving inference models off an accelerator."""
        if device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()
            return
        if device.startswith("mps"):
            mps = getattr(torch, "mps", None)
            empty_cache = getattr(mps, "empty_cache", None)
            if callable(empty_cache):
                empty_cache()

    def prepare_for_training(self, target_device: str) -> InferenceTrainingHandoff:
        """Create a reversible inference-to-training runtime handoff.

        When inference owns the same coordinated accelerator, residency is converted to
        training ownership atomically while this service lock is held. The caller may
        roll the handoff back until background training accepts ownership.
        """
        with self._lock:
            if not same_accelerator_family(self.device_str, target_device):
                return InferenceTrainingHandoff()
            self._generation_admission.ensure_idle(operation="prepare_training")
            if self.model is None or self.tokenizer is None:
                return InferenceTrainingHandoff()

            previous_device = self.device_str
            previous_generator = self.generator
            model = self.model
            tokenizer = self.tokenizer
            backend = self.current_backend
            residency_device = self._residency_device
            admission_transferred = False

            if isinstance(model, torch.nn.Module):
                model.to("cpu")
            self._empty_accelerator_cache(previous_device)
            try:
                cpu_generator = GeneratorRegistry.create_for_inference(
                    backend, model=model, tokenizer=tokenizer, device="cpu"
                )
                if residency_device is not None and self._accelerator_coordinator is not None:
                    self._accelerator_coordinator.transfer_inference_to_training(residency_device)
                    admission_transferred = True
            except Exception:
                try:
                    if isinstance(model, torch.nn.Module):
                        model.to(previous_device)
                finally:
                    self.generator = previous_generator
                raise

            self.generator = cpu_generator
            self.device_str = "cpu"
            self._residency_device = None

            def rollback() -> None:
                with self._lock:
                    if self.model is not model or self.device_str != "cpu":
                        return
                    restored_residency = False
                    if admission_transferred and self._accelerator_coordinator is not None:
                        self._accelerator_coordinator.transfer_training_to_inference(
                            previous_device
                        )
                        restored_residency = True
                    try:
                        if isinstance(model, torch.nn.Module):
                            model.to(previous_device)
                    except Exception:
                        if restored_residency and self._accelerator_coordinator is not None:
                            self._accelerator_coordinator.release_inference_residency(
                                previous_device
                            )
                        raise
                    self.generator = previous_generator
                    self.device_str = previous_device
                    self._residency_device = residency_device if restored_residency else None

            return InferenceTrainingHandoff(
                training_admission_reserved=admission_transferred,
                rollback=rollback,
            )

    def set_backend(self, backend: str) -> None:
        """Chuyển đổi generator backend sang một backend khác trong GeneratorRegistry."""
        with self._lock:
            self._generation_admission.ensure_idle(operation="set_backend")
            backend_clean = backend.lower().strip()
            # Luôn xác thực tên backend, kể cả khi model/tokenizer chưa được nạp.
            # Nếu không, UI có thể lưu một backend không tồn tại và chỉ lỗi muộn
            # ở lần load checkpoint/generate tiếp theo.
            GeneratorRegistry.get(backend_clean)
            if self.model is not None and self.tokenizer is not None:
                self.generator = GeneratorRegistry.create_for_inference(
                    backend_clean,
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=self.device_str,
                )
            self.current_backend = backend_clean
            logger.info(f"Đã chuyển đổi Generator backend sang: '{backend_clean}'")

    def list_models(self) -> List[str]:
        """Return registered model architectures through the application boundary."""
        return ModelRegistry.list_models()

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
        """Load a checkpoint and atomically publish it only after validation succeeds."""
        with self._lock:
            if require_managed:
                checkpoint_path = self._resolve_checkpoint_path_for_dir(
                    self.checkpoint_dir, checkpoint_path
                )
            self._generation_admission.ensure_idle(operation="load_checkpoint")
            target_backend = self.current_backend
            if backend:
                target_backend = backend.lower().strip()
            GeneratorRegistry.get(target_backend)

            if not os.path.exists(checkpoint_path):
                raise FileNotFoundError(f"Không tìm thấy file checkpoint: {checkpoint_path}")

            target_device = resolve_device(self.configured_device)
            reserved_accelerator = False
            new_residency_acquired: Optional[str] = None
            residency_committed = False
            previous_residency_device = self._residency_device
            if self._accelerator_coordinator is not None:
                self._accelerator_coordinator.reserve_generation(
                    target_device, operation="checkpoint_load"
                )
                reserved_accelerator = True

            try:
                # Materialize and validate CPU artifacts before touching the active runtime.
                artifacts = load_checkpoint_artifacts(
                    checkpoint_path,
                    vocab_path=self.vocab_path,
                    fallback_tokenizer=self.tokenizer,
                )
                loaded_checkpoint_identity = artifacts.identity
                tokenizer = artifacts.tokenizer
                model = artifacts.model

                previous_model = self.model
                previous_model_to_restore: Optional[BaseModel] = None
                previous_device = self.device_str
                previous_was_accelerator_resident = same_accelerator_family(
                    previous_device, previous_device
                )
                if previous_was_accelerator_resident and previous_model is not None:
                    previous_model.to("cpu")
                    previous_model_to_restore = previous_model
                    self._empty_accelerator_cache(previous_device)

                try:
                    if isinstance(model, torch.nn.Module):
                        model.to(target_device)
                        model.eval()

                    generator = GeneratorRegistry.create_for_inference(
                        target_backend,
                        model=model,
                        tokenizer=tokenizer,
                        device=target_device,
                    )
                except Exception:
                    if previous_model_to_restore is not None:
                        if isinstance(model, torch.nn.Module):
                            try:
                                model.to("cpu")
                            except Exception as cleanup_exc:
                                logger.warning(
                                    "Không thể offload model mới sau khi checkpoint swap lỗi: %s",
                                    cleanup_exc,
                                )
                        self._empty_accelerator_cache(target_device)
                        try:
                            previous_model_to_restore.to(previous_device)
                        except Exception as restore_exc:
                            raise RuntimeError(
                                "Checkpoint swap thất bại và không thể khôi phục model trước đó "
                                "lên inference device."
                            ) from restore_exc
                    raise

                next_residency_device: Optional[str] = None
                if same_accelerator_family(target_device, target_device):
                    if previous_residency_device is not None and same_accelerator_family(
                        previous_residency_device, target_device
                    ):
                        next_residency_device = previous_residency_device
                    elif self._accelerator_coordinator is not None:
                        self._accelerator_coordinator.reserve_inference_residency(target_device)
                        new_residency_acquired = target_device
                        next_residency_device = target_device

                # Atomic state commit: failed validation/load above must leave the active service untouched.
                self.tokenizer = tokenizer
                self.model = model
                self.generator = generator
                self.current_backend = target_backend
                self.current_checkpoint_path = checkpoint_path
                self._current_checkpoint_identity = loaded_checkpoint_identity
                self.device_str = target_device
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
                    f"Đã nạp checkpoint thành công: {checkpoint_path} trên {self.device_str} (Backend: '{self.current_backend}')"
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
                if reserved_accelerator and self._accelerator_coordinator is not None:
                    self._accelerator_coordinator.release_generation(target_device)

    def delete_checkpoint(self, filename: str) -> bool:
        """Delete one managed checkpoint while protecting configured/active artifacts."""
        with self._lock:
            safe_filename = catalog_delete_checkpoint(
                checkpoint_dir=self.checkpoint_dir,
                checkpoint_name=self.checkpoint_name,
                filename=filename,
                active_path=self.current_checkpoint_path,
            )
            logger.info(f"🗑️ Đã xóa checkpoint: {safe_filename}")
            return True

    def begin_generation(
        self,
        prompt: str,
        config: GenerationConfig,
        backend: Optional[str] = None,
        stop_words: Optional[List[str]] = None,
    ) -> GenerationSession:
        """Freeze one runtime snapshot and delegate bounded session admission."""
        with self._lock:
            current_backend = self.current_backend
            requested_backend = backend.lower().strip() if backend else current_backend
            return self._generation_admission.begin(
                prompt=prompt,
                config=config,
                requested_backend=requested_backend,
                current_backend=current_backend,
                generator=self.generator,
                tokenizer=self.tokenizer,
                model=self.model,
                device=self.device_str,
                execution_lock=self._generation_lock,
                stop_words=stop_words,
            )

    def stream_generate(
        self,
        prompt: str,
        config: GenerationConfig,
        backend: Optional[str] = None,
        stop_words: Optional[List[str]] = None,
    ) -> Generator[dict[str, object], None, None]:
        """Compatibility event generator around the explicit GenerationSession lifecycle."""
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
    """Compatibility/use-case facade backed by the same checkpoint loader as Web inference."""
    checkpoint_dir = os.path.dirname(os.path.abspath(checkpoint_path)) or "."
    service = InferenceService(
        checkpoint_dir=checkpoint_dir,
        default_checkpoint=os.path.join(checkpoint_dir, "__no_auto_load__.pt"),
        vocab_path=vocab_path,
        device=device,
        backend=backend,
    )
    service.load_checkpoint(checkpoint_path, backend=backend)
    if service.generator is None:
        raise RuntimeError("Checkpoint đã nạp nhưng không tạo được generator.")
    return service.generator
