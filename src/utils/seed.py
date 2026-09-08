"""Tiện ích seed và snapshot RNG phục vụ tái lập / resume chính xác."""

import random
from typing import Any, Dict, cast

import numpy as np
import torch


def set_seed(seed: int = 1337, deterministic: bool = True) -> None:
    """Cài đặt seed cho tất cả các thư viện ngẫu nhiên."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False


def capture_rng_state() -> Dict[str, Any]:
    """Capture RNG state using only objects accepted by torch weights-only loading."""
    np_state = cast(
        tuple[str, np.ndarray, int, int, float],
        np.random.get_state(legacy=True),
    )
    state: Dict[str, Any] = {
        "python": random.getstate(),
        "numpy": {
            "bit_generator": np_state[0],
            "state": torch.from_numpy(np_state[1].astype(np.int64, copy=True)),
            "pos": int(np_state[2]),
            "has_gauss": int(np_state[3]),
            "cached_gaussian": float(np_state[4]),
        },
        "torch_cpu": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def restore_rng_state(state: Dict[str, Any]) -> None:
    """Restore a snapshot produced by :func:`capture_rng_state`."""
    python_state = state.get("python")
    if python_state is not None:
        random.setstate(python_state)

    numpy_state = state.get("numpy")
    if isinstance(numpy_state, dict):
        raw_state = numpy_state.get("state")
        if not isinstance(raw_state, torch.Tensor):
            raise ValueError("RNG NumPy state trong checkpoint không hợp lệ.")
        np.random.set_state(
            (
                str(numpy_state.get("bit_generator", "MT19937")),
                raw_state.detach().cpu().numpy().astype(np.uint32, copy=True),
                int(numpy_state.get("pos", 0)),
                int(numpy_state.get("has_gauss", 0)),
                float(numpy_state.get("cached_gaussian", 0.0)),
            )
        )

    torch_cpu = state.get("torch_cpu")
    if isinstance(torch_cpu, torch.Tensor):
        torch.set_rng_state(torch_cpu.detach().cpu())

    torch_cuda = state.get("torch_cuda")
    if torch_cuda is not None and torch.cuda.is_available():
        torch.cuda.set_rng_state_all([item.detach().cpu() for item in torch_cuda])


__all__ = ["set_seed", "capture_rng_state", "restore_rng_state"]
