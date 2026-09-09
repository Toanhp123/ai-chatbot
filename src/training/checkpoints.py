"""Training checkpoint filesystem mechanics."""

from __future__ import annotations

import os
import stat


def capture_checkpoint_identity(path: str) -> tuple[int, int, int, int]:
    """Pin the exact regular-file revision used for a later resume operation."""
    with open(path, "rb") as checkpoint_file:
        file_stat = os.fstat(checkpoint_file.fileno())
        if not stat.S_ISREG(file_stat.st_mode):
            raise OSError(f"Checkpoint resume không phải file thường: {path}")
        return (
            int(file_stat.st_dev),
            int(file_stat.st_ino),
            int(file_stat.st_size),
            int(file_stat.st_mtime_ns),
        )


__all__ = ["capture_checkpoint_identity"]
