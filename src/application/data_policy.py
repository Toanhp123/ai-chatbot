"""Application-owned data preparation policy.

Application selects explicit fallback/use-case policy while concrete cleaner,
tokenizer and dataset mechanics stay behind ``src.data.api``.
"""

from __future__ import annotations

from typing import Any, Optional

from src.core.config import DataConfig
from src.core.exceptions import DataPipelineError
from src.core.logging import get_logger
from src.data.api import (
    create_cleaner,
    create_standard_cleaner,
    create_tokenizer,
    prepare_dataset,
)

logger = get_logger("ApplicationDataPolicy")


class FallbackCleaner:
    """Apply an explicit Application-selected fallback for recoverable cleaner failures."""

    def __init__(self, primary: Any, fallback: Any) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = f"{getattr(primary, 'name', type(primary).__name__)}WithApplicationFallback"

    def process(self, text: str) -> str:
        try:
            return self.primary(text)
        except DataPipelineError as exc:
            logger.warning(
                "Cleaner '%s' unavailable (%s); Application selected '%s' fallback.",
                getattr(self.primary, "name", type(self.primary).__name__),
                exc.message,
                getattr(self.fallback, "name", type(self.fallback).__name__),
            )
            return self.fallback(text)

    def __call__(self, text: str) -> str:
        return self.process(text)


def build_application_cleaner(cleaner_type: str, **kwargs: Any) -> Any:
    """Resolve the configured cleaner and apply the app's explicit fallback policy."""
    primary = create_cleaner(cleaner_type, **kwargs)
    if cleaner_type.strip().lower() != "gemini":
        return primary
    fallback = create_standard_cleaner(
        clean_line_numbers=bool(kwargs.get("clean_line_numbers", True))
    )
    return FallbackCleaner(primary=primary, fallback=fallback)


def build_application_tokenizer(config: DataConfig, text: str) -> Any:
    """Select a tokenizer from canonical config; the data capability constructs it."""
    tokenizer_kwargs = dict(config.tokenizer_kwargs)
    tokenizer_kwargs.setdefault("text", text)
    return create_tokenizer(config.tokenizer_type, **tokenizer_kwargs)


def prepare_application_dataset(
    config: DataConfig,
    *,
    block_size: Optional[int] = None,
    fallback_text: Optional[str] = None,
    persist_fallback: bool = False,
):
    """Apply use-case policy and delegate dataset mechanics through the data facade."""
    cleaner_kwargs = dict(config.cleaner_kwargs)
    cleaner_kwargs.setdefault("clean_line_numbers", config.clean_line_numbers)
    cleaner = build_application_cleaner(config.cleaner_type, **cleaner_kwargs)
    return prepare_dataset(
        config,
        cleaner=cleaner,
        tokenizer_factory=lambda text: build_application_tokenizer(config, text),
        block_size=block_size,
        fallback_text=fallback_text,
        persist_fallback=persist_fallback,
    )


__all__ = [
    "FallbackCleaner",
    "build_application_cleaner",
    "build_application_tokenizer",
    "prepare_application_dataset",
]
