"""Application-owned data preparation policy.

Capability modules report failures and execute mechanics; Application selects
cleaner/tokenizer implementations and explicit fallback behavior.
"""

from __future__ import annotations

from typing import Any, Optional

from src.core.config import DataConfig
from src.core.exceptions import DataPipelineError
from src.core.logging import get_logger
from src.data.cleaners import BaseTextPreprocessor, GeminiTextCleaner, TextCleaner, get_cleaner
from src.data.pipeline import DataPipeline
from src.data.tokenizers import BaseTokenizer, get_tokenizer

logger = get_logger("ApplicationDataPolicy")


class FallbackCleaner(BaseTextPreprocessor):
    """Apply an explicit Application-selected fallback for recoverable cleaner failures."""

    def __init__(
        self,
        primary: BaseTextPreprocessor,
        fallback: BaseTextPreprocessor,
    ) -> None:
        super().__init__(name=f"{primary.name}WithApplicationFallback")
        self.primary = primary
        self.fallback = fallback

    def process(self, text: str) -> str:
        try:
            return self.primary(text)
        except DataPipelineError as exc:
            logger.warning(
                "Cleaner '%s' unavailable (%s); Application selected '%s' fallback.",
                self.primary.name,
                exc.message,
                self.fallback.name,
            )
            return self.fallback(text)


def build_application_cleaner(cleaner_type: str, **kwargs: Any) -> BaseTextPreprocessor:
    """Resolve the configured cleaner and apply the app's explicit fallback policy."""

    primary = get_cleaner(cleaner_type=cleaner_type, **kwargs)
    if not isinstance(primary, GeminiTextCleaner):
        return primary

    fallback = TextCleaner(
        clean_line_numbers=bool(kwargs.get("clean_line_numbers", True)),
        normalize_ws=True,
        normalize_uni=True,
        normalize_punct=True,
    )
    return FallbackCleaner(primary=primary, fallback=fallback)


def build_application_tokenizer(config: DataConfig, text: str) -> BaseTokenizer:
    """Select the tokenizer from canonical config; DataPipeline only executes it."""

    tokenizer_kwargs = dict(config.tokenizer_kwargs)
    tokenizer_kwargs.setdefault("text", text)
    return get_tokenizer(config.tokenizer_type, **tokenizer_kwargs)


def prepare_application_dataset(
    config: DataConfig,
    *,
    block_size: Optional[int] = None,
    fallback_text: Optional[str] = None,
    persist_fallback: bool = False,
):
    """Apply application policy, then delegate dataset mechanics to DataPipeline."""

    cleaner_kwargs = dict(config.cleaner_kwargs)
    cleaner_kwargs.setdefault("clean_line_numbers", config.clean_line_numbers)
    cleaner = build_application_cleaner(config.cleaner_type, **cleaner_kwargs)
    return DataPipeline.setup_data(
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
