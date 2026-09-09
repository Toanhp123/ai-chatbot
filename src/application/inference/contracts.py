"""Transport-neutral inference request contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


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
