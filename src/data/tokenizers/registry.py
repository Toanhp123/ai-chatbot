"""
Cơ chế điều phối và đăng ký bộ mã hóa văn bản (Tokenizer Registry).
Bao gồm:
- TokenizerRegistry: Quản lý đăng ký động, tạo đối tượng (Factory) và phục hồi từ vocab.json (Polymorphic Deserializer).
- get_tokenizer: Hàm factory tiện ích tra cứu từ Registry.
- load_tokenizer: Hàm nạp tự động nhận diện loại Tokenizer từ file vocab.json.
"""

import json
import os
from typing import Any, Callable, Dict, List, Type

from src.core.exceptions import DataPipelineError, VocabularyMissingError
from src.core.logging import get_logger
from src.data.tokenizers.base import BaseTokenizer

logger = get_logger("TokenizerRegistry")


class TokenizerRegistry:
    """Registry trung tâm quản lý đăng ký và khởi tạo động các bộ Tokenizer."""

    _registry: Dict[str, Type[BaseTokenizer]] = {}

    @classmethod
    def register(cls, *names: str) -> Callable[[Any], Any]:
        """Decorator đăng ký một Tokenizer class với một hoặc nhiều tên định danh."""

        def decorator(subclass: Any) -> Any:
            for name in names:
                cls._registry[name.lower().strip()] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> BaseTokenizer:
        """Khởi tạo một instance Tokenizer từ tên đăng ký."""
        name_clean = name.lower().strip()
        if name_clean in cls._registry:
            target_cls = cls._registry[name_clean]
            return target_cls(**kwargs)

        available = list(cls._registry.keys())
        raise DataPipelineError(
            f"Loại Tokenizer không được hỗ trợ: '{name}'",
            details={"requested_type": name, "available_types": available},
            suggestion=f"Hãy chọn loại tokenizer khả dụng: {available} hoặc đăng ký bằng @TokenizerRegistry.register('{name}')",
        )

    @classmethod
    def load(cls, filepath: str, **kwargs: Any) -> BaseTokenizer:
        """Phục hồi đa hình Tokenizer từ file vocab.json dựa vào metadata 'tokenizer_type'."""
        if not os.path.exists(filepath):
            raise VocabularyMissingError(vocab_path=filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            # Định dạng v1 legacy: danh sách mảng ký tự
            char_cls = cls._registry.get("char")
            if char_cls is not None:
                return char_cls.load_vocab(filepath, **kwargs)
            raise DataPipelineError("Không tìm thấy CharTokenizer trong registry để nạp legacy vocab.")

        if isinstance(data, dict):
            raw_type = data.get("tokenizer_type", "char")
            norm_type = str(raw_type).lower().strip()

            target_cls = cls._registry.get(norm_type)
            if target_cls is not None:
                return target_cls.load_vocab(filepath, **kwargs)

            raise DataPipelineError(
                f"Loại Tokenizer trong metadata không được hỗ trợ: '{raw_type}'",
                details={"requested_type": norm_type, "available_types": cls.list_available()},
                suggestion="Không tự động fallback vì có thể làm thay đổi ngữ nghĩa token của checkpoint.",
            )

        raise DataPipelineError(
            f"Định dạng file từ vựng không hợp lệ tại {filepath}",
            details={"data_type": type(data).__name__},
            suggestion="File vocab.json phải là mảng JSON hoặc đối tượng JSON hợp lệ.",
        )

    @classmethod
    def list_available(cls) -> List[str]:
        """Danh sách tất cả các loại Tokenizer đã đăng ký."""
        return sorted(list(cls._registry.keys()))


def get_tokenizer(tokenizer_type: str = "char", **kwargs: Any) -> BaseTokenizer:
    """Factory tra cứu và khởi tạo Tokenizer từ Registry."""
    return TokenizerRegistry.create(tokenizer_type, **kwargs)


def load_tokenizer(vocab_path: str, **kwargs: Any) -> BaseTokenizer:
    """Factory nạp và phục hồi đúng lớp Tokenizer từ file từ vựng."""
    return TokenizerRegistry.load(vocab_path, **kwargs)


def load_tokenizer_state(state: object) -> BaseTokenizer:
    """Reconstruct a tokenizer from checkpoint-embedded semantic state."""
    if not isinstance(state, dict):
        raise DataPipelineError("Tokenizer state trong checkpoint không hợp lệ.")

    raw_type = state.get("tokenizer_type")
    norm_type = str(raw_type).lower().strip() if raw_type is not None else ""
    special = state.get("special_tokens", {})
    if not isinstance(special, dict):
        special = {}

    if norm_type == "char":
        vocab = state.get("vocab")
        if not isinstance(vocab, list) or not all(isinstance(token, str) for token in vocab):
            raise DataPipelineError("Checkpoint CharTokenizer thiếu vocab hợp lệ.")
        return TokenizerRegistry.create(
            "char",
            vocab=vocab,
            add_special_tokens=bool(state.get("add_special_tokens", False)),
            pad_token=str(special.get("pad", "<pad>")),
            unk_token=str(special.get("unk", "<unk>")),
            bos_token=str(special.get("bos", "<bos>")),
            eos_token=str(special.get("eos", "<eos>")),
        )

    if norm_type == "byte":
        return TokenizerRegistry.create(
            "byte",
            pad_token=str(special.get("pad", "<pad>")),
            unk_token=str(special.get("unk", "<unk>")),
            bos_token=str(special.get("bos", "<bos>")),
            eos_token=str(special.get("eos", "<eos>")),
        )

    raise DataPipelineError(
        f"Tokenizer state không thể phục hồi: '{raw_type}'.",
        details={"tokenizer_type": raw_type, "available_types": ["char", "byte"]},
        suggestion="Dùng checkpoint v3 được tạo bởi CharTokenizer/ByteTokenizer tương thích.",
    )


__all__ = [
    "BaseTokenizer",
    "TokenizerRegistry",
    "get_tokenizer",
    "load_tokenizer",
    "load_tokenizer_state",
]
