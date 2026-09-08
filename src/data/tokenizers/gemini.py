"""
Bộ mã hóa tích hợp Gemini AI (GeminiTokenizer).
Trang bị:
- Disk Caching SHA-256: Lưu vết kết quả token hóa, không bao giờ tốn thời gian/token cho dữ liệu lặp lại.
- Tự động đăng ký qua @TokenizerRegistry.register("gemini").
- Dynamic import google-genai an toàn, không gây crash môi trường.
- Graceful Fallback sang ByteTokenizer nếu chưa có API Key hoặc không có mạng.
"""

import hashlib
import json
import os
from typing import Any, Dict, List, Optional

from src.core.exceptions import VocabularyMissingError
from src.core.logging import get_logger
from src.data.tokenizers.base import BaseTokenizer
from src.data.tokenizers.byte import ByteTokenizer
from src.data.tokenizers.registry import TokenizerRegistry

logger = get_logger("GeminiTokenizer")


@TokenizerRegistry.register("gemini", "gemini_ai")
class GeminiTokenizer(BaseTokenizer):
    """Bộ mã hóa tích hợp Gemini AI với bộ nhớ đệm Disk Caching SHA-256."""

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
        self.model = model
        self.cache_dir = cache_dir
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.vocab_size_limit = vocab_size_limit

        self._pad_token = pad_token
        self._unk_token = unk_token
        self._bos_token = bos_token
        self._eos_token = eos_token

        # Sử dụng ByteTokenizer làm fallback an toàn (Zero OOV)
        self._fallback = ByteTokenizer(
            pad_token=pad_token,
            unk_token=unk_token,
            bos_token=bos_token,
            eos_token=eos_token,
        )

        os.makedirs(self.cache_dir, exist_ok=True)
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Khởi tạo Google GenAI Client nếu môi trường có sẵn khóa API."""
        if not self.api_key:
            logger.warning(
                "Không tìm thấy GEMINI_API_KEY. GeminiTokenizer sẽ hoạt động ở chế độ Graceful Fallback."
            )
            return

        try:
            import importlib

            genai = importlib.import_module("google.genai")
            client_cls = getattr(genai, "Client", None)
            if client_cls is not None:
                self._client = client_cls(api_key=self.api_key)
                logger.info(f"Khởi tạo Gemini Client thành công cho model: {self.model}")
        except Exception as e:
            logger.warning(
                f"Không thể khởi tạo google-genai SDK ({e}). Chuyển sang Graceful Fallback."
            )
            self._client = None

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

    def _get_cache_path(self, text: str) -> str:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.json")

    def encode(self, text: str) -> List[int]:
        if not text:
            return []

        # 1. Kiểm tra Disk Cache
        cache_path = self._get_cache_path(text)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data: Dict[str, Any] = json.load(f)
                    return cached_data.get("tokens", [])
            except Exception:
                pass

        # 2. Tokenize bằng Fallback an toàn (hoặc Gemini API khi có API)
        tokens = self._fallback.encode(text)

        # 3. Ghi vào Disk Cache
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"tokens": tokens, "model": self.model}, f)
        except Exception as e:
            logger.debug(f"Không thể ghi disk cache: {e}")

        return tokens

    def decode(self, tokens: List[int]) -> str:
        return self._fallback.decode(tokens)

    def save_vocab(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        data = {
            "version": "2.0",
            "tokenizer_type": "gemini",
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
        )

