"""Public inference gateway exposed to outer adapters."""

from __future__ import annotations

from typing import Optional

from .contracts import (
    GenerationCommand,
    GenerationStream,
    InferencePreparationCommand,
    InferencePreparationResult,
)
from .service import InferenceService


class InferenceGateway:
    """Expose adapter-facing inference use cases without cross-use-case internals."""

    def __init__(self, service: InferenceService) -> None:
        self._service = service

    @property
    def current_backend(self) -> str:
        return self._service.current_backend

    @property
    def configured_checkpoint_path(self) -> str:
        return self._service.configured_checkpoint_path

    def set_vocab_path(self, vocab_path: str) -> None:
        self._service.set_vocab_path(vocab_path)

    def prepare(self, command: InferencePreparationCommand) -> InferencePreparationResult:
        return self._service.prepare(command)

    def get_runtime_state(self) -> dict[str, object]:
        return self._service.get_runtime_state()

    def list_generators(self) -> list[str]:
        return self._service.list_generators()

    def set_backend(self, backend: str) -> None:
        self._service.set_backend(backend)

    def begin_generation_command(self, command: GenerationCommand) -> GenerationStream:
        return self._service.begin_generation_command(command)

    def list_checkpoints(self) -> list[dict[str, object]]:
        return self._service.list_checkpoints()

    def load_checkpoint(
        self,
        checkpoint_path: str,
        backend: Optional[str] = None,
        *,
        require_managed: bool = False,
    ) -> None:
        self._service.load_checkpoint(
            checkpoint_path,
            backend=backend,
            require_managed=require_managed,
        )

    def delete_checkpoint(self, filename: str) -> bool:
        return self._service.delete_checkpoint(filename)

    def resolve_checkpoint_path(self, path: str, *, filename_only: bool = False) -> str:
        return self._service.resolve_checkpoint_path(path, filename_only=filename_only)

    def list_models(self) -> list[str]:
        return self._service.list_models()


__all__ = ["InferenceGateway"]
