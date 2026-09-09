"""Application-owned ports for runtime resource coordination."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol


class SynchronizationPort(Protocol):
    def section(self) -> AbstractContextManager[None]: ...


class AcceleratorPort(Protocol):
    def reserve_training(self, device: str) -> None: ...
    def release_training(self, device: str) -> None: ...
    def reserve_generation(self, device: str, operation: str = "generation") -> None: ...
    def release_generation(self, device: str) -> None: ...
    def reserve_inference_residency(self, device: str) -> None: ...
    def release_inference_residency(self, device: str) -> None: ...
    def transfer_inference_to_training(self, device: str) -> None: ...
    def transfer_training_to_inference(self, device: str) -> None: ...


def same_accelerator_family(first: str, second: str) -> bool:
    """Application policy helper for whether two targets compete for one family."""

    def key(device: str) -> str | None:
        normalized = (device or "cpu").lower().strip()
        if normalized.startswith("cuda"):
            return "cuda"
        if normalized.startswith("mps"):
            return "mps"
        return None

    first_key = key(first)
    return first_key is not None and first_key == key(second)


__all__ = ["AcceleratorPort", "SynchronizationPort", "same_accelerator_family"]
