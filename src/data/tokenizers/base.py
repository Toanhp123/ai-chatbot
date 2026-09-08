"""
Lớp cơ sở trừu tượng cho tất cả các bộ mã hóa văn bản (BaseTokenizer).
Bao gồm:
- Định nghĩa các thuộc tính trừu tượng: vocab_size, encode, decode, save_vocab, load_vocab.
- Các thuộc tính token đặc biệt (unk_token, bos_token, eos_token, pad_token).
- Xử lý theo lô (batch_encode, batch_decode).
- Chuyển đổi và tạo Tensor cho PyTorch với hỗ trợ Padding & Attention Mask.
"""

from abc import ABC, abstractmethod
import hashlib
import json
from typing import Any, Dict, List, Optional

import torch


class IncrementalTextDecoder:
    """Stateful decoder used by streaming generation."""

    def __init__(self, tokenizer: "BaseTokenizer") -> None:
        self.tokenizer = tokenizer

    def push(self, tokens: List[int]) -> str:
        return self.tokenizer.decode(tokens) if tokens else ""

    def finish(self) -> str:
        return ""


class BaseTokenizer(ABC):
    """Lớp cơ sở trừu tượng cho tất cả Tokenizers."""

    @property
    @abstractmethod
    def vocab_size(self) -> int:
        """Kích thước bảng từ vựng."""
        pass

    @abstractmethod
    def encode(self, text: str) -> List[int]:
        """Mã hóa văn bản thành chuỗi token IDs."""
        pass

    @abstractmethod
    def decode(self, tokens: List[int]) -> str:
        """Giải mã chuỗi token IDs trở lại văn bản."""
        pass

    @property
    def unk_token(self) -> Optional[str]:
        """Ký tự đại diện cho token không xác định (Out-of-Vocabulary)."""
        return None

    @property
    def unk_token_id(self) -> Optional[int]:
        """ID của token không xác định."""
        return None

    @property
    def bos_token(self) -> Optional[str]:
        """Ký tự đại diện cho token bắt đầu chuỗi."""
        return None

    @property
    def bos_token_id(self) -> Optional[int]:
        """ID của token bắt đầu chuỗi (Beginning-Of-Sequence)."""
        return None

    @property
    def eos_token(self) -> Optional[str]:
        """Ký tự đại diện cho token kết thúc chuỗi."""
        return None

    @property
    def eos_token_id(self) -> Optional[int]:
        """ID của token kết thúc chuỗi (End-Of-Sequence)."""
        return None

    @property
    def pad_token(self) -> Optional[str]:
        """Ký tự đại diện cho token đệm."""
        return None

    @property
    def pad_token_id(self) -> Optional[int]:
        """ID của token đệm (Padding)."""
        return None

    def create_incremental_decoder(self) -> IncrementalTextDecoder:
        """Create a stateful decoder for token chunks emitted over time."""
        return IncrementalTextDecoder(self)

    def identity_payload(self) -> Dict[str, Any]:
        """Canonical semantic identity used to bind checkpoints to token IDs."""
        return {
            "tokenizer_type": f"{type(self).__module__}.{type(self).__qualname__}",
            "vocab_size": self.vocab_size,
            "special_tokens": {
                "pad": self.pad_token,
                "unk": self.unk_token,
                "bos": self.bos_token,
                "eos": self.eos_token,
            },
        }

    def batch_encode(self, texts: List[str]) -> List[List[int]]:
        """Mã hóa một danh sách nhiều chuỗi văn bản thành danh sách token IDs."""
        return [self.encode(text) for text in texts]

    def batch_decode(self, batch_tokens: List[List[int]]) -> List[str]:
        """Giải mã một danh sách các chuỗi token IDs thành danh sách văn bản."""
        return [self.decode(tokens) for tokens in batch_tokens]

    def encode_as_tensor(self, text: str, device: Optional[str] = None) -> torch.Tensor:
        """Mã hóa văn bản trực tiếp thành 1D PyTorch Long Tensor."""
        tokens = self.encode(text)
        t = torch.tensor(tokens, dtype=torch.long)
        return t.to(device) if device else t

    def encode_batch_tensors(
        self,
        texts: List[str],
        max_length: Optional[int] = None,
        padding: bool = True,
        truncation: bool = True,
        device: Optional[str] = None,
    ) -> Dict[str, torch.Tensor]:
        """Mã hóa lô văn bản thành PyTorch Tensors có hỗ trợ đệm (Padding) và Attention Mask."""
        batch_ids = self.batch_encode(texts)

        if truncation and max_length is not None:
            batch_ids = [ids[:max_length] for ids in batch_ids]

        if padding:
            target_len = (
                max_length
                if max_length is not None
                else max((len(ids) for ids in batch_ids), default=0)
            )
            pad_id = self.pad_token_id if self.pad_token_id is not None else 0

            padded_ids: List[List[int]] = []
            attention_masks: List[List[int]] = []

            for ids in batch_ids:
                curr_len = len(ids)
                pad_count = max(0, target_len - curr_len)
                padded_ids.append(ids + [pad_id] * pad_count)
                attention_masks.append([1] * curr_len + [0] * pad_count)

            input_ids_tensor = torch.tensor(padded_ids, dtype=torch.long)
            attn_mask_tensor = torch.tensor(attention_masks, dtype=torch.long)
        else:
            input_ids_tensor = torch.tensor(batch_ids, dtype=torch.long)
            attn_mask_tensor = torch.ones_like(input_ids_tensor)

        if device:
            input_ids_tensor = input_ids_tensor.to(device)
            attn_mask_tensor = attn_mask_tensor.to(device)

        return {
            "input_ids": input_ids_tensor,
            "attention_mask": attn_mask_tensor,
        }

    @abstractmethod
    def save_vocab(self, filepath: str) -> None:
        """Lưu trữ bảng từ vựng / metadata vào file."""
        pass

    @classmethod
    def load_vocab(cls, filepath: str, **kwargs: Any) -> "BaseTokenizer":
        """Tải và phục hồi tokenizer từ file từ vựng."""
        raise NotImplementedError(
            f"{cls.__name__} chưa triển khai phương thức nạp từ điển 'load_vocab'."
        )


def get_tokenizer_identity(tokenizer: BaseTokenizer) -> Dict[str, Any]:
    """Return a stable fingerprint plus canonical payload for checkpoint validation."""
    payload = tokenizer.identity_payload()
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "fingerprint": hashlib.sha256(canonical).hexdigest(),
        "payload": payload,
    }


__all__ = ["BaseTokenizer", "IncrementalTextDecoder", "get_tokenizer_identity"]

