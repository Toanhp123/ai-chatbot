"""Cross-service admission for accelerator ownership.

Training may coexist with CPU inference, but CUDA/MPS training is exclusive against
both active generation work and an inference model that is still resident on that
accelerator. Multiple generation sessions may coexist subject to the inference
service's own bounded-session limit.
"""

from __future__ import annotations

import threading
from typing import Dict

from src.core.exceptions import AcceleratorBusyError


def accelerator_key(device: str) -> str | None:
    """Collapse concrete accelerator devices into the ownership family we coordinate."""
    normalized = (device or "cpu").lower().strip()
    if normalized.startswith("cuda"):
        return "cuda"
    if normalized.startswith("mps"):
        return "mps"
    return None


def same_accelerator_family(first: str, second: str) -> bool:
    """Return True only when both devices use the same coordinated accelerator family."""
    first_key = accelerator_key(first)
    return first_key is not None and first_key == accelerator_key(second)


class AcceleratorCoordinator:
    """Thread-safe ownership coordinator shared by training and inference services."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Dict[str, Dict[str, int | bool]] = {}

    @staticmethod
    def _empty_state() -> Dict[str, int | bool]:
        return {"training": False, "generation": 0, "inference_residency": 0}

    def _cleanup_locked(self, key: str) -> None:
        state = self._state.get(key)
        if state is None:
            return
        if (
            not bool(state["training"])
            and int(state["generation"]) <= 0
            and int(state["inference_residency"]) <= 0
        ):
            self._state.pop(key, None)

    def reserve_training(self, device: str) -> None:
        key = accelerator_key(device)
        if key is None:
            return
        with self._lock:
            state = self._state.setdefault(key, self._empty_state())
            if (
                bool(state["training"])
                or int(state["generation"]) > 0
                or int(state["inference_residency"]) > 0
            ):
                if bool(state["training"]):
                    owner = "training"
                elif int(state["generation"]) > 0:
                    owner = "generation"
                else:
                    owner = "inference_residency"
                raise AcceleratorBusyError(key, owner, "training")
            state["training"] = True

    def release_training(self, device: str) -> None:
        key = accelerator_key(device)
        if key is None:
            return
        with self._lock:
            state = self._state.get(key)
            if state is None:
                return
            state["training"] = False
            self._cleanup_locked(key)

    def reserve_generation(self, device: str, operation: str = "generation") -> None:
        key = accelerator_key(device)
        if key is None:
            return
        with self._lock:
            state = self._state.setdefault(key, self._empty_state())
            if bool(state["training"]):
                raise AcceleratorBusyError(key, "training", operation)
            state["generation"] = int(state["generation"]) + 1

    def release_generation(self, device: str) -> None:
        key = accelerator_key(device)
        if key is None:
            return
        with self._lock:
            state = self._state.get(key)
            if state is None:
                return
            state["generation"] = max(0, int(state["generation"]) - 1)
            self._cleanup_locked(key)

    def reserve_inference_residency(self, device: str) -> None:
        """Hold a lease while inference weights remain resident on CUDA/MPS."""
        key = accelerator_key(device)
        if key is None:
            return
        with self._lock:
            state = self._state.setdefault(key, self._empty_state())
            if bool(state["training"]):
                raise AcceleratorBusyError(key, "training", "inference_residency")
            state["inference_residency"] = int(state["inference_residency"]) + 1

    def release_inference_residency(self, device: str) -> None:
        key = accelerator_key(device)
        if key is None:
            return
        with self._lock:
            state = self._state.get(key)
            if state is None:
                return
            state["inference_residency"] = max(0, int(state["inference_residency"]) - 1)
            self._cleanup_locked(key)

    def snapshot(self) -> Dict[str, Dict[str, int | bool]]:
        with self._lock:
            return {key: dict(value) for key, value in self._state.items()}


__all__ = [
    "AcceleratorBusyError",
    "AcceleratorCoordinator",
    "accelerator_key",
    "same_accelerator_family",
]
