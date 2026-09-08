"""Typed probe outcomes used by diagnostics collectors."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


class ProbeStatus(str, Enum):
    OK = "OK"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ProbeResult(Generic[T]):
    status: ProbeStatus
    value: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, value: T) -> "ProbeResult[T]":
        return cls(status=ProbeStatus.OK, value=value)

    @classmethod
    def unsupported(cls, reason: str, value: Optional[T] = None) -> "ProbeResult[T]":
        return cls(status=ProbeStatus.UNSUPPORTED, value=value, error=reason)

    @classmethod
    def failed(cls, error: Exception | str) -> "ProbeResult[T]":
        return cls(status=ProbeStatus.FAILED, error=str(error))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


__all__ = ["ProbeStatus", "ProbeResult"]
