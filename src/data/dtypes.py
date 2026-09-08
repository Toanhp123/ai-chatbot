"""Shared NumPy dtype validation for binary token dataset persistence."""

from typing import Any

import numpy as np

from src.core.exceptions import DataPipelineError


def resolve_numpy_dtype(dtype: str) -> Any:
    """Resolve an integer NumPy dtype suitable for token IDs."""
    try:
        resolved = np.dtype(dtype)
    except (TypeError, ValueError) as e:
        raise DataPipelineError(f"dtype NumPy không hợp lệ: '{dtype}'") from e

    if not np.issubdtype(resolved, np.integer):
        raise DataPipelineError(
            f"dtype lưu token phải là integer dtype, nhận được '{dtype}'"
        )
    return resolved


__all__ = ["resolve_numpy_dtype"]
