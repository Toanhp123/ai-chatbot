"""Bounded generation-session admission policy for inference application flows."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from src.application.runtime.accelerator import AcceleratorCoordinator
from src.core.config import GenerationConfig
from src.core.exceptions import EmptyPromptError, GenerationBusyError


class GenerationAdmissionManager:
    """Own use-case session limits and accelerator leases, not runtime artifacts."""

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

    def acquire(
        self,
        *,
        prompt: str,
        config: GenerationConfig,
        device: str,
    ) -> Callable[[], None]:
        """Reserve one generation slot and return an idempotent release callback."""
        if not prompt.strip():
            raise EmptyPromptError()
        config.validate()

        with self._lock:
            if self._active_sessions >= self._max_sessions:
                raise GenerationBusyError(
                    active=self._active_sessions,
                    limit=self._max_sessions,
                )
            if self._accelerator_coordinator is not None:
                self._accelerator_coordinator.reserve_generation(device)
            self._active_sessions += 1

        release_lock = threading.Lock()
        released = False

        def release() -> None:
            nonlocal released
            with release_lock:
                if released:
                    return
                released = True
            with self._lock:
                self._active_sessions = max(0, self._active_sessions - 1)
            if self._accelerator_coordinator is not None:
                self._accelerator_coordinator.release_generation(device)

        return release


__all__ = ["GenerationAdmissionManager"]
