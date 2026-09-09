"""Bounded generation-session admission for inference application flows."""

from __future__ import annotations

import threading
from dataclasses import replace
from typing import Callable, Optional

from src.application.inference.session import GenerationSession
from src.application.runtime.accelerator import AcceleratorCoordinator
from src.core.config import GenerationConfig
from src.core.exceptions import EmptyPromptError, GenerationBusyError, GenerationNotReadyError
from src.data.tokenizers import BaseTokenizer
from src.generation import BaseGenerator, GeneratorRegistry
from src.models.base import BaseModel


class GenerationAdmissionManager:
    """Own session limits and accelerator leases, independent of checkpoint/runtime state."""

    def __init__(
        self,
        *,
        max_sessions: int,
        accelerator_coordinator: Optional[AcceleratorCoordinator] = None,
    ) -> None:
        if max_sessions <= 0:
            raise ValueError("max_sessions phải > 0")
        self._max_sessions = max_sessions
        self._accelerator_coordinator = accelerator_coordinator
        self._active_sessions = 0
        self._lock = threading.Lock()

    @property
    def active_sessions(self) -> int:
        with self._lock:
            return self._active_sessions

    @property
    def max_sessions(self) -> int:
        return self._max_sessions

    def ensure_idle(self, *, operation: str) -> None:
        with self._lock:
            active = self._active_sessions
        if active:
            raise GenerationBusyError(
                active=active,
                limit=self._max_sessions,
                operation=operation,
            )

    def _release(self, device: str) -> None:
        with self._lock:
            self._active_sessions = max(0, self._active_sessions - 1)
        if self._accelerator_coordinator is not None:
            self._accelerator_coordinator.release_generation(device)

    def begin(
        self,
        *,
        prompt: str,
        config: GenerationConfig,
        requested_backend: str,
        current_backend: str,
        generator: Optional[BaseGenerator],
        tokenizer: Optional[BaseTokenizer],
        model: Optional[BaseModel],
        device: str,
        execution_lock: threading.Lock,
        stop_words: Optional[list[str]] = None,
    ) -> GenerationSession:
        if not prompt.strip():
            raise EmptyPromptError()
        config.validate()

        requested_generator_cls = GeneratorRegistry.get(requested_backend)
        with self._lock:
            if self._active_sessions >= self._max_sessions:
                raise GenerationBusyError(
                    active=self._active_sessions,
                    limit=self._max_sessions,
                )
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
                device_snapshot = device

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

            if self._accelerator_coordinator is not None:
                self._accelerator_coordinator.reserve_generation(device)

            def release_admission() -> None:
                self._release(device)

            try:
                session = GenerationSession(
                    generator_provider=generator_provider,
                    prompt=prompt,
                    config=frozen_config,
                    execution_lock=execution_lock,
                    release_admission=release_admission,
                )
            except Exception:
                if self._accelerator_coordinator is not None:
                    self._accelerator_coordinator.release_generation(device)
                raise
            self._active_sessions += 1
            return session


__all__ = ["GenerationAdmissionManager"]
