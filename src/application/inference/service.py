"""
Inference Service: Quản lý nạp mô hình, hoán đổi checkpoint và điều phối sinh văn bản theo luồng (Streaming).
"""

import math
import os
import stat as stat_module
import threading
import time
from dataclasses import replace
from typing import Any, Callable, Dict, Generator, List, Optional

import torch

from src.application.config import ConfigurationService
from src.application.inference.contracts import GenerationCommand, GenerationOverrides
from src.application.inference.session import GenerationSession
from src.application.runtime.accelerator import (
    AcceleratorCoordinator,
    same_accelerator_family,
)
from src.core.config import EngineConfig, GenerationConfig, ModelConfig
from src.core.exceptions import EmptyPromptError, GenerationBusyError, GenerationNotReadyError
from src.core.logging import get_logger
from src.data.tokenizers import BaseTokenizer, load_tokenizer, load_tokenizer_state
from src.data.tokenizers.base import get_tokenizer_identity
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
    ) -> None:
        if max_generation_sessions <= 0:
            raise ValueError("max_generation_sessions phải > 0")
        base_config = EngineConfig()
        canonical_generation = (
            GenerationConfig.from_kwargs_safe(generation_config.to_dict())
            if generation_config is not None
            else GenerationConfig.from_kwargs_safe(base_config.generation.to_dict())
        )
        self._engine_config = ConfigurationService.snapshot(
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
        self._config_service = config_service
        if self._config_service is not None:
            self._config_service.activate(self._engine_config)

        self.current_checkpoint_path: Optional[str] = None
        self._current_checkpoint_identity: Optional[tuple[int, int, int, int]] = None
        self._device_override: Optional[str] = None
        self.device_str = resolve_device(self.configured_device)
        self.current_backend: str = backend
        self._accelerator_coordinator = accelerator_coordinator
        self._residency_device: Optional[str] = None
        self.tokenizer: Optional[BaseTokenizer] = None
        self.model: Optional[BaseModel] = None
        self.generator: Optional[BaseGenerator] = None
        self._lock = threading.Lock()
        self._max_generation_sessions = max_generation_sessions
        self._generation_sessions = 0
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
            checkpoint_dir=config.training.checkpoint_dir,
            checkpoint_name=config.training.checkpoint_name,
            default_checkpoint=os.path.join(
                config.training.checkpoint_dir, config.training.checkpoint_name
            ),
            vocab_path=config.data.vocab_file,
            device=config.system.device,
            backend=backend,
            max_generation_sessions=max_generation_sessions,
            generation_config=config.generation,
            accelerator_coordinator=accelerator_coordinator,
            config_service=config_service,
        )

    def _preference_config(self) -> EngineConfig:
        """Return the one authoritative preference snapshot for future inference work."""
        if self._config_service is not None:
            return self._config_service.current()
        return ConfigurationService.snapshot(self._engine_config)

    def _activate_preference_config(self, config: EngineConfig) -> EngineConfig:
        snapshot = ConfigurationService.snapshot(config)
        self._engine_config = snapshot
        if self._config_service is not None:
            self._config_service.activate(snapshot)
        return snapshot

    @property
    def checkpoint_dir(self) -> str:
        return self._preference_config().training.checkpoint_dir

    @checkpoint_dir.setter
    def checkpoint_dir(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("checkpoint_dir không được để trống.")
        config = self._preference_config()
        self._activate_preference_config(
            config.copy(training=config.training.copy(checkpoint_dir=value))
        )

    @property
    def checkpoint_name(self) -> str:
        return self._preference_config().training.checkpoint_name

    @checkpoint_name.setter
    def checkpoint_name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("checkpoint_name không được để trống.")
        config = self._preference_config()
        self._activate_preference_config(
            config.copy(training=config.training.copy(checkpoint_name=value))
        )

    @property
    def vocab_path(self) -> str:
        return self._preference_config().data.vocab_file

    @vocab_path.setter
    def vocab_path(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("vocab_path không được để trống.")
        config = self._preference_config()
        self._activate_preference_config(config.copy(data=config.data.copy(vocab_file=value)))

    @property
    def configured_device(self) -> str:
        # Explicit device ordinals (for example ``cuda:0``) are runtime placement
        # overrides, not valid persisted SystemConfig values.
        return self._device_override or self._preference_config().system.device

    @configured_device.setter
    def configured_device(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("configured_device không được để trống.")
        self._device_override = value

    @property
    def default_generation_config(self) -> GenerationConfig:
        return GenerationConfig.from_kwargs_safe(self._preference_config().generation.to_dict())

    @default_generation_config.setter
    def default_generation_config(self, value: GenerationConfig) -> None:
        config = self._preference_config()
        generation = GenerationConfig.from_kwargs_safe(value.to_dict())
        self._activate_preference_config(config.copy(generation=generation))

    def apply_engine_config(self, config: EngineConfig) -> None:
        """Activate canonical preferences for future inference operations.

        Loaded runtime artifacts remain untouched; only the shared configuration snapshot
        changes. All compatibility properties derive from that one snapshot.
        """
        config.validate()
        self._device_override = None
        self._activate_preference_config(config)

    def get_engine_config(self) -> EngineConfig:
        """Return a defensive copy of the shared canonical configuration snapshot."""
        return self._preference_config()

    @staticmethod
    def _identity_from_stat(stat_result: os.stat_result) -> tuple[int, int, int, int]:
        return (
            int(stat_result.st_dev),
            int(stat_result.st_ino),
            int(stat_result.st_size),
            int(stat_result.st_mtime_ns),
        )

    @classmethod
    def _checkpoint_identity(cls, path: str) -> tuple[int, int, int, int]:
        return cls._identity_from_stat(os.stat(path))

    @staticmethod
    def _resolve_checkpoint_path_for_dir(
        checkpoint_dir: str, path: str, *, filename_only: bool = False
    ) -> str:
        root = os.path.realpath(os.path.abspath(checkpoint_dir))
        if filename_only:
            candidate = os.path.realpath(os.path.join(root, os.path.basename(path)))
        else:
            candidate = os.path.realpath(os.path.abspath(path))
            if os.path.dirname(path) in {"", "."}:
                candidate = os.path.realpath(os.path.join(root, os.path.basename(path)))
        try:
            if os.path.commonpath([root, candidate]) != root or candidate == root:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Checkpoint phải nằm bên trong checkpoint_dir đã cấu hình.") from exc
        return candidate

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
        """Scan one coherent checkpoint-directory snapshot and return stable file metadata."""
        with self._lock:
            checkpoint_dir = self.checkpoint_dir
            checkpoint_name = self.checkpoint_name
            active_path = self.current_checkpoint_path
            active_identity = self._current_checkpoint_identity

        checkpoints: List[Dict[str, Any]] = []
        if not os.path.exists(checkpoint_dir):
            return checkpoints

        try:
            filenames = os.listdir(checkpoint_dir)
        except OSError:
            return checkpoints

        for fname in filenames:
            if not (fname.endswith(".pt") or fname.endswith(".pth")):
                continue
            try:
                fpath = self._resolve_checkpoint_path_for_dir(
                    checkpoint_dir, fname, filename_only=True
                )
                with open(fpath, "rb") as checkpoint_file:
                    file_stat = os.fstat(checkpoint_file.fileno())
                    if not stat_module.S_ISREG(file_stat.st_mode):
                        continue
                    current_identity = self._identity_from_stat(file_stat)
                    size_mb = round(file_stat.st_size / (1024 * 1024), 2)
                    modified_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(file_stat.st_mtime)
                    )
                    step = None
                    val_loss = None
                    run_name = None
                    try:
                        meta = torch.load(checkpoint_file, map_location="cpu", weights_only=True)
                        if isinstance(meta, dict):
                            step = meta.get("step")
                            raw_val = meta.get("val_loss")
                            if raw_val is not None:
                                try:
                                    value = float(raw_val)
                                    if math.isfinite(value):
                                        val_loss = round(value, 4)
                                except (ValueError, TypeError):
                                    pass
                            run_name = meta.get("run_name")
                    except Exception:
                        pass
            except (OSError, ValueError):
                continue

            is_active = (
                active_path is not None
                and os.path.abspath(fpath) == os.path.abspath(active_path)
                and active_identity == current_identity
            )
            checkpoints.append(
                {
                    "filename": fname,
                    "path": fpath.replace("\\", "/"),
                    "size_mb": size_mb,
                    "modified_time": modified_time,
                    "is_active": is_active,
                    "step": step,
                    "val_loss": val_loss,
                    "run_name": run_name,
                    "is_configured_best": fname == checkpoint_name,
                }
            )

        valid_losses = [c["val_loss"] for c in checkpoints if c.get("val_loss") is not None]
        min_loss = min(valid_losses) if valid_losses else None
        for checkpoint in checkpoints:
            checkpoint["is_best_val"] = (
                min_loss is not None
                and checkpoint.get("val_loss") is not None
                and abs(checkpoint["val_loss"] - min_loss) < 1e-5
            )
            fname = checkpoint["filename"]
            if fname == checkpoint_name:
                checkpoint["tag"] = "best"
            elif fname == "last_model.pt":
                checkpoint["tag"] = "canonical_last"
            elif fname.endswith("_last.pt"):
                checkpoint["tag"] = "run_last"
            elif "_step" in fname:
                checkpoint["tag"] = "top_k"
            else:
                checkpoint["tag"] = "custom"

        def _checkpoint_sort_key(item: Dict[str, Any]):
            is_best = 0 if item["filename"] == checkpoint_name else 1
            mtime = 0.0
            try:
                mtime = time.mktime(time.strptime(item["modified_time"], "%Y-%m-%d %H:%M:%S"))
            except Exception:
                pass
            step = item.get("step") or 0
            return (is_best, -mtime, -step)

        checkpoints.sort(key=_checkpoint_sort_key)
        return checkpoints

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

    def prepare_for_training(self, target_device: str) -> bool:
        """Offload idle inference weights when training needs the same accelerator.

        The checkpoint identity remains active; only its execution residency changes.
        A persistent coordinator residency lease prevents a checkpoint reload from
        silently reoccupying the accelerator between this handoff and training admission.
        """
        with self._lock:
            if not same_accelerator_family(self.device_str, target_device):
                return False
            if self._generation_sessions:
                raise GenerationBusyError(
                    active=self._generation_sessions,
                    limit=self._max_generation_sessions,
                    operation="prepare_training",
                )
            if self.model is None or self.tokenizer is None:
                return False

            previous_device = self.device_str
            previous_generator = self.generator
            model = self.model
            tokenizer = self.tokenizer
            backend = self.current_backend

            if isinstance(model, torch.nn.Module):
                model.to("cpu")
            self._empty_accelerator_cache(previous_device)
            try:
                cpu_generator = GeneratorRegistry.create_for_inference(
                    backend, model=model, tokenizer=tokenizer, device="cpu"
                )
            except Exception:
                try:
                    if isinstance(model, torch.nn.Module):
                        model.to(previous_device)
                finally:
                    self.generator = previous_generator
                raise

            self.generator = cpu_generator
            self.device_str = "cpu"
            residency_device = self._residency_device
            self._residency_device = None
            if residency_device is not None and self._accelerator_coordinator is not None:
                self._accelerator_coordinator.release_inference_residency(residency_device)
            return True

    def set_backend(self, backend: str) -> None:
        """Chuyển đổi generator backend sang một backend khác trong GeneratorRegistry."""
        with self._lock:
            if self._generation_sessions:
                raise GenerationBusyError(
                    active=self._generation_sessions,
                    limit=self._max_generation_sessions,
                    operation="set_backend",
                )
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
            if self._generation_sessions:
                raise GenerationBusyError(
                    active=self._generation_sessions,
                    limit=self._max_generation_sessions,
                    operation="load_checkpoint",
                )
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
                # Stage checkpoint tensors on CPU first. Loading directly onto the active
                # inference device would temporarily duplicate checkpoint + old model + new model
                # in VRAM before the atomic service-state commit.
                with open(checkpoint_path, "rb") as checkpoint_file:
                    loaded_checkpoint_identity = self._identity_from_stat(
                        os.fstat(checkpoint_file.fileno())
                    )
                    checkpoint = torch.load(checkpoint_file, map_location="cpu", weights_only=True)
                checkpoint_identity = checkpoint.get("tokenizer_identity")
                if not isinstance(checkpoint_identity, dict):
                    raise ValueError(
                        "Checkpoint legacy không có tokenizer identity; từ chối nạp để tránh ánh xạ token sai."
                    )
                checkpoint_version = int(checkpoint.get("checkpoint_version", 1))
                embedded_state = checkpoint.get("tokenizer_state")
                if checkpoint_version >= 3 and not isinstance(embedded_state, dict):
                    raise ValueError("Checkpoint v3 thiếu tokenizer state bắt buộc.")
                if isinstance(embedded_state, dict):
                    tokenizer = load_tokenizer_state(embedded_state)
                else:
                    tokenizer = (
                        load_tokenizer(self.vocab_path)
                        if os.path.exists(self.vocab_path)
                        else self.tokenizer
                    )
                if tokenizer is None:
                    raise ValueError(
                        "Không thể nạp checkpoint khi chưa có tokenizer/từ vựng tương ứng."
                    )
                current_identity = get_tokenizer_identity(tokenizer)
                if checkpoint_identity.get("fingerprint") != current_identity.get("fingerprint"):
                    raise ValueError(
                        "Tokenizer/từ vựng hiện tại không khớp tokenizer identity của checkpoint."
                    )

                cfg_dict = checkpoint.get("config", {}).get("model", {})
                model_config = ModelConfig.from_kwargs_safe(cfg_dict, ignore_unknown=True)
                model = ModelRegistry.create(model_config.name, model_config)

                if isinstance(model, torch.nn.Module):
                    model.load_state_dict(checkpoint["model_state_dict"])

                # The checkpoint payload is no longer needed after the CPU model has been
                # populated. Drop it before an accelerator swap to avoid retaining another
                # full copy of the weights in host memory during the handoff.
                del checkpoint

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
        """Xóa một checkpoint khỏi thư mục lưu trữ an toàn."""
        with self._lock:
            safe_filename = os.path.basename(filename)
            target_path = self._resolve_checkpoint_path_for_dir(
                self.checkpoint_dir, safe_filename, filename_only=True
            )
            if not os.path.exists(target_path):
                raise FileNotFoundError(f"Không tìm thấy file checkpoint: {safe_filename}")

            if safe_filename == self.checkpoint_name:
                raise ValueError("Không thể xóa checkpoint tốt nhất đang được cấu hình!")

            if self.current_checkpoint_path and os.path.abspath(target_path) == os.path.abspath(
                self.current_checkpoint_path
            ):
                raise ValueError("Không thể xóa checkpoint đang được nạp phục vụ suy luận!")

            os.remove(target_path)
            logger.info(f"🗑️ Đã xóa checkpoint: {safe_filename}")
            return True

    def _release_generation_admission(self, device: str) -> None:
        with self._lock:
            self._generation_sessions = max(0, self._generation_sessions - 1)
        if self._accelerator_coordinator is not None:
            self._accelerator_coordinator.release_generation(device)

    def begin_generation(
        self,
        prompt: str,
        config: GenerationConfig,
        backend: Optional[str] = None,
        stop_words: Optional[List[str]] = None,
    ) -> GenerationSession:
        """Reserve bounded admission and freeze all mutable inference inputs for one request."""
        if not prompt.strip():
            raise EmptyPromptError()
        config.validate()
        with self._lock:
            current_backend = self.current_backend
            requested_backend = backend.lower().strip() if backend else current_backend
            # Validate request input before admission/readiness so an invalid backend
            # cannot be masked by a transient busy or not-ready service state.
            requested_generator_cls = GeneratorRegistry.get(requested_backend)

            if self._generation_sessions >= self._max_generation_sessions:
                raise GenerationBusyError(
                    active=self._generation_sessions,
                    limit=self._max_generation_sessions,
                )

            generator = self.generator
            tokenizer = self.tokenizer
            model = self.model
            if generator is None or tokenizer is None:
                raise GenerationNotReadyError()
            generator_provider: Callable[[], BaseGenerator]
            if requested_backend == current_backend:
                generator_snapshot = generator

                def current_generator_provider() -> BaseGenerator:
                    return generator_snapshot

                generator_provider = current_generator_provider
            else:
                if model is None:
                    raise GenerationNotReadyError()
                generator_cls_snapshot = requested_generator_cls
                model_snapshot = model
                tokenizer_snapshot = tokenizer
                device_snapshot = self.device_str

                def requested_generator_provider() -> BaseGenerator:
                    return generator_cls_snapshot.from_inference_context(
                        model=model_snapshot,
                        tokenizer=tokenizer_snapshot,
                        device=device_snapshot,
                    )

                generator_provider = requested_generator_provider

            stop_sequences = (
                [list(sequence) for sequence in config.stop_sequences]
                if config.stop_sequences
                else []
            )
            if stop_words:
                stop_sequences.extend(
                    sequence for word in stop_words if word and (sequence := tokenizer.encode(word))
                )
            frozen_config = replace(
                config,
                stop_tokens=list(config.stop_tokens) if config.stop_tokens else None,
                stop_sequences=stop_sequences or None,
            )
            device_snapshot = self.device_str
            if self._accelerator_coordinator is not None:
                self._accelerator_coordinator.reserve_generation(device_snapshot)

            def release_admission() -> None:
                self._release_generation_admission(device_snapshot)

            try:
                session = GenerationSession(
                    generator_provider=generator_provider,
                    prompt=prompt,
                    config=frozen_config,
                    execution_lock=self._generation_lock,
                    release_admission=release_admission,
                )
            except Exception:
                if self._accelerator_coordinator is not None:
                    self._accelerator_coordinator.release_generation(device_snapshot)
                raise
            self._generation_sessions += 1
            return session

    def stream_generate(
        self,
        prompt: str,
        config: GenerationConfig,
        backend: Optional[str] = None,
        stop_words: Optional[List[str]] = None,
    ) -> Generator[str, None, None]:
        """Compatibility generator around the explicit GenerationSession lifecycle."""
        session = self.begin_generation(prompt, config, backend=backend, stop_words=stop_words)
        try:
            yield from session.iter_sse()
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
