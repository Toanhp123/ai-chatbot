"""
Các bộ làm sạch & bộ lọc văn bản chuẩn hóa trên CPU (Standard Text Cleaners).
Bao gồm:
- TextCleaner: Chuẩn hóa Unicode (NFC), loại bỏ ký tự ẩn, số thứ tự đầu câu, chuẩn hóa khoảng trắng và dấu câu.
- LineLengthFilter, DeduplicationFilter, RepetitionFilter: Các bộ lọc chất lượng văn bản.
- TextPreprocessingPipeline: Chuỗi hóa nhiều bước xử lý tuần tự.
- PassthroughCleaner: Bộ làm sạch giữ nguyên văn bản gốc.
"""

import os
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Set, Union

from src.core.exceptions import DataPipelineError
from src.core.logging import get_logger
from src.data.cleaners.base import BaseTextPreprocessor
from src.data.cleaners.registry import CleanerRegistry

logger = get_logger("StandardCleaner")


@CleanerRegistry.register("default", "standard", "text_cleaner")
class TextCleaner(BaseTextPreprocessor):
    """Bộ làm sạch văn bản toàn diện cho huấn luyện mô hình ngôn ngữ tiếng Việt."""

    def __init__(
        self,
        clean_line_numbers: bool = True,
        normalize_ws: bool = True,
        normalize_uni: bool = True,
        remove_control_chars: bool = True,
        strip_html: bool = False,
        normalize_punct: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(name="TextCleaner")
        self.clean_line_numbers = clean_line_numbers
        self.normalize_ws = normalize_ws
        self.normalize_uni = normalize_uni
        self.remove_control_chars = remove_control_chars
        self.strip_html = strip_html
        self.normalize_punct = normalize_punct

    def process(self, text: str) -> str:
        """Thực thi chuỗi làm sạch tuần tự theo cấu hình."""
        if not text:
            return ""

        result = text

        # 1. Loại bỏ ký tự điều khiển ẩn & BOM
        if self.remove_control_chars:
            result = self.remove_control_characters(result)

        # 2. Chuẩn hóa Unicode dựng sẵn (NFC cho tiếng Việt)
        if self.normalize_uni:
            result = self.normalize_unicode(result, form="NFC")

        # 3. Bóc tách thẻ HTML nếu được yêu cầu
        if self.strip_html:
            result = self.strip_html_and_urls(result, strip_html=True, strip_urls=False)

        # 4. Chuẩn hóa dấu câu (ngoặc kép, gạch ngang)
        if self.normalize_punct:
            result = self.normalize_punctuation(result)

        # 5. Loại bỏ số thứ tự đầu câu
        if self.clean_line_numbers:
            result = self.remove_line_numbers(result)

        # 6. Chuẩn hóa khoảng trắng
        if self.normalize_ws:
            result = self.normalize_whitespace(result)

        return result

    @staticmethod
    def remove_line_numbers(text: str) -> str:
        """Loại bỏ số thứ tự đầu câu như '1..', '10.. ', '36 ', '9,,'."""
        cleaned_lines: List[str] = []
        for line in text.splitlines():
            cleaned = re.sub(r"^\s*\d+[\.,\s]+", "", line).strip()
            if cleaned:
                cleaned_lines.append(cleaned)
        return "\n".join(cleaned_lines) + "\n" if cleaned_lines else ""

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Chuẩn hóa khoảng trắng liên tiếp và xóa khoảng trắng thừa đầu/cuối dòng."""
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(lines)

    @staticmethod
    def normalize_unicode(text: str, form: str = "NFC") -> str:
        """Chuẩn hóa bảng mã Unicode (mặc định NFC dựng sẵn - chuẩn tiếng Việt)."""
        if form not in ("NFC", "NFD", "NFKC", "NFKD"):
            raise DataPipelineError(
                f"Dạng chuẩn hóa Unicode '{form}' không hợp lệ. Chỉ chấp nhận: NFC, NFD, NFKC, NFKD.",
                details={"form": form},
                suggestion="Hãy sử dụng 'NFC' cho tiếng Việt dựng sẵn hoặc 'NFKC' để chuẩn hóa tương thích.",
            )
        return unicodedata.normalize(form, text)

    @staticmethod
    def remove_control_characters(text: str, keep_newlines: bool = True) -> str:
        """Loại bỏ ký tự điều khiển ẩn, zero-width space, và UTF-8 BOM."""
        cleaned_chars: List[str] = []
        for ch in text:
            code = ord(ch)
            if keep_newlines and ch in ("\n", "\r", "\t"):
                cleaned_chars.append(ch)
                continue
            if code in (0xFEFF, 0x200B, 0x200C, 0x200D, 0x2060):
                continue
            category = unicodedata.category(ch)
            if not category.startswith("C"):
                cleaned_chars.append(ch)
        return "".join(cleaned_chars)

    @staticmethod
    def strip_html_and_urls(
        text: str,
        strip_html: bool = True,
        strip_urls: bool = False,
        strip_emails: bool = False,
    ) -> str:
        """Loại bỏ thẻ HTML, URL web, hoặc địa chỉ email trong corpus crawl."""
        result = text
        if strip_html:
            result = re.sub(r"<[^>]+>", " ", result)
        if strip_urls:
            result = re.sub(r"https?://\S+|www\.\S+", " ", result)
        if strip_emails:
            result = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", " ", result)
        return result

    @staticmethod
    def normalize_punctuation(text: str) -> str:
        """Chuẩn hóa dấu ngoặc kép cong, dấu gạch ngang typographic thành ký tự ASCII."""
        result = re.sub(r"[“”„«»]", '"', text)
        result = re.sub(r"[‘’‚‹›]", "'", result)
        result = re.sub(r"[–—―]", "-", result)
        result = result.replace("…", "...")
        return result

    def clean_file(
        self,
        input_path: str,
        output_path: str,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """Làm sạch toàn bộ file văn bản theo luồng (streaming), tránh tràn RAM."""
        if not os.path.exists(input_path):
            raise DataPipelineError(
                f"File nguồn không tồn tại: {input_path}",
                details={"input_path": input_path},
                suggestion="Hãy kiểm tra lại đường dẫn file dữ liệu đầu vào.",
            )

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        raw_size = os.path.getsize(input_path)

        with (
            open(input_path, "r", encoding=encoding, errors="replace") as fin,
            open(output_path, "w", encoding=encoding) as fout,
        ):
            for line in fin:
                cleaned_line = self(line)
                if cleaned_line.strip():
                    fout.write(cleaned_line.rstrip() + "\n")

        cleaned_size = os.path.getsize(output_path)
        stats = self.get_stats()
        stats["raw_file_size_bytes"] = raw_size
        stats["cleaned_file_size_bytes"] = cleaned_size

        return stats


class LineLengthFilter(BaseTextPreprocessor):
    """Bộ lọc giới hạn độ dài dòng văn bản."""

    def __init__(self, min_len: int = 2, max_len: int = 4096) -> None:
        super().__init__(name="LineLengthFilter")
        self.min_len = min_len
        self.max_len = max_len

    def process(self, text: str) -> str:
        cleaned_lines: List[str] = []
        for line in text.splitlines():
            line_str = line.strip()
            if self.min_len <= len(line_str) <= self.max_len:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)


class DeduplicationFilter(BaseTextPreprocessor):
    """Bộ lọc khử trùng lặp văn bản (consecutive hoặc global)."""

    def __init__(self, mode: str = "consecutive") -> None:
        super().__init__(name="DeduplicationFilter")
        if mode not in ("consecutive", "global"):
            raise ValueError(
                f"Chế độ deduplication '{mode}' không hợp lệ. Chỉ chấp nhận 'consecutive' hoặc 'global'."
            )
        self.mode = mode
        self._seen: Set[str] = set()

    def process(self, text: str) -> str:
        lines = text.splitlines()
        if not lines:
            return ""

        result_lines: List[str] = []
        if self.mode == "consecutive":
            prev_line: Optional[str] = None
            for line in lines:
                normalized = line.strip()
                if normalized != prev_line:
                    result_lines.append(line)
                    prev_line = normalized
        else:  # global
            for line in lines:
                normalized = line.strip()
                if normalized not in self._seen:
                    self._seen.add(normalized)
                    result_lines.append(line)

        return "\n".join(result_lines)

    def reset_stats(self) -> None:
        super().reset_stats()
        self._seen.clear()


class RepetitionFilter(BaseTextPreprocessor):
    """Bộ lọc nén các ký tự lặp lại bất thường."""

    def __init__(self, max_consecutive_chars: int = 3) -> None:
        super().__init__(name="RepetitionFilter")
        self.max_consecutive_chars = max_consecutive_chars
        self._char_pattern = re.compile(r"(.)\1{" + str(max_consecutive_chars) + r",}")

    def process(self, text: str) -> str:
        if not text:
            return ""
        repl = r"\1" * self.max_consecutive_chars
        return self._char_pattern.sub(repl, text)


StepType = Union[BaseTextPreprocessor, Callable[[str], str]]


@CleanerRegistry.register("pipeline", "full")
class TextPreprocessingPipeline(BaseTextPreprocessor):
    """Đường ống chuỗi hóa các thao tác tiền xử lý văn bản."""

    def __init__(
        self,
        steps: Optional[List[StepType]] = None,
        name: str = "TextPreprocessingPipeline",
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name)
        self.steps: List[StepType] = list(steps) if steps is not None else []

    def add_step(self, step: StepType) -> "TextPreprocessingPipeline":
        """Thêm một bước tiền xử lý vào cuối đường ống."""
        self.steps.append(step)
        return self

    def process(self, text: str) -> str:
        """Thực thi tuần tự toàn bộ các bước trong đường ống."""
        current_text = text
        for step in self.steps:
            if isinstance(step, BaseTextPreprocessor):
                current_text = step.process(current_text)
            elif callable(step):
                current_text = step(current_text)
            else:
                raise DataPipelineError(
                    f"Bước tiền xử lý không hợp lệ trong pipeline: {type(step).__name__}",
                    details={"step_type": type(step).__name__},
                    suggestion="Đảm bảo mỗi bước kế thừa BaseTextPreprocessor hoặc là một callable nhận/trả về str.",
                )
        return current_text

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Lấy báo cáo thống kê toàn diện của pipeline và từng bước con."""
        step_stats = []
        for i, step in enumerate(self.steps):
            if isinstance(step, BaseTextPreprocessor):
                stats = step.get_stats()
                step_stats.append(stats)
            else:
                name = getattr(step, "__name__", f"step_{i}")
                step_stats.append({"name": name, "type": "callable"})

        overall = self.get_stats()
        overall["steps"] = step_stats
        return overall

    def reset_stats(self) -> None:
        """Đặt lại số liệu thống kê của pipeline và toàn bộ các bước con."""
        super().reset_stats()
        for step in self.steps:
            if isinstance(step, BaseTextPreprocessor):
                step.reset_stats()


@CleanerRegistry.register("none", "passthrough", "raw")
class PassthroughCleaner(BaseTextPreprocessor):
    """Bộ làm sạch giữ nguyên văn bản gốc (No-op)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="PassthroughCleaner")

    def process(self, text: str) -> str:
        return text


__all__ = [
    "TextCleaner",
    "LineLengthFilter",
    "DeduplicationFilter",
    "RepetitionFilter",
    "TextPreprocessingPipeline",
    "PassthroughCleaner",
]
