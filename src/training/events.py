"""Transport-neutral training event fan-out.

The hub owns subscriber buffering and slow-consumer isolation. Lifecycle/state
policy remains in ``TrainingService``; adapters only serialize the dict events.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Generator
from typing import Any


class TrainingEventHub:
    """Broadcast structured training events without coupling Application to SSE."""

    def __init__(self, *, queue_size: int = 500) -> None:
        self._queue_size = queue_size
        self._subscribers: list[queue.Queue[dict[str, Any]]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=self._queue_size)
        with self._lock:
            self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(event)
            except queue.Full:
                # One slow consumer must never block the training worker or peers.
                continue

    def iter_events(
        self,
        snapshot: Callable[[], dict[str, Any]],
        *,
        heartbeat_seconds: float = 1.0,
    ) -> Generator[dict[str, Any], None, None]:
        subscriber = self.subscribe()
        try:
            yield {"type": "init", **snapshot()}
            while True:
                try:
                    yield subscriber.get(timeout=heartbeat_seconds)
                except queue.Empty:
                    yield {"type": "heartbeat", "timestamp": time.time()}
        finally:
            self.unsubscribe(subscriber)


__all__ = ["TrainingEventHub"]
