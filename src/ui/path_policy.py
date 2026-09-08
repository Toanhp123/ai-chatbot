"""Shared filesystem boundary helpers for UI-managed paths."""

import os


def resolve_path_within_root(
    path: str,
    root: str,
    *,
    bare_name_in_root: bool = False,
    allow_root: bool = False,
) -> str:
    """Resolve ``path`` and reject traversal or symlink escape outside ``root``."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Đường dẫn không được để trống.")

    root_real = os.path.realpath(os.path.abspath(root))
    raw_path = path.strip()
    if bare_name_in_root and os.path.dirname(raw_path) in {"", "."}:
        candidate = os.path.realpath(os.path.join(root_real, os.path.basename(raw_path)))
    else:
        candidate = os.path.realpath(os.path.abspath(os.path.normpath(raw_path)))

    try:
        inside_root = os.path.commonpath([root_real, candidate]) == root_real
    except ValueError:
        inside_root = False

    if not inside_root or (not allow_root and candidate == root_real):
        raise ValueError(f"Đường dẫn phải nằm bên trong thư mục được quản lý: {root_real}")
    return candidate


__all__ = ["resolve_path_within_root"]
