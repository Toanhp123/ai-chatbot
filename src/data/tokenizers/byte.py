"""
Bộ mã hóa cấp độ byte UTF-8 tiêu chuẩn công nghiệp.
Kích thước 260 tokens, Zero OOV, hỗ trợ đa ngữ và emoji.
"""

import json
import os
from typing import Any, List, Optional

from src.core.exceptions import VocabularyMissingError
from src.data.tokenizers.base import BaseTokenizer
from src.data.tokenizers.registry import TokenizerRegistry


@TokenizerRegistry.register("byte", "utf8", "utf-8")
class ByteTokenizer(BaseTokenizer):
    """Bộ mã hóa cấp độ byte UTF-8 tiêu chuẩn công nghiệp. Kích thước 260 tokens, Zero OOV."""

    def __init__(
        self,
        pad_token: str = "<pad>",
        unk_token: str = "<unk>",
        bos_token: str = "<bos>",
        eos_token: str = "<eos>",
        **kwargs: Any,
    ) -> None:
        self._pad_token = pad_token
        self._unk_token = unk_token
        self._bos_token = bos_token
        self._eos_token = eos_token

        self._num_bytes = 256
        self._pad_id = 256
        self._unk_id = 257
        self._bos_id = 258
        self._eos_id = 259
        self._vocab_size = 260

    @property
    def vocab_size(self) -> int:
        return self._vocab_size

    @property
    def pad_token(self) -> Optional[str]:
        return self._pad_token

    @property
    def pad_token_id(self) -> Optional[int]:
        return self._pad_id

    @property
    def unk_token(self) -> Optional[str]:
        return self._unk_token

    @property
    def unk_token_id(self) -> Optional[int]:
        return self._unk_id

    @property
    def bos_token(self) -> Optional[str]:
        return self._bos_token

    @property
    def bos_token_id(self) -> Optional[int]:
        return self._bos_id

    @property
    def eos_token(self) -> Optional[str]:
        return self._eos_token

    @property
    def eos_token_id(self) -> Optional[int]:
        return self._eos_id

    def encode(self, text: str) -> List[int]:
        if not text:
            return []
        return list(text.encode("utf-8"))

    def decode(self, tokens: List[int]) -> str:
        if not tokens:
            return ""
        valid_bytes = bytes([t for t in tokens if 0 <= t < 256])
        return valid_bytes.decode("utf-8", errors="replace")

    def save_vocab(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        data = {
            "version": "2.0",
            "tokenizer_type": "byte",
            "vocab_size": self._vocab_size,
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
    def load_vocab(cls, filepath: str, **kwargs: Any) -> "ByteTokenizer":
        if not os.path.exists(filepath):
            raise VocabularyMissingError(vocab_path=filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        special = data.get("special_tokens", {})
        return cls(
            pad_token=special.get("pad", "<pad>"),
            unk_token=special.get("unk", "<unk>"),
            bos_token=special.get("bos", "<bos>"),
            eos_token=special.get("eos", "<eos>"),
        )
