"""Background execution mechanics owned by the training capability."""

from __future__ import annotations

import threading
from typing import Optional

import torch

from src.training.contracts import BackgroundTarget, BackgroundTask, CancellationSignal


class _ThreadTask:
    def __init__(self, target: BackgroundTarget) -> None:
        self._thread = threading.Thread(target=target, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def join(self, timeout: Optional[float] = None) -> None:
        self._thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        return self._thread.is_alive()


class BackgroundExecution:
    """Own thread/event and accelerator-cache cleanup primitives."""

    @staticmethod
    def create_task(target: BackgroundTarget) -> BackgroundTask:
        return _ThreadTask(target)

    @staticmethod
    def create_cancellation_signal() -> CancellationSignal:
        return threading.Event()

    @staticmethod
    def create_lock():
        return threading.Lock()

    @staticmethod
    def is_current_task(task: BackgroundTask) -> bool:
        if isinstance(task, _ThreadTask):
            return task._thread is threading.current_thread()
        return task is threading.current_thread()

    @staticmethod
    def cleanup_accelerator_cache() -> None:
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass


__all__ = ["BackgroundExecution"]
