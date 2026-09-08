"""
Bộ mã hóa cấp độ ký tự (Character-level Tokenizer).
Hỗ trợ Unicode Tiếng Việt, Out-of-Vocabulary handling, và special tokens.
"""

import json
import os
from typing import Any, List, Optional

from src.core.exceptions import DataPipelineError, VocabularyMissingError
from src.data.tokenizers.base import BaseTokenizer
from src.data.tokenizers.registry import TokenizerRegistry


@TokenizerRegistry.register("char", "character")
class CharTokenizer(BaseTokenizer):
    """Bộ mã hóa văn bản cấp độ ký tự (Character-level Tokenizer)."""

    def __init__(
        self,
        text: Optional[str] = None,
        vocab: Optional[List[str]] = None,
        add_special_tokens: bool = False,
        pad_token: str = "<pad>",
        unk_token: str = "<unk>",
        bos_token: str = "<bos>",
        eos_token: str = "<eos>",
    ) -> None:
        self.add_special_tokens = add_special_tokens
        self._pad_token_str = pad_token
        self._unk_token_str = unk_token
        self._bos_token_str = bos_token
        self._eos_token_str = eos_token

        raw_chars: List[str] = []
        if vocab is not None:
            raw_chars = sorted(list(set(vocab)))
        elif text is not None:
            raw_chars = sorted(list(set(text)))
        else:
            raise DataPipelineError(
                "Cần cung cấp text hoặc vocab để khởi tạo CharTokenizer.",
                details={"text": None, "vocab": None},
                suggestion="Hãy truyền chuỗi văn bản mẫu text='...' hoặc danh sách ký tự vocab=['a', 'b'].",
            )

        if not raw_chars and not add_special_tokens:
            raise DataPipelineError(
                "Bảng từ vựng rỗng!",
                suggestion="Cung cấp văn bản không rỗng để xây dựng từ điển ký tự.",
            )

        if add_special_tokens:
            special_tokens = [pad_token, unk_token, bos_token, eos_token]
            filtered_raw = [ch for ch in raw_chars if ch not in special_tokens]
            self.chars: List[str] = special_tokens + sorted(filtered_raw)
            self._pad_id: Optional[int] = self.chars.index(pad_token)
            self._unk_id: Optional[int] = self.chars.index(unk_token)
            self._bos_id: Optional[int] = self.chars.index(bos_token)
            self._eos_id: Optional[int] = self.chars.index(eos_token)
        else:
            self.chars = raw_chars
            self._pad_id = None
            self._unk_id = None
            self._bos_id = None
            self._eos_id = None

        self._vocab_size = len(self.chars)
        self.stoi = {ch: i for i, ch in enumerate(self.chars)}
        self.itos = {i: ch for i, ch in enumerate(self.chars)}

    @property
    def vocab_size(self) -> int:
        return self._vocab_size

    @property
    def pad_token(self) -> Optional[str]:
        return self._pad_token_str if self.add_special_tokens else None

    @property
    def pad_token_id(self) -> Optional[int]:
        return self._pad_id

    @property
    def unk_token(self) -> Optional[str]:
        return self._unk_token_str if self.add_special_tokens else None

    @property
    def unk_token_id(self) -> Optional[int]:
        return self._unk_id

    @property
    def bos_token(self) -> Optional[str]:
        return self._bos_token_str if self.add_special_tokens else None

    @property
    def bos_token_id(self) -> Optional[int]:
        return self._bos_id

    @property
    def eos_token(self) -> Optional[str]:
        return self._eos_token_str if self.add_special_tokens else None

    @property
    def eos_token_id(self) -> Optional[int]:
        return self._eos_id

    def identity_payload(self) -> dict[str, Any]:
        return {
            "tokenizer_type": "char",
            "vocab": list(self.chars),
            "add_special_tokens": self.add_special_tokens,
            "special_tokens": {
                "pad": self._pad_token_str,
                "unk": self._unk_token_str,
                "bos": self._bos_token_str,
                "eos": self._eos_token_str,
            }
            if self.add_special_tokens
            else {},
        }

    def encode(self, text: str) -> List[int]:
        if self._unk_id is not None:
            return [self.stoi.get(c, self._unk_id) for c in text]
        return [self.stoi[c] for c in text if c in self.stoi]

    def decode(self, tokens: List[int]) -> str:
        return "".join([self.itos.get(i, "") for i in tokens])

    def save_vocab(self, filepath: str) -> None:
        """Lưu trữ từ điển vào file JSON kèm metadata."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        data = {
            "version": "2.0",
            "tokenizer_type": "char",
            "vocab_size": self._vocab_size,
            "add_special_tokens": self.add_special_tokens,
            "special_tokens": {
                "pad": self._pad_token_str,
                "unk": self._unk_token_str,
                "bos": self._bos_token_str,
                "eos": self._eos_token_str,
            }
            if self.add_special_tokens
            else {},
            "vocab": self.chars,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_vocab(cls, filepath: str, **kwargs: Any) -> "CharTokenizer":
        """Tải từ điển từ file JSON (hỗ trợ v1 list và v2 dict)."""
        if not os.path.exists(filepath):
            raise VocabularyMissingError(vocab_path=filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)

        if isinstance(loaded_data, list):
            return cls(vocab=loaded_data, add_special_tokens=False)
        elif isinstance(loaded_data, dict):
            chars = loaded_data.get("vocab", [])
            add_special = loaded_data.get("add_special_tokens", False)
            special_tokens = loaded_data.get("special_tokens", {})
            return cls(
                vocab=chars,
                add_special_tokens=add_special,
                pad_token=special_tokens.get("pad", "<pad>"),
                unk_token=special_tokens.get("unk", "<unk>"),
                bos_token=special_tokens.get("bos", "<bos>"),
                eos_token=special_tokens.get("eos", "<eos>"),
            )
        else:
            raise DataPipelineError(
                f"Định dạng file từ vựng không hợp lệ tại {filepath}",
                details={"data_type": type(loaded_data).__name__},
                suggestion="File vocab.json phải là mảng JSON hoặc đối tượng JSON chứa trường 'vocab'.",
            )

