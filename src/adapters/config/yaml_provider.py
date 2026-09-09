"""YAML config-document adapter: decode/encode and atomic file I/O only."""

from __future__ import annotations

import os
import tempfile
from typing import Mapping, Optional

import yaml

from src.application.config.contracts import (
    DEFAULT_CONFIG_PATH,
    ConfigDocumentError,
)


class YamlConfigProvider:
    def __init__(self, default_path: str = DEFAULT_CONFIG_PATH) -> None:
        self._default_path = default_path

    @property
    def default_path(self) -> str:
        return self._default_path

    def _path(self, source: Optional[str]) -> str:
        return source or self._default_path

    def is_default_path(self, path: str) -> bool:
        return os.path.realpath(os.path.abspath(path)) == os.path.realpath(
            os.path.abspath(self._default_path)
        )

    @staticmethod
    def _decode(content: str) -> Mapping[str, object]:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ConfigDocumentError(f"Lỗi phân tích cú pháp YAML: {exc}") from exc
        if parsed is None:
            return {}
        if not isinstance(parsed, dict):
            raise ConfigDocumentError(
                "Nội dung YAML phải là một dictionary/mapping ở cấp cao nhất."
            )
        return parsed

    def load_mapping(self, source: Optional[str] = None) -> Mapping[str, object]:
        path = self._path(source)
        if source is None and not os.path.isfile(path):
            return {}
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình: {path}")
        with open(path, "r", encoding="utf-8") as handle:
            return self._decode(handle.read())

    def parse_mapping(self, content: str) -> Mapping[str, object]:
        return self._decode(content)

    def read_raw(self, source: Optional[str] = None) -> tuple[str, str]:
        path = self._path(source)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình: {path}")
        with open(path, "r", encoding="utf-8") as handle:
            return path, handle.read()

    def write_raw(self, content: str, source: Optional[str] = None) -> str:
        path = self._path(source)
        target_dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(target_dir, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=".config-", suffix=".yaml", dir=target_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except Exception:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
            raise
        return path
