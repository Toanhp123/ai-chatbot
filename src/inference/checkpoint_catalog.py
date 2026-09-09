"""Managed checkpoint catalog and filesystem policy for inference application flows."""

from __future__ import annotations

import math
import os
import stat
import time
from typing import Any, Dict, List, Optional

import torch


def identity_from_stat(stat_result: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(stat_result.st_dev),
        int(stat_result.st_ino),
        int(stat_result.st_size),
        int(stat_result.st_mtime_ns),
    )


def checkpoint_identity(path: str) -> tuple[int, int, int, int]:
    return identity_from_stat(os.stat(path))


def resolve_checkpoint_path(
    checkpoint_dir: str,
    path: str,
    *,
    filename_only: bool = False,
) -> str:
    root = os.path.realpath(os.path.abspath(checkpoint_dir))
    if filename_only:
        candidate = os.path.realpath(os.path.join(root, os.path.basename(path)))
    else:
        candidate = os.path.realpath(os.path.abspath(path))
        if os.path.dirname(path) in {"", "."}:
            candidate = os.path.realpath(os.path.join(root, os.path.basename(path)))
    try:
        if os.path.commonpath([root, candidate]) != root or candidate == root:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Checkpoint phải nằm bên trong checkpoint_dir đã cấu hình.") from exc
    return candidate


def list_checkpoints(
    *,
    checkpoint_dir: str,
    checkpoint_name: str,
    active_path: Optional[str],
    active_identity: Optional[tuple[int, int, int, int]],
) -> List[Dict[str, Any]]:
    """Read stable checkpoint metadata from one directory/config snapshot."""
    checkpoints: List[Dict[str, Any]] = []
    if not os.path.exists(checkpoint_dir):
        return checkpoints

    try:
        filenames = os.listdir(checkpoint_dir)
    except OSError:
        return checkpoints

    for fname in filenames:
        if not (fname.endswith(".pt") or fname.endswith(".pth")):
            continue
        try:
            fpath = resolve_checkpoint_path(checkpoint_dir, fname, filename_only=True)
            with open(fpath, "rb") as checkpoint_file:
                file_stat = os.fstat(checkpoint_file.fileno())
                if not stat.S_ISREG(file_stat.st_mode):
                    continue
                current_identity = identity_from_stat(file_stat)
                size_mb = round(file_stat.st_size / (1024 * 1024), 2)
                modified_time = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(file_stat.st_mtime)
                )
                step = None
                val_loss = None
                run_name = None
                try:
                    meta = torch.load(checkpoint_file, map_location="cpu", weights_only=True)
                    if isinstance(meta, dict):
                        step = meta.get("step")
                        raw_val = meta.get("val_loss")
                        if raw_val is not None:
                            try:
                                value = float(raw_val)
                                if math.isfinite(value):
                                    val_loss = round(value, 4)
                            except (ValueError, TypeError):
                                pass
                        run_name = meta.get("run_name")
                except Exception:
                    # Catalog listing is best effort; unreadable payloads remain visible.
                    pass
        except (OSError, ValueError):
            continue

        is_active = (
            active_path is not None
            and os.path.abspath(fpath) == os.path.abspath(active_path)
            and active_identity == current_identity
        )
        checkpoints.append(
            {
                "filename": fname,
                "path": fpath.replace("\\", "/"),
                "size_mb": size_mb,
                "modified_time": modified_time,
                "is_active": is_active,
                "step": step,
                "val_loss": val_loss,
                "run_name": run_name,
                "is_configured_best": fname == checkpoint_name,
            }
        )

    valid_losses = [c["val_loss"] for c in checkpoints if c.get("val_loss") is not None]
    min_loss = min(valid_losses) if valid_losses else None
    for checkpoint in checkpoints:
        checkpoint["is_best_val"] = (
            min_loss is not None
            and checkpoint.get("val_loss") is not None
            and abs(checkpoint["val_loss"] - min_loss) < 1e-5
        )
        fname = checkpoint["filename"]
        if fname == checkpoint_name:
            checkpoint["tag"] = "best"
        elif fname == "last_model.pt":
            checkpoint["tag"] = "canonical_last"
        elif fname.endswith("_last.pt"):
            checkpoint["tag"] = "run_last"
        elif "_step" in fname:
            checkpoint["tag"] = "top_k"
        else:
            checkpoint["tag"] = "custom"

    def sort_key(item: Dict[str, Any]):
        configured_rank = 0 if item["filename"] == checkpoint_name else 1
        mtime = 0.0
        try:
            mtime = time.mktime(time.strptime(item["modified_time"], "%Y-%m-%d %H:%M:%S"))
        except Exception:
            pass
        step = item.get("step") or 0
        return (configured_rank, -mtime, -step)

    checkpoints.sort(key=sort_key)
    return checkpoints


def delete_checkpoint(
    *,
    checkpoint_dir: str,
    checkpoint_name: str,
    filename: str,
    active_path: Optional[str],
) -> str:
    safe_filename = os.path.basename(filename)
    target_path = resolve_checkpoint_path(checkpoint_dir, safe_filename, filename_only=True)
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Không tìm thấy file checkpoint: {safe_filename}")
    if safe_filename == checkpoint_name:
        raise ValueError("Không thể xóa checkpoint tốt nhất đang được cấu hình!")
    if active_path and os.path.abspath(target_path) == os.path.abspath(active_path):
        raise ValueError("Không thể xóa checkpoint đang được nạp phục vụ suy luận!")
    os.remove(target_path)
    return safe_filename


__all__ = [
    "identity_from_stat",
    "checkpoint_identity",
    "resolve_checkpoint_path",
    "list_checkpoints",
    "delete_checkpoint",
]
