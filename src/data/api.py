"""Stable public API for the data capability.

Application code should depend on this module rather than concrete cleaners,
tokenizers or pipeline implementation files.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

from src.core.config import DataConfig
from src.data.cleaners import (
    DeduplicationFilter,
    LineLengthFilter,
    RepetitionFilter,
    TextCleaner,
    get_cleaner,
)
from src.data.batch_provider import (
    BaseBatchProvider,
    TensorBatchProvider,
    get_batch_provider,
)
from src.data.constants import FALLBACK_CORPUS
from src.data.pipeline import DataPipeline
from src.data.tokenizers import (
    BaseTokenizer,
    ByteTokenizer,
    GeminiTokenizer,
    get_tokenizer,
    load_tokenizer,
    load_tokenizer_state,
)
from src.data.tokenizers.base import get_tokenizer_identity


def create_cleaner(cleaner_type: str, **kwargs: Any) -> Any:
    return get_cleaner(cleaner_type=cleaner_type, **kwargs)


def create_standard_cleaner(*, clean_line_numbers: bool = True) -> Any:
    return TextCleaner(
        clean_line_numbers=clean_line_numbers,
        normalize_ws=True,
        normalize_uni=True,
        normalize_punct=True,
    )


def create_tokenizer(tokenizer_type: str, **kwargs: Any) -> Any:
    return get_tokenizer(tokenizer_type, **kwargs)


def prepare_dataset(
    config: DataConfig,
    *,
    cleaner: Callable[[str], str],
    tokenizer_factory: Callable[[str], Any],
    block_size: Optional[int] = None,
    fallback_text: Optional[str] = None,
    persist_fallback: bool = False,
):
    return DataPipeline.setup_data(
        config,
        cleaner=cleaner,
        tokenizer_factory=tokenizer_factory,
        block_size=block_size,
        fallback_text=fallback_text,
        persist_fallback=persist_fallback,
    )


def create_batch_provider(
    *,
    provider_type: str,
    train_data: Any,
    val_data: Any,
    block_size: int,
    num_workers: int = 0,
    pin_memory: bool = False,
):
    """Create a batch provider behind the stable data capability boundary."""
    return get_batch_provider(
        provider_type=provider_type,
        train_data=train_data,
        val_data=val_data,
        block_size=block_size,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )


def clean_for_explorer(
    *,
    text: str,
    cleaner: Callable[[str], str],
    dedup: bool,
    dedup_mode: str,
    repetition: bool,
    min_length: Optional[int],
    max_length: Optional[int],
) -> dict[str, Any]:
    cleaned = cleaner(text)
    if repetition:
        cleaned = RepetitionFilter().process(cleaned)
    if min_length is not None or max_length is not None:
        cleaned = LineLengthFilter(
            min_len=min_length if min_length is not None else 1,
            max_len=max_length if max_length is not None else 4096,
        ).process(cleaned)
    if dedup:
        cleaned = DeduplicationFilter(mode=dedup_mode).process(cleaned)
    return {
        "raw": text,
        "cleaned": cleaned,
        "raw_length": len(text),
        "cleaned_length": len(cleaned),
        "diff_chars": len(text) - len(cleaned),
    }


def tokenize_for_explorer(
    *,
    text: str,
    tokenizer_type: str,
    vocab_file: Optional[str] = None,
) -> dict[str, Any]:
    requested_type = tokenizer_type.strip().lower()
    if requested_type == "byte":
        tokenizer = ByteTokenizer()
    elif requested_type == "gemini":
        tokenizer = GeminiTokenizer()
    elif requested_type == "char":
        if not vocab_file or not os.path.isfile(vocab_file):
            raise FileNotFoundError(f"Không tìm thấy file từ điển {vocab_file}")
        tokenizer = load_tokenizer(vocab_file)
    else:
        raise ValueError(f"Tokenizer không được hỗ trợ: {requested_type}")

    token_ids = tokenizer.encode(text)
    identity = tokenizer.identity_payload()
    byte_semantics = identity.get("tokenizer_type") == "byte"
    tokens_detail = []
    for token_id in token_ids:
        decoded = None
        if not byte_semantics:
            try:
                decoded = tokenizer.decode([token_id])
            except Exception:
                decoded = None
        tokens_detail.append({"id": token_id, "decoded": decoded})
    return {
        "text": text,
        "tokenizer_type": (
            "gemini"
            if requested_type == "gemini"
            else str(identity.get("tokenizer_type", requested_type))
        ),
        "token_ids": token_ids,
        "tokens": tokens_detail,
        "char_count": len(text),
        "token_count": len(token_ids),
        "vocab_size": getattr(tokenizer, "vocab_size", 0),
    }


def dataset_sample(*, input_file: str, vocab_file: str) -> dict[str, Any]:
    sample_lines: list[str] = []
    total_chars = 0
    total_lines = 0
    if os.path.isfile(input_file):
        with open(input_file, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        total_lines = len(lines)
        total_chars = sum(len(line) for line in lines)
        sample_lines = [line.strip() for line in lines[:25] if line.strip()]

    vocab_size = 0
    vocab_chars: list[str] = []
    if os.path.isfile(vocab_file):
        tokenizer = load_tokenizer(vocab_file)
        vocab_size = tokenizer.vocab_size
        raw_vocab = tokenizer.identity_payload().get("vocab")
        if isinstance(raw_vocab, list):
            vocab_chars = [str(token) for token in raw_vocab[:50]]
    return {
        "input_file": str(input_file).replace("\\", "/"),
        "vocab_file": str(vocab_file).replace("\\", "/"),
        "total_lines": total_lines,
        "total_chars": total_chars,
        "sample_lines": sample_lines,
        "vocab_size": vocab_size,
        "sample_vocab": vocab_chars,
    }


def export_binary_dataset(
    *,
    train_data: Any,
    val_data: Any,
    input_file: str,
) -> dict[str, Any]:
    data_dir = os.path.dirname(os.path.abspath(input_file))
    train_bin = os.path.join(data_dir, "train.bin")
    val_bin = os.path.join(data_dir, "val.bin")
    DataPipeline.save_to_binary(train_data, train_bin)
    DataPipeline.save_to_binary(val_data, val_bin)
    return {
        "status": "success",
        "message": "Đã đóng gói dữ liệu nhị phân thành công!",
        "train_tokens": len(train_data),
        "val_tokens": len(val_data),
        "train_bin": train_bin,
        "val_bin": val_bin,
        "train_size_mb": round(os.path.getsize(train_bin) / (1024 * 1024), 2),
        "val_size_mb": round(os.path.getsize(val_bin) / (1024 * 1024), 2),
    }


def compare_tokenizers(*, text: str, vocab_file: str) -> dict[str, Any]:
    configured = load_tokenizer(vocab_file) if os.path.isfile(vocab_file) else None
    byte_tokenizer = ByteTokenizer()
    candidates: list[tuple[str, str, Any]] = []
    if configured is not None:
        configured_type = str(configured.identity_payload().get("tokenizer_type", "configured"))
        if configured_type != "byte":
            candidates.append((configured_type, f"{configured_type.title()} Tokenizer", configured))
    candidates.append(("byte", "Byte Tokenizer (Zero-OOV)", byte_tokenizer))

    results: dict[str, Any] = {}
    for key, label, tokenizer in candidates:
        token_ids = tokenizer.encode(text)
        results[key] = {
            "label": label,
            "vocab_size": getattr(tokenizer, "vocab_size", 0),
            "token_count": len(token_ids),
            "compression_ratio": round(len(text) / max(len(token_ids), 1), 2),
            "sample_token_ids": token_ids[:15],
        }
    return {"text": text, "char_count": len(text), "comparisons": results}


__all__ = [
    "BaseBatchProvider",
    "BaseTokenizer",
    "FALLBACK_CORPUS",
    "TensorBatchProvider",
    "clean_for_explorer",
    "compare_tokenizers",
    "create_batch_provider",
    "create_cleaner",
    "create_standard_cleaner",
    "create_tokenizer",
    "dataset_sample",
    "export_binary_dataset",
    "get_tokenizer_identity",
    "load_tokenizer",
    "load_tokenizer_state",
    "prepare_dataset",
    "tokenize_for_explorer",
]
