"""Configuration application contracts.

Application owns canonical configuration policy. Adapters only decode/encode and
perform source I/O through this port; they never construct ``EngineConfig``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Protocol, Sequence

DEFAULT_CONFIG_PATH = "configs/truyen_kieu.yaml"


@dataclass(frozen=True)
class ConfigRequest:
    """One request to resolve canonical application configuration."""

    source: Optional[str] = None
    overrides: tuple[str, ...] = ()

    @classmethod
    def from_values(
        cls,
        source: Optional[str] = None,
        overrides: Optional[Sequence[str]] = None,
    ) -> "ConfigRequest":
        return cls(source=source, overrides=tuple(overrides or ()))


@dataclass(frozen=True)
class LoggingSettings:
    level: str
    file: str


class ConfigDocumentError(ValueError):
    """Raised when an adapter cannot decode a configuration document."""


class ConfigDocumentProvider(Protocol):
    """Port for config document conversion and I/O only."""

    @property
    def default_path(self) -> str: ...

    def load_mapping(self, source: Optional[str] = None) -> Mapping[str, object]: ...

    def parse_mapping(self, content: str) -> Mapping[str, object]: ...

    def read_raw(self, source: Optional[str] = None) -> tuple[str, str]: ...

    def write_raw(self, content: str, source: Optional[str] = None) -> str: ...

    def is_default_path(self, path: str) -> bool: ...


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "ConfigDocumentError",
    "ConfigDocumentProvider",
    "ConfigRequest",
    "LoggingSettings",
]
