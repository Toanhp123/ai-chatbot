"""
Inference Service: Quản lý nạp mô hình, hoán đổi checkpoint và điều phối sinh văn bản theo luồng (Streaming).
"""

import math
import os
import threading
import time
from dataclasses import replace
from typing import Any, Callable, Dict, Generator, List, Optional

import torch

from src.core.config import GenerationConfig, ModelConfig
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
from src.ui.services.generation_session import GenerationSession
from src.utils.device import resolve_device

logger = get_logger("InferenceService")


class InferenceService:
    """Service singleton phục vụ suy luận văn bản và quản lý checkpoints cho Web UI."""

    def __init__(
        self,
        checkpoint_dir: str = "checkpoints",
        default_checkpoint: str = "checkpoints/best_model.pt",
        vocab_path: str = "data/vocab.json",
        device: str = "auto",
        backend: str = "local",
        max_generation_sessions: int = 2,
    ) -> None:
        if max_generation_sessions <= 0:
            raise ValueError("max_generation_sessions phải > 0")
        self.checkpoint_dir = checkpoint_dir
        self.current_checkpoint_path: Optional[str] = None
        self.vocab_path = vocab_path
        self.device_str = resolve_device(device)
        self.current_backend: str = backend
        self.tokenizer: Optional[BaseTokenizer] = None
        self.model: Optional[BaseModel] = None
        self.generator: Optional[BaseGenerator] = None
        self._lock = threading.Lock()
        self._max_generation_sessions = max_generation_sessions
        self._generation_sessions = 0
        # Model instances own mutable KV-cache state, so workers execute one at a time.
        self._generation_lock = threading.Lock()

        # Nạp mặc định nếu checkpoint và từ vựng tồn tại
        if os.path.exists(vocab_path):
            try:
                self.tokenizer = load_tokenizer(vocab_path)
            except Exception as e:
                logger.warning(f"Chưa thể nạp tokenizer từ {vocab_path}: {e}")

        if os.path.exists(default_checkpoint):
            try:
                self.load_checkpoint(default_checkpoint)
            except Exception as e:
                logger.warning(f"Chưa thể nạp checkpoint mặc định {default_checkpoint}: {e}")

    def set_checkpoint_dir(self, checkpoint_dir: str) -> None:
        """Update the single checkpoint directory used by list/delete/download flows."""
        if not checkpoint_dir or not checkpoint_dir.strip():
            raise ValueError("checkpoint_dir không được để trống.")
        with self._lock:
            self.checkpoint_dir = checkpoint_dir

    def set_vocab_path(self, vocab_path: str) -> None:
        """Update the vocab source used for future checkpoint loads without disturbing the active model."""
        if not vocab_path or not vocab_path.strip():
            raise ValueError("vocab_path không được để trống.")
        with self._lock:
            self.vocab_path = vocab_path

    def resolve_checkpoint_path(self, path: str, *, filename_only: bool = False) -> str:
        """Resolve a managed checkpoint path without allowing traversal or symlink escape."""
        root = os.path.realpath(os.path.abspath(self.checkpoint_dir))
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

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """Quét và trả về danh sách tất cả checkpoint cùng metadata."""
        checkpoints: List[Dict[str, Any]] = []
        if not os.path.exists(self.checkpoint_dir):
            return checkpoints

        for fname in os.listdir(self.checkpoint_dir):
            if fname.endswith(".pt") or fname.endswith(".pth"):
                try:
                    fpath = self.resolve_checkpoint_path(fname, filename_only=True)
                except ValueError:
                    continue
                if not os.path.isfile(fpath):
                    continue
                stat = os.stat(fpath)
                size_mb = round(stat.st_size / (1024 * 1024), 2)
                modified_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                is_active = os.path.abspath(fpath) == (
                    os.path.abspath(self.current_checkpoint_path)
                    if self.current_checkpoint_path
                    else ""
                )

                # Đọc nhanh metadata nếu có
                step = None
                val_loss = None
                run_name = None
                try:
                    meta = torch.load(fpath, map_location="cpu", weights_only=True)
                    if isinstance(meta, dict):
                        step = meta.get("step")
                        raw_val = meta.get("val_loss")
                        if raw_val is not None:
                            try:
                                v = float(raw_val)
                                if math.isfinite(v):
                                    val_loss = round(v, 4)
                            except (ValueError, TypeError):
                                pass
                        run_name = meta.get("run_name")
                except Exception:
                    pass

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
                    }
                )

        # Xác định val_loss thấp nhất thực tế trên toàn bộ checkpoint
        valid_losses = [c["val_loss"] for c in checkpoints if c.get("val_loss") is not None]
        min_loss = min(valid_losses) if valid_losses else None

        for c in checkpoints:
            c["is_best_val"] = (
                min_loss is not None
                and c.get("val_loss") is not None
                and abs(c["val_loss"] - min_loss) < 1e-5
            )
            fname = c["filename"]
            if fname == "best_model.pt":
                c["tag"] = "best"
            elif fname == "last_model.pt":
                c["tag"] = "canonical_last"
            elif fname.endswith("_last.pt"):
                c["tag"] = "run_last"
            elif "_step" in fname:
                c["tag"] = "top_k"
            else:
                c["tag"] = "custom"

        def _checkpoint_sort_key(x: Dict[str, Any]):
            # best_model.pt luôn được ghim ở đầu bảng (ưu tiên 0 so với 1)
            is_best = 0 if x["filename"] == "best_model.pt" else 1
            mtime = 0.0
            try:
                mtime = time.mktime(time.strptime(x["modified_time"], "%Y-%m-%d %H:%M:%S"))
            except Exception:
                pass
            step = x.get("step") or 0
            # Sắp xếp: best lên trước, sau đó là thời gian mới nhất (mtime giảm dần), step giảm dần
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

    def load_checkpoint(self, checkpoint_path: str, backend: Optional[str] = None) -> None:
        """Nạp checkpoint mới và chỉ commit state sau khi toàn bộ quá trình thành công."""
        with self._lock:
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

            # Stage checkpoint tensors on CPU first. Loading directly onto the active
            # inference device would temporarily duplicate checkpoint + old model + new model
            # in VRAM before the atomic service-state commit.
            checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
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
            accelerator_target = self.device_str != "cpu"
            if accelerator_target and previous_model is not None:
                previous_model.to("cpu")
                previous_model_to_restore = previous_model
                self._empty_accelerator_cache(self.device_str)

            try:
                if isinstance(model, torch.nn.Module):
                    model.to(self.device_str)
                    model.eval()

                generator = GeneratorRegistry.create_for_inference(
                    target_backend,
                    model=model,
                    tokenizer=tokenizer,
                    device=self.device_str,
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
                    self._empty_accelerator_cache(self.device_str)
                    try:
                        previous_model_to_restore.to(self.device_str)
                    except Exception as restore_exc:
                        raise RuntimeError(
                            "Checkpoint swap thất bại và không thể khôi phục model trước đó "
                            "lên inference device."
                        ) from restore_exc
                raise

            # Atomic state commit: failed validation/load above must leave the active service untouched.
            self.tokenizer = tokenizer
            self.model = model
            self.generator = generator
            self.current_backend = target_backend
            self.current_checkpoint_path = checkpoint_path
            logger.info(
                f"Đã nạp checkpoint thành công: {checkpoint_path} trên {self.device_str} (Backend: '{self.current_backend}')"
            )

    def delete_checkpoint(self, filename: str) -> bool:
        """Xóa một checkpoint khỏi thư mục lưu trữ an toàn."""
        with self._lock:
            safe_filename = os.path.basename(filename)
            target_path = self.resolve_checkpoint_path(safe_filename, filename_only=True)
            if not os.path.exists(target_path):
                raise FileNotFoundError(f"Không tìm thấy file checkpoint: {safe_filename}")

            if self.current_checkpoint_path and os.path.abspath(target_path) == os.path.abspath(
                self.current_checkpoint_path
            ):
                raise ValueError("Không thể xóa checkpoint đang được nạp phục vụ suy luận!")

            os.remove(target_path)
            logger.info(f"🗑️ Đã xóa checkpoint: {safe_filename}")
            return True

    def _release_generation_admission(self) -> None:
        with self._lock:
            self._generation_sessions = max(0, self._generation_sessions - 1)

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
            session = GenerationSession(
                generator_provider=generator_provider,
                prompt=prompt,
                config=frozen_config,
                execution_lock=self._generation_lock,
                release_admission=self._release_generation_admission,
            )
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
