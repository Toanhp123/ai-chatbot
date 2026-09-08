"""Central device-resolution policy shared by training and inference composition roots."""

import torch


def _mps_available() -> bool:
    """Return whether PyTorch's Metal backend is usable on this runtime."""
    mps = getattr(torch.backends, "mps", None)
    is_available = getattr(mps, "is_available", None)
    return bool(callable(is_available) and is_available())


def resolve_device(device: str) -> str:
    """Resolve ``auto`` to the best available backend while preserving explicit choices."""
    normalized = device.lower().strip()
    if normalized == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if _mps_available():
            return "mps"
        return "cpu"
    if normalized in {"cuda", "mps", "cpu"}:
        return normalized
    raise ValueError(f"Thiết bị không hợp lệ: {device!r}")


__all__ = ["resolve_device"]
