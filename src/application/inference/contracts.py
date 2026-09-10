"""Application-owned contracts for inference use cases.

The Application layer talks to inference mechanics only through these structural
ports. Concrete model/tokenizer/generator/session implementations stay inside the
inference capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator, Mapping, Optional, Protocol, Sequence

from src.application.config.contracts import ConfigRequest
from src.core.config import GenerationConfig


@dataclass(frozen=True)
class GenerationOverrides:
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    min_p: Optional[float] = None
    repetition_penalty: Optional[float] = None
    max_new_tokens: Optional[int] = None
    greedy: Optional[bool] = None
    use_cache: Optional[bool] = None


@dataclass(frozen=True)
class GenerationCommand:
    prompt: str
    overrides: GenerationOverrides = GenerationOverrides()
    backend: Optional[str] = None
    stop_words: Optional[tuple[str, ...]] = None

    @classmethod
    def create(
        cls,
        *,
        prompt: str,
        overrides: Optional[GenerationOverrides] = None,
        backend: Optional[str] = None,
        stop_words: Optional[Sequence[str]] = None,
    ) -> "GenerationCommand":
        return cls(
            prompt=prompt,
            overrides=overrides or GenerationOverrides(),
            backend=backend,
            stop_words=tuple(stop_words) if stop_words is not None else None,
        )


class GenerationStream(Protocol):
    def iter_events(self) -> Iterator[dict[str, object]]: ...
    def close(self) -> None: ...


class RuntimeHandoff(Protocol):
    @property
    def previous_device(self) -> str: ...

    def rollback(self) -> None: ...


class InferenceRuntimePort(Protocol):
    @property
    def current_checkpoint_path(self) -> Optional[str]: ...

    @property
    def current_checkpoint_identity(self) -> Optional[tuple[int, int, int, int]]: ...

    @property
    def device(self) -> str: ...

    @property
    def backend(self) -> str: ...

    @property
    def ready(self) -> bool: ...

    def path_exists(self, path: str) -> bool: ...
    def join_path(self, *parts: str) -> str: ...
    def load_tokenizer_if_present(self, vocab_path: str) -> bool: ...
    def resolve_checkpoint_path_for_dir(
        self,
        checkpoint_dir: str,
        path: str,
        *,
        filename_only: bool = False,
    ) -> str: ...
    def list_checkpoints(
        self,
        *,
        checkpoint_dir: str,
        checkpoint_name: str,
    ) -> list[dict[str, object]]: ...
    def delete_checkpoint(
        self,
        *,
        checkpoint_dir: str,
        checkpoint_name: str,
        filename: str,
    ) -> str: ...
    def list_generators(self) -> list[str]: ...
    def list_models(self) -> list[str]: ...
    def validate_backend(self, backend: str) -> str: ...
    def resolve_device_name(self, device: str) -> str: ...
    def set_backend(self, backend: str) -> str: ...
    def load_checkpoint(
        self,
        checkpoint_path: str,
        *,
        vocab_path: str,
        configured_device: str,
        backend: str,
    ) -> tuple[int, int, int, int]: ...
    def prepare_training_handoff(self) -> Optional[RuntimeHandoff]: ...
    def begin_generation(
        self,
        *,
        prompt: str,
        config: GenerationConfig,
        requested_backend: str,
        stop_words: Optional[Sequence[str]],
        release_admission: Callable[[], None],
    ) -> GenerationStream: ...


class GenerationAdmissionPort(Protocol):
    @property
    def active_sessions(self) -> int: ...
    def ensure_idle(self, *, operation: str) -> None: ...
    def acquire(
        self,
        *,
        prompt: str,
        config: GenerationConfig,
        device: str,
    ) -> Callable[[], None]: ...


@dataclass(frozen=True)
class InferenceTrainingHandoff:
    """Application transaction token for a reversible cross-use-case handoff."""

    training_admission_reserved: bool = False
    rollback_action: Optional[Callable[[], None]] = None

    def rollback(self) -> None:
        if self.rollback_action is not None:
            self.rollback_action()


InferenceState = Mapping[str, object]

@dataclass(frozen=True)
class InferencePreparationCommand:
    """Adapter-safe command for explicit inference preparation."""

    config_request: ConfigRequest = field(default_factory=ConfigRequest)
    checkpoint_path: Optional[str] = None
    vocab_path: Optional[str] = None
    backend: Optional[str] = None
    requested_device: Optional[str] = None
    require_managed_checkpoint: bool = False
    strict: bool = True


@dataclass(frozen=True)
class InferencePreparationResult:
    """Result of an explicit inference preparation transaction."""

    ready: bool
    checkpoint_path: Optional[str]
    backend: str
    configured_device: str
    active_device: str
    warning: Optional[str] = None


__all__ = [
    "GenerationAdmissionPort",
    "GenerationCommand",
    "GenerationOverrides",
    "GenerationStream",
    "InferencePreparationCommand",
    "InferencePreparationResult",
    "InferenceRuntimePort",
    "InferenceState",
    "InferenceTrainingHandoff",
    "RuntimeHandoff",
]
