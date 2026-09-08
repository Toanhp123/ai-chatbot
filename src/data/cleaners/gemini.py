"""
Bộ tiền xử lý & làm sạch văn bản sử dụng Google Gemini AI (Plug-and-Play Cleaner).
Tự động đăng ký vào CleanerRegistry qua decorator @CleanerRegistry.register('gemini').

Trang bị:
- Disk Caching SHA-256: Lưu đệm kết quả vào đĩa, tiết kiệm 100% chi phí token và chống trùng lặp.
- Graceful Fallback: Tự động chuyển về TextCleaner chuẩn nếu chưa cấu hình GEMINI_API_KEY.
"""

import hashlib
import importlib
import os
from typing import Any, Optional

from src.core.logging import get_logger
from src.data.cleaners.base import BaseTextPreprocessor
from src.data.cleaners.registry import CleanerRegistry
from src.data.cleaners.standard import TextCleaner

logger = get_logger("GeminiCleaner")


@CleanerRegistry.register("gemini", "gemini_ai", "gemini_cleaner")
class GeminiTextCleaner(BaseTextPreprocessor):
    """Bộ làm sạch văn bản thông minh tích hợp Google Gemini AI."""

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        api_key: Optional[str] = None,
        cache_dir: str = ".cache/gemini",
        clean_line_numbers: bool = True,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name="GeminiTextCleaner")
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.cache_dir = cache_dir
        self.clean_line_numbers = clean_line_numbers
        self.system_instruction = system_instruction or (
            "Bạn là trợ lý AI làm sạch dữ liệu văn bản tiếng Việt. "
            "Hãy loại bỏ rác, thẻ HTML, ký tự dị thường, giữ nguyên vần điệu và nội dung văn học."
        )

        # Bộ làm sạch fallback khi offline hoặc không có API key
        self._fallback_cleaner = TextCleaner(
            clean_line_numbers=clean_line_numbers,
            normalize_ws=True,
            normalize_uni=True,
            normalize_punct=True,
        )

        os.makedirs(self.cache_dir, exist_ok=True)
        self._cache_hits = 0
        self._api_calls = 0

    def _get_cache_path(self, text: str) -> str:
        """Tạo đường dẫn file cache theo mã băm SHA-256 của chuỗi văn bản."""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.txt")

    def process(self, text: str) -> str:
        """Xử lý văn bản với Disk Cache SHA-256 và Gemini API."""
        if not text.strip():
            return ""

        # 1. Kiểm tra Disk Cache (O(1) thời gian, $0 chi phí)
        cache_file = self._get_cache_path(text)
        if os.path.exists(cache_file):
            self._cache_hits += 1
            with open(cache_file, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        # 2. Kiểm tra API Key
        if not self.api_key:
            logger.warning(
                "⚠️ Chưa thiết lập GEMINI_API_KEY! Tự động chuyển về TextCleaner chuẩn (NFC/Regex)."
            )
            cleaned = self._fallback_cleaner(text)
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(cleaned)
            return cleaned

        # 3. Gọi Gemini API
        try:
            cleaned = self._call_gemini_api(text)
            self._api_calls += 1
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(cleaned)
            return cleaned
        except Exception as e:
            logger.error(f"❌ Lỗi khi gọi Gemini API ({e}). Kích hoạt Fallback Cleaner an toàn.")
            return self._fallback_cleaner(text)

    def _call_gemini_api(self, text: str) -> str:
        """Hàm nội bộ gọi Gemini API bằng dynamic import an toàn."""
        # 1. Thử nạp google.genai (SDK chính thức mới)
        try:
            genai_mod: Any = importlib.import_module("google.genai")
            client = genai_mod.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=f"{self.system_instruction}\n\nVăn bản đầu vào:\n{text}",
            )
            return str(getattr(response, "text", text) or text)
        except (ImportError, AttributeError, ModuleNotFoundError):
            pass

        # 2. Thử nạp google.generativeai (SDK cũ)
        try:
            legacy_genai: Any = importlib.import_module("google.generativeai")
            legacy_genai.configure(api_key=self.api_key)
            model_inst = legacy_genai.GenerativeModel(self.model)
            response = model_inst.generate_content(
                f"{self.system_instruction}\n\nVăn bản đầu vào:\n{text}"
            )
            return str(getattr(response, "text", text) or text)
        except (ImportError, AttributeError, ModuleNotFoundError):
            logger.warning(
                "Chưa cài đặt SDK 'google-genai' hoặc 'google-generativeai'. Chạy: pip install google-genai"
            )
            return self._fallback_cleaner(text)

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats["cache_hits"] = self._cache_hits
        stats["api_calls"] = self._api_calls
        stats["model"] = self.model
        return stats


__all__ = ["GeminiTextCleaner"]

