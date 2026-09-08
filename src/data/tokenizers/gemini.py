"""
Legacy ``gemini`` tokenizer compatibility adapter.

Historically this class initialized the Gemini SDK but token IDs were always produced by
``ByteTokenizer``.  That made the configuration appear to select a remote tokenizer when
runtime semantics never changed.  The adapter is now explicit: it is a deterministic,
cached byte tokenizer and performs no external API calls.  The legacy registry name is
kept so existing configs/vocab metadata remain loadable.
"""

import hashlib
import json
import os
from typing import Any, Dict, List, Optional

from src.core.exceptions import VocabularyMissingError
from src.core.logging import get_logger
from src.data.tokenizers.base import BaseTokenizer, IncrementalTextDecoder
from src.data.tokenizers.byte import ByteTokenizer
from src.data.tokenizers.registry import TokenizerRegistry

logger = get_logger("GeminiTokenizer")


@TokenizerRegistry.register("gemini", "gemini_ai")
class GeminiTokenizer(BaseTokenizer):
    """Backward-compatible cached-byte tokenizer under the historical ``gemini`` name."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash",
        cache_dir: str = ".cache/gemini_tokens",
        pad_token: str = "<pad>",
        unk_token: str = "<unk>",
        bos_token: str = "<bos>",
        eos_token: str = "<eos>",
        vocab_size_limit: int = 32000,
        **kwargs: Any,
    ) -> None:
        # api_key/model/vocab_size_limit are accepted only for legacy config compatibility.
        del api_key, vocab_size_limit, kwargs
        self.model = model
        self.cache_dir = cache_dir
        self._pad_token = pad_token
        self._unk_token = unk_token
        self._bos_token = bos_token
        self._eos_token = eos_token
        self._fallback = ByteTokenizer(
            pad_token=pad_token,
            unk_token=unk_token,
            bos_token=bos_token,
            eos_token=eos_token,
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    @property
    def vocab_size(self) -> int:
        return self._fallback.vocab_size

    @property
    def pad_token(self) -> Optional[str]:
        return self._pad_token

    @property
    def pad_token_id(self) -> Optional[int]:
        return self._fallback.pad_token_id

    @property
    def unk_token(self) -> Optional[str]:
        return self._unk_token

    @property
    def unk_token_id(self) -> Optional[int]:
        return self._fallback.unk_token_id

    @property
    def bos_token(self) -> Optional[str]:
        return self._bos_token

    @property
    def bos_token_id(self) -> Optional[int]:
        return self._fallback.bos_token_id

    @property
    def eos_token(self) -> Optional[str]:
        return self._eos_token

    @property
    def eos_token_id(self) -> Optional[int]:
        return self._fallback.eos_token_id

    def identity_payload(self) -> Dict[str, Any]:
        # Token-ID semantics are exactly ByteTokenizer semantics, so checkpoints are compatible.
        return self._fallback.identity_payload()

    def _get_cache_path(self, text: str) -> str:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.json")

    def create_incremental_decoder(self) -> IncrementalTextDecoder:
        return self._fallback.create_incremental_decoder()

    def encode(self, text: str) -> List[int]:
        if not text:
            return []

        cache_path = self._get_cache_path(text)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data: Dict[str, Any] = json.load(f)
                tokens = cached_data.get("tokens", [])
                if isinstance(tokens, list) and all(isinstance(token, int) for token in tokens):
                    return tokens
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass

        tokens = self._fallback.encode(text)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"tokens": tokens, "backend": "byte"}, f)
        except OSError as exc:
            logger.debug(f"Không thể ghi disk cache: {exc}")
        return tokens

    def decode(self, tokens: List[int]) -> str:
        return self._fallback.decode(tokens)

    def save_vocab(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        data = {
            "version": "2.1",
            "tokenizer_type": "gemini",
            "backend": "byte",
            "model": self.model,
            "vocab_size": self.vocab_size,
            "special_tokens": {
                "pad": self._pad_token,
                "unk": self._unk_token,
                "bos": self._bos_token,
                "eos": self._eos_token,
            },
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_vocab(cls, filepath: str, **kwargs: Any) -> "GeminiTokenizer":
        if not os.path.exists(filepath):
            raise VocabularyMissingError(vocab_path=filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        special = data.get("special_tokens", {})
        model = data.get("model", "gemini-1.5-flash")
        return cls(
            model=model,
            pad_token=special.get("pad", "<pad>"),
            unk_token=special.get("unk", "<unk>"),
            bos_token=special.get("bos", "<bos>"),
            eos_token=special.get("eos", "<eos>"),
            **kwargs,
        )
