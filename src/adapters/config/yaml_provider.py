"""YAML implementation of the application ConfigProvider port."""

from __future__ import annotations

import os
import tempfile
from typing import Optional

import yaml

from src.application.config.contracts import DEFAULT_CONFIG_PATH, ConfigRequest
from src.core.config import EngineConfig
from src.core.exceptions import ConfigurationError


class YamlConfigProvider:
    def __init__(self, default_path: str = DEFAULT_CONFIG_PATH) -> None:
        self._default_path = default_path

    @property
    def default_path(self) -> str:
        return self._default_path

    def _path(self, source: Optional[str]) -> str:
        return source or self._default_path

    def load(self, request: ConfigRequest) -> EngineConfig:
        path = self._path(request.source)
        if request.source is None and not os.path.isfile(path):
            config = EngineConfig()
            if request.overrides:
                from src.core.config.engine import apply_overrides

                config = EngineConfig.from_dict(
                    apply_overrides(config.to_dict(), request.overrides)
                )
            return config
        return EngineConfig.from_yaml(path, overrides=request.overrides or None)

    def read_raw(self, source: Optional[str] = None) -> tuple[str, str]:
        path = self._path(source)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình: {path}")
        with open(path, "r", encoding="utf-8") as handle:
            return path, handle.read()

    def save_raw(self, content: str, source: Optional[str] = None) -> tuple[str, EngineConfig]:
        path = self._path(source)
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"Lỗi phân tích cú pháp YAML: {exc}") from exc
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict):
            raise ConfigurationError("Nội dung YAML phải là một dictionary/mapping ở cấp cao nhất.")
        validated = EngineConfig.from_dict(parsed)

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
        return path, validated
