"""Explorer application use cases over the stable data capability API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.application.config import ConfigRequest, ConfigurationService
from src.application.data_policy import build_application_cleaner, prepare_application_dataset
from src.data.api import (
    FALLBACK_CORPUS,
    clean_for_explorer,
    export_binary_dataset,
    tokenize_for_explorer,
)
from src.data.api import compare_tokenizers as compare_tokenizers_data
from src.data.api import dataset_sample as inspect_dataset_sample


class ExplorerApplicationService:
    def __init__(self, config_service: ConfigurationService) -> None:
        self.config_service = config_service

    def _config(self, source: Optional[str] = None):
        if source is None:
            return self.config_service.current()
        return self.config_service.resolve(ConfigRequest(source=source))

    @staticmethod
    def clean(
        *,
        text: str,
        cleaner_type: str,
        clean_line_numbers: bool,
        dedup: bool,
        dedup_mode: str,
        repetition: bool,
        min_length: Optional[int],
        max_length: Optional[int],
    ) -> Dict[str, Any]:
        cleaner = build_application_cleaner(
            cleaner_type,
            clean_line_numbers=clean_line_numbers,
        )
        mode = dedup_mode if dedup_mode in ("consecutive", "global") else "consecutive"
        return clean_for_explorer(
            text=text,
            cleaner=cleaner,
            dedup=dedup,
            dedup_mode=mode,
            repetition=repetition,
            min_length=min_length,
            max_length=max_length,
        )

    def tokenize(self, *, text: str, tokenizer_type: str, source: Optional[str] = None):
        requested_type = tokenizer_type.strip().lower()
        vocab_file = self._config(source).data.vocab_file if requested_type == "char" else None
        return tokenize_for_explorer(
            text=text,
            tokenizer_type=requested_type,
            vocab_file=vocab_file,
        )

    def dataset_sample(self, source: Optional[str] = None) -> Dict[str, Any]:
        config = self._config(source)
        return inspect_dataset_sample(
            input_file=config.data.input_file,
            vocab_file=config.data.vocab_file,
        )

    def export_binary(self, source: Optional[str] = None) -> Dict[str, Any]:
        config = self._config(source)
        train_data, val_data, _ = prepare_application_dataset(
            config.data,
            fallback_text=FALLBACK_CORPUS,
            persist_fallback=True,
        )
        return export_binary_dataset(
            train_data=train_data,
            val_data=val_data,
            input_file=config.data.input_file,
        )

    def compare_tokenizers(self, *, text: str, source: Optional[str] = None) -> Dict[str, Any]:
        config = self._config(source)
        return compare_tokenizers_data(text=text, vocab_file=config.data.vocab_file)
