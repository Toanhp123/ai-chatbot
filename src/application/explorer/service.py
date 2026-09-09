"""Explorer application use cases for cleaning, tokenization and dataset inspection."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from src.application.config import ConfigRequest, ConfigurationService
from src.data.cleaners import get_cleaner
from src.data.cleaners.standard import DeduplicationFilter, LineLengthFilter, RepetitionFilter
from src.data.pipeline import DataPipeline
from src.data.tokenizers import ByteTokenizer, load_tokenizer
from src.data.tokenizers.gemini import GeminiTokenizer


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
        cleaner = get_cleaner(cleaner_type, clean_line_numbers=clean_line_numbers)
        cleaned = cleaner.process(text)
        if repetition:
            cleaned = RepetitionFilter().process(cleaned)
        if min_length is not None or max_length is not None:
            cleaned = LineLengthFilter(
                min_len=min_length if min_length is not None else 1,
                max_len=max_length if max_length is not None else 4096,
            ).process(cleaned)
        if dedup:
            mode = dedup_mode if dedup_mode in ("consecutive", "global") else "consecutive"
            cleaned = DeduplicationFilter(mode=mode).process(cleaned)
        return {
            "raw": text,
            "cleaned": cleaned,
            "raw_length": len(text),
            "cleaned_length": len(cleaned),
            "diff_chars": len(text) - len(cleaned),
        }

    def tokenize(self, *, text: str, tokenizer_type: str, source: Optional[str] = None):
        requested_type = tokenizer_type.strip().lower()
        if requested_type == "byte":
            tokenizer = ByteTokenizer()
        elif requested_type == "gemini":
            tokenizer = GeminiTokenizer()
        elif requested_type == "char":
            config = self._config(source)
            if not os.path.isfile(config.data.vocab_file):
                raise FileNotFoundError(f"Không tìm thấy file từ điển {config.data.vocab_file}")
            tokenizer = load_tokenizer(config.data.vocab_file)
        else:
            raise ValueError(f"Tokenizer không được hỗ trợ: {requested_type}")

        token_ids = tokenizer.encode(text)
        byte_semantics = tokenizer.identity_payload().get("tokenizer_type") == "byte"
        tokens_detail = []
        for token_id in token_ids:
            try:
                if byte_semantics and 0 <= token_id < 256:
                    if token_id == 32:
                        display = "␣"
                    elif token_id == 10:
                        display = "⏎\n"
                    elif 33 <= token_id <= 126:
                        display = chr(token_id)
                    else:
                        display = f"0x{token_id:02X}"
                else:
                    char = tokenizer.decode([token_id])
                    display = "␣" if char == " " else ("⏎\n" if char == "\n" else char)
            except Exception:
                display = f"<{token_id}>"
            tokens_detail.append({"id": token_id, "raw": display})

        return {
            "text": text,
            "tokenizer_type": (
                "gemini"
                if requested_type == "gemini"
                else str(tokenizer.identity_payload().get("tokenizer_type", requested_type))
            ),
            "token_ids": token_ids,
            "tokens": tokens_detail,
            "char_count": len(text),
            "token_count": len(token_ids),
            "vocab_size": getattr(tokenizer, "vocab_size", 0),
        }

    def dataset_sample(self, source: Optional[str] = None) -> Dict[str, Any]:
        config = self._config(source)
        input_file = config.data.input_file
        vocab_file = config.data.vocab_file
        sample_lines = []
        total_chars = 0
        total_lines = 0
        if os.path.isfile(input_file):
            with open(input_file, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            total_lines = len(lines)
            total_chars = sum(len(line) for line in lines)
            sample_lines = [line.strip() for line in lines[:25] if line.strip()]

        vocab_size = 0
        vocab_chars = []
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

    def export_binary(self, source: Optional[str] = None) -> Dict[str, Any]:
        config = self._config(source)
        train_data, val_data, _ = DataPipeline.setup_data(config.data)
        data_dir = os.path.dirname(os.path.abspath(config.data.input_file))
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

    def compare_tokenizers(self, *, text: str, source: Optional[str] = None) -> Dict[str, Any]:
        config = self._config(source)
        configured = (
            load_tokenizer(config.data.vocab_file)
            if os.path.isfile(config.data.vocab_file)
            else None
        )
        byte_tokenizer = ByteTokenizer()
        candidates = []
        if configured is not None:
            configured_type = str(configured.identity_payload().get("tokenizer_type", "configured"))
            if configured_type != "byte":
                candidates.append(
                    (configured_type, f"{configured_type.title()} Tokenizer", configured)
                )
        candidates.append(("byte", "Byte Tokenizer (Zero-OOV)", byte_tokenizer))
        results: Dict[str, Any] = {}
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
