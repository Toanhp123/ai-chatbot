"""Inference capability runtime mechanics.

This module owns checkpoint I/O/materialization, device movement, generator
construction and generation worker/session mechanics. Application services may
coordinate these operations only through :mod:`src.inference.api`.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import torch

from src.core.config import GenerationConfig
from src.core.exceptions import GenerationNotReadyError
from src.core.logging import get_logger
from src.data.api import BaseTokenizer, load_tokenizer
from src.generation.api import (
    BaseGenerator,
    create_generator_for_inference,
    list_generators,
    validate_generator_backend,
)
from src.models.api import BaseModel, list_models
from src.utils.device import resolve_device

from .checkpoint_catalog import (
    checkpoint_identity,
    delete_checkpoint,
    identity_from_stat,
    list_checkpoints,
    resolve_checkpoint_path,
)
from .checkpoint_loader import load_checkpoint_artifacts
from .session import GenerationSession

logger = get_logger("InferenceRuntime")


@dataclass(frozen=True)
class RuntimeTrainingHandoff:
    """Reversible runtime-only offload performed before cross-use-case ownership transfer."""

    previous_device: str
    rollback: Callable[[], None]


class InferenceRuntime:
    """Own mutable inference artifacts and all concrete runtime mechanics."""

    def __init__(self, *, device: str = "auto", backend: str = "local") -> None:
        self.current_checkpoint_path: Optional[str] = None
        self.current_checkpoint_identity: Optional[tuple[int, int, int, int]] = None
        self.device: str = resolve_device(device)
        self.backend: str = validate_generator_backend(backend)
        self.tokenizer: Optional[BaseTokenizer] = None
        self.model: Optional[BaseModel] = None
        self.generator: Optional[BaseGenerator] = None
        self._generation_lock = threading.Lock()
        self._lock = threading.RLock()

    @staticmethod
    def path_exists(path: str) -> bool:
        return os.path.exists(path)

    @staticmethod
    def join_path(*parts: str) -> str:
        return os.path.join(*parts)

    @staticmethod
    def dirname(path: str) -> str:
        return os.path.dirname(os.path.abspath(path)) or "."

    @staticmethod
    def resolve_device_name(device: str) -> str:
        return resolve_device(device)

    @staticmethod
    def identity_from_stat(stat_result: os.stat_result) -> tuple[int, int, int, int]:
        return identity_from_stat(stat_result)

    @staticmethod
    def checkpoint_identity(path: str) -> tuple[int, int, int, int]:
        return checkpoint_identity(path)

    @staticmethod
    def resolve_checkpoint_path_for_dir(
        checkpoint_dir: str,
        path: str,
        *,
        filename_only: bool = False,
    ) -> str:
        return resolve_checkpoint_path(checkpoint_dir, path, filename_only=filename_only)

    def load_tokenizer_if_present(self, vocab_path: str) -> bool:
        if not os.path.exists(vocab_path):
            return False
        with self._lock:
            self.tokenizer = load_tokenizer(vocab_path)
        return True

    def list_checkpoints(
        self,
        *,
        checkpoint_dir: str,
        checkpoint_name: str,
    ) -> list[dict[str, object]]:
        with self._lock:
            return list_checkpoints(
                checkpoint_dir=checkpoint_dir,
                checkpoint_name=checkpoint_name,
                active_path=self.current_checkpoint_path,
                active_identity=self.current_checkpoint_identity,
            )

    def delete_checkpoint(
        self,
        *,
        checkpoint_dir: str,
        checkpoint_name: str,
        filename: str,
    ) -> str:
        with self._lock:
            return delete_checkpoint(
                checkpoint_dir=checkpoint_dir,
                checkpoint_name=checkpoint_name,
                filename=filename,
                active_path=self.current_checkpoint_path,
            )

    @staticmethod
    def list_generators() -> list[str]:
        return list_generators()

    @staticmethod
    def list_models() -> list[str]:
        return list_models()

    @staticmethod
    def validate_backend(backend: str) -> str:
        return validate_generator_backend(backend)

    @staticmethod
    def _empty_accelerator_cache(device: str) -> None:
        if device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()
            return
        if device.startswith("mps"):
            mps = getattr(torch, "mps", None)
            empty_cache = getattr(mps, "empty_cache", None)
            if callable(empty_cache):
                empty_cache()

    @staticmethod
    def _is_accelerator(device: str) -> bool:
        normalized = (device or "cpu").lower().strip()
        return normalized.startswith("cuda") or normalized.startswith("mps")

    @property
    def ready(self) -> bool:
        with self._lock:
            return (
                self.model is not None and self.tokenizer is not None and self.generator is not None
            )

    def set_backend(self, backend: str) -> str:
        cleaned = self.validate_backend(backend)
        with self._lock:
            if self.model is not None and self.tokenizer is not None:
                self.generator = create_generator_for_inference(
                    cleaned,
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=self.device,
                )
            self.backend = cleaned
        return cleaned

    def load_checkpoint(
        self,
        checkpoint_path: str,
        *,
        vocab_path: str,
        configured_device: str,
        backend: str,
    ) -> tuple[int, int, int, int]:
        """Materialize, validate, move and atomically publish one checkpoint."""
        target_backend = self.validate_backend(backend)
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Không tìm thấy file checkpoint: {checkpoint_path}")
        target_device = resolve_device(configured_device)

        with self._lock:
            artifacts = load_checkpoint_artifacts(
                checkpoint_path,
                vocab_path=vocab_path,
                fallback_tokenizer=self.tokenizer,
            )
            tokenizer = artifacts.tokenizer
            model = artifacts.model
            previous_model = self.model
            previous_device = self.device
            previous_model_to_restore: Optional[BaseModel] = None

            if self._is_accelerator(previous_device) and previous_model is not None:
                previous_model.to("cpu")
                previous_model_to_restore = previous_model
                self._empty_accelerator_cache(previous_device)

            try:
                model.to(target_device)
                model.eval()
                generator = create_generator_for_inference(
                    target_backend,
                    model=model,
                    tokenizer=tokenizer,
                    device=target_device,
                )
            except Exception:
                if previous_model_to_restore is not None:
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

            self.tokenizer = tokenizer
            self.model = model
            self.generator = generator
            self.backend = target_backend
            self.current_checkpoint_path = checkpoint_path
            self.current_checkpoint_identity = artifacts.identity
            self.device = target_device
            return artifacts.identity

    def prepare_training_handoff(self) -> Optional[RuntimeTrainingHandoff]:
        """Offload active inference artifacts to CPU and return a reversible runtime token."""
        with self._lock:
            if self.model is None or self.tokenizer is None:
                return None
            previous_device = self.device
            previous_generator = self.generator
            model = self.model
            tokenizer = self.tokenizer
            backend = self.backend

            model.to("cpu")
            self._empty_accelerator_cache(previous_device)
            try:
                cpu_generator = create_generator_for_inference(
                    backend,
                    model=model,
                    tokenizer=tokenizer,
                    device="cpu",
                )
            except Exception:
                model.to(previous_device)
                self.generator = previous_generator
                raise

            self.generator = cpu_generator
            self.device = "cpu"

        rollback_lock = threading.Lock()
        rolled_back = False

        def rollback() -> None:
            nonlocal rolled_back
            with rollback_lock:
                if rolled_back:
                    return
                rolled_back = True
            with self._lock:
                if self.model is not model or self.device != "cpu":
                    return
                model.to(previous_device)
                self.generator = previous_generator
                self.device = previous_device

        return RuntimeTrainingHandoff(previous_device=previous_device, rollback=rollback)

    def begin_generation(
        self,
        *,
        prompt: str,
        config: GenerationConfig,
        requested_backend: str,
        stop_words: Optional[Sequence[str]],
        release_admission: Callable[[], None],
    ) -> GenerationSession:
        """Freeze runtime artifacts and build one bounded generation session."""
        requested_backend = self.validate_backend(requested_backend)
        with self._lock:
            if self.generator is None or self.tokenizer is None:
                raise GenerationNotReadyError()
            tokenizer = self.tokenizer
            current_backend = self.backend
            device = self.device

            if requested_backend == current_backend:
                generator_snapshot = self.generator

                def generator_provider() -> BaseGenerator:
                    return generator_snapshot

            else:
                if self.model is None:
                    raise GenerationNotReadyError()
                model_snapshot = self.model
                tokenizer_snapshot = tokenizer
                device_snapshot = device

                def generator_provider() -> BaseGenerator:
                    return create_generator_for_inference(
                        requested_backend,
                        model=model_snapshot,
                        tokenizer=tokenizer_snapshot,
                        device=device_snapshot,
                    )

            stop_sequences = (
                [list(sequence) for sequence in config.stop_sequences]
                if config.stop_sequences
                else []
            )
            if stop_words:
                stop_sequences.extend(
                    sequence for word in stop_words if word and (sequence := tokenizer.encode(word))
                )
            frozen_config = config.copy(stop_sequences=stop_sequences or None)
            return GenerationSession(
                generator_provider=generator_provider,
                prompt=prompt,
                config=frozen_config,
                execution_lock=self._generation_lock,
                release_admission=release_admission,
            )


def load_generator_from_checkpoint(
    checkpoint_path: str,
    vocab_path: str,
    *,
    device: str = "auto",
    backend: str = "local",
) -> BaseGenerator:
    """Capability helper for one-off CLI compatibility loading."""
    runtime = InferenceRuntime(device=device, backend=backend)
    runtime.load_checkpoint(
        checkpoint_path,
        vocab_path=vocab_path,
        configured_device=device,
        backend=backend,
    )
    if runtime.generator is None:
        raise RuntimeError("Checkpoint đã nạp nhưng không tạo được generator.")
    return runtime.generator


__all__ = [
    "InferenceRuntime",
    "RuntimeTrainingHandoff",
    "load_generator_from_checkpoint",
]
