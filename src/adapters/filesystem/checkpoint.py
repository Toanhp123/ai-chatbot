"""Filesystem implementation of the Application resume-checkpoint port."""

from __future__ import annotations

import os
import stat


class FilesystemResumeCheckpointAdapter:
    """Resolve managed checkpoint paths and pin the exact regular-file revision."""

    def resolve(self, path: str, checkpoint_dir: str) -> str:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Đường dẫn checkpoint không được để trống.")

        root_real = os.path.realpath(os.path.abspath(checkpoint_dir))
        raw_path = path.strip()
        if os.path.dirname(raw_path) in {"", "."}:
            candidate = os.path.realpath(os.path.join(root_real, os.path.basename(raw_path)))
        else:
            candidate = os.path.realpath(os.path.abspath(os.path.normpath(raw_path)))

        try:
            inside_root = os.path.commonpath([root_real, candidate]) == root_real
        except ValueError:
            inside_root = False
        if not inside_root or candidate == root_real:
            raise ValueError(f"Checkpoint resume phải nằm bên trong checkpoint_dir: {root_real}")
        return candidate

    def capture_identity(self, path: str) -> tuple[int, int, int, int]:
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


__all__ = ["FilesystemResumeCheckpointAdapter"]
