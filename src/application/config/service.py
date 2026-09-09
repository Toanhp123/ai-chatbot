"""Application-facing configuration authority."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from src.core.config import EngineConfig, apply_overrides
from src.core.exceptions import ConfigurationError

from .contracts import ConfigDocumentError, ConfigDocumentProvider, ConfigRequest


class ConfigurationService:
    """Own defaults, overrides, canonical validation, snapshots and activation."""

    def __init__(self, provider: ConfigDocumentProvider) -> None:
        self._provider = provider
        self._active: Optional[EngineConfig] = None

    @property
    def default_path(self) -> str:
        return self._provider.default_path

    @staticmethod
    def _canonical_from_mapping(
        mapping: Mapping[str, object],
        *,
        overrides: Sequence[str] = (),
    ) -> EngineConfig:
        raw = dict(mapping)
        if overrides:
            raw = apply_overrides(raw, overrides)
        return EngineConfig.from_dict(raw)

    def resolve(self, request: Optional[ConfigRequest] = None) -> EngineConfig:
        effective = request or ConfigRequest()
        try:
            mapping = self._provider.load_mapping(effective.source)
        except FileNotFoundError as exc:
            raise ConfigurationError(str(exc)) from exc
        except ConfigDocumentError as exc:
            raise ConfigurationError(str(exc)) from exc
        return self.snapshot(self._canonical_from_mapping(mapping, overrides=effective.overrides))

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
        try:
            mapping = self._provider.parse_mapping(content)
        except ConfigDocumentError as exc:
            raise ConfigurationError(str(exc)) from exc
        config = self._canonical_from_mapping(mapping)
        path = self._provider.write_raw(content, source)
        if self._provider.is_default_path(path):
            self._active = self.snapshot(config)
        return path, self.snapshot(config)
