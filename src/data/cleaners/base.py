"""
Lớp cơ sở trừu tượng cho tất cả các bộ tiền xử lý và làm sạch văn bản (BaseTextPreprocessor).
Trang bị các chức năng:
- Đo lường và thống kê hiệu năng, tỷ lệ nén/cắt giảm ký tự (stats & timing).
- Hỗ trợ xử lý theo lô (batch/lines) và luồng dữ liệu lớn (streaming/generator).
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Iterator, List, Optional

from src.core.exceptions import DataPipelineError
from src.core.logging import get_logger

logger = get_logger("BaseTextPreprocessor")


class BaseTextPreprocessor(ABC):
    """Lớp cơ sở trừu tượng cho toàn bộ các bộ làm sạch văn bản."""

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or self.__class__.__name__
        self._chars_in = 0
        self._chars_out = 0
        self._lines_processed = 0
        self._total_time_sec = 0.0

    @abstractmethod
    def process(self, text: str) -> str:
        """Tiền xử lý và làm sạch một đoạn văn bản."""
        pass

    def __call__(self, text: Any) -> str:
        """Cho phép gọi preprocessor như một hàm: cleaner(text)."""
        if not isinstance(text, str):
            raise DataPipelineError(
                f"Đầu vào cho {self.name} phải là chuỗi ký tự (str), nhận được: {type(text).__name__}",
                details={"input_type": type(text).__name__, "preprocessor": self.name},
                suggestion="Hãy đảm bảo dữ liệu đầu vào đã được decode UTF-8 thành kiểu str hợp lệ.",
            )

        start = time.perf_counter()
        chars_before = len(text)

        result = self.process(text)

        elapsed = time.perf_counter() - start
        self._chars_in += chars_before
        self._chars_out += len(result)
        self._lines_processed += text.count("\n") + 1
        self._total_time_sec += elapsed

        return result

    def process_lines(self, lines: List[str]) -> List[str]:
        """Tiền xử lý văn bản theo từng dòng trong danh sách."""
        return [self(line) for line in lines]

    def process_stream(self, lines: Iterable[str]) -> Iterator[str]:
        """Tiền xử lý theo luồng (Generator) tối ưu bộ nhớ cho file lớn."""
        for line in lines:
            yield self(line)

    def get_stats(self) -> Dict[str, Any]:
        """Trả về báo cáo thống kê hoạt động làm sạch."""
        reduction_chars = self._chars_in - self._chars_out
        reduction_ratio = (reduction_chars / self._chars_in) if self._chars_in > 0 else 0.0
        return {
            "name": self.name,
            "chars_in": self._chars_in,
            "chars_out": self._chars_out,
            "reduction_chars": reduction_chars,
            "reduction_percentage": f"{reduction_ratio * 100:.2f}%",
            "lines_processed": self._lines_processed,
            "total_time_sec": round(self._total_time_sec, 4),
        }

    def reset_stats(self) -> None:
        """Đặt lại bộ đếm thống kê."""
        self._chars_in = 0
        self._chars_out = 0
        self._lines_processed = 0
        self._total_time_sec = 0.0


__all__ = ["BaseTextPreprocessor"]

