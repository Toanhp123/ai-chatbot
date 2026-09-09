"""Application-facing configuration authority."""

from __future__ import annotations

import os
from typing import Optional, Sequence

from src.core.config import EngineConfig

from .contracts import ConfigProvider, ConfigRequest


class ConfigurationService:
    """Resolve and snapshot configuration through one provider contract."""

    def __init__(self, provider: ConfigProvider) -> None:
        self._provider = provider
        self._active: Optional[EngineConfig] = None

    @property
    def default_path(self) -> str:
        return self._provider.default_path

    def resolve(self, request: Optional[ConfigRequest] = None) -> EngineConfig:
        resolved = self._provider.load(request or ConfigRequest())
        return self.snapshot(resolved)

    def resolve_values(
        self,
        source: Optional[str] = None,
        overrides: Optional[Sequence[str]] = None,
    ) -> EngineConfig:
        return self.resolve(ConfigRequest.from_values(source, overrides))

    @staticmethod
    def snapshot(config: EngineConfig) -> EngineConfig:
        """Detach callers from later mutations while preserving validated semantics."""
        return EngineConfig.from_dict(config.to_dict())

    def activate(self, config: EngineConfig) -> EngineConfig:
        self._active = self.snapshot(config)
        return self.snapshot(self._active)

    def current(self) -> EngineConfig:
        if self._active is None:
            return self.resolve()
        return self.snapshot(self._active)

    def canonical_override_paths(
        self,
        domains: tuple[str, ...] = ("system", "data", "model", "training", "generation"),
    ) -> set[str]:
        raw = self.current().to_dict()
        result: set[str] = set()
        for domain in domains:
            values = raw.get(domain, {})
            if isinstance(values, dict):
                result.update(f"{domain}.{key}" for key in values)
        return result

    def read_raw(self, source: Optional[str] = None) -> tuple[str, str]:
        return self._provider.read_raw(source)

    def save_raw(self, content: str, source: Optional[str] = None) -> tuple[str, EngineConfig]:
        path, config = self._provider.save_raw(content, source)
        if os.path.realpath(os.path.abspath(path)) == os.path.realpath(
            os.path.abspath(self.default_path)
        ):
            self._active = self.snapshot(config)
        return path, self.snapshot(config)
