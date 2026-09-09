"""Configuration application contracts.

Only this layer owns the canonical default source. Inner modules receive resolved
EngineConfig snapshots and never know whether the source was YAML, HTTP or tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from src.core.config import EngineConfig

DEFAULT_CONFIG_PATH = "configs/truyen_kieu.yaml"


@dataclass(frozen=True)
class ConfigRequest:
    """One request to resolve a canonical EngineConfig."""

    source: Optional[str] = None
    overrides: tuple[str, ...] = ()

    @classmethod
    def from_values(
        cls,
        source: Optional[str] = None,
        overrides: Optional[Sequence[str]] = None,
    ) -> "ConfigRequest":
        return cls(source=source, overrides=tuple(overrides or ()))


class ConfigProvider(Protocol):
    """Port for obtaining and persisting canonical configuration."""

    @property
    def default_path(self) -> str: ...

    def load(self, request: ConfigRequest) -> EngineConfig: ...

    def read_raw(self, source: Optional[str] = None) -> tuple[str, str]: ...

    def save_raw(self, content: str, source: Optional[str] = None) -> tuple[str, EngineConfig]: ...
