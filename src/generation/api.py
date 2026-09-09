"""Stable public API for the generation capability.

Cross-capability and application code should depend on this module rather than
registry/generator implementation modules.
"""

from __future__ import annotations

from typing import Any

from src.generation.base import BaseGenerator, GenerationCancellation, GenerationOutput
from src.generation.registry import GeneratorRegistry, get_generator
from src.generation.streamers import TextIteratorStreamer


def create_generator(backend: str, **kwargs: Any) -> BaseGenerator:
    """Create a generator through the capability-owned registry."""
    return get_generator(backend, **kwargs)


def create_generator_for_inference(
    backend: str,
    *,
    model: Any,
    tokenizer: Any,
    device: str,
) -> BaseGenerator:
    """Create a generator from the stable inference-context contract."""
    return GeneratorRegistry.create_for_inference(
        backend,
        model=model,
        tokenizer=tokenizer,
        device=device,
    )


def validate_generator_backend(backend: str) -> str:
    """Validate and canonicalize a registered generation backend name."""
    cleaned = backend.lower().strip()
    GeneratorRegistry.get(cleaned)
    return cleaned


def list_generators() -> list[str]:
    """Return registered generation backends."""
    return GeneratorRegistry.list_generators()


__all__ = [
    "BaseGenerator",
    "GenerationCancellation",
    "GenerationOutput",
    "TextIteratorStreamer",
    "create_generator",
    "create_generator_for_inference",
    "list_generators",
    "validate_generator_backend",
]
