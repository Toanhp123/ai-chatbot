"""Inner synchronization mechanics shared by application coordinators through ports."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager


class ThreadSynchronization:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    @contextmanager
    def section(self) -> Iterator[None]:
        with self._lock:
            yield


__all__ = ["ThreadSynchronization"]
