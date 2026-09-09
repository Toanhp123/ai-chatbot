"""Public configuration gateway exposed to outer adapters."""

from __future__ import annotations

from typing import Optional

from .contracts import ConfigRequest, LoggingSettings
from .service import ConfigurationService


class ConfigGateway:
    """Expose transport-safe config use cases without leaking ``EngineConfig``."""

    def __init__(self, service: ConfigurationService) -> None:
        self._service = service

    @property
    def default_path(self) -> str:
        return self._service.default_path

    def canonical_override_paths(
        self,
        domains: tuple[str, ...] = ("system", "data", "model", "training", "generation"),
    ) -> set[str]:
        return self._service.canonical_override_paths(domains)

    def resolve_mapping(self, request: Optional[ConfigRequest] = None) -> dict[str, object]:
        return self._service.resolve(request).to_dict()

    def logging_settings(self) -> LoggingSettings:
        system = self._service.current().system
        return LoggingSettings(level=str(system.log_level), file=str(system.log_file))

    def read_raw(self, source: Optional[str] = None) -> tuple[str, str]:
        return self._service.read_raw(source)

    def save_raw(self, content: str, source: Optional[str] = None) -> str:
        path, _config = self._service.save_raw(content, source)
        return path


__all__ = ["ConfigGateway"]
