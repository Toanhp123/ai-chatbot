"""
Bộ kiểm thử toàn diện cho hệ thống Tiền xử lý dữ liệu (cleaner.py).
Đảm bảo chuẩn hóa Unicode NFC, filters, pipeline streaming và factory get_cleaner.
"""

import unicodedata

import pytest

from src.core.exceptions import DataPipelineError
from src.data.cleaners import (
    BaseTextPreprocessor,
    CleanerRegistry,
    DeduplicationFilter,
    GeminiTextCleaner,
    LineLengthFilter,
    PassthroughCleaner,
    RepetitionFilter,
    TextCleaner,
    TextPreprocessingPipeline,
    get_cleaner,
)


def test_cleaner_hierarchy_and_factory():
    cleaner = TextCleaner()
    pipeline = TextPreprocessingPipeline()
    length_filter = LineLengthFilter()

    # Kiểm tra tính kế thừa BaseTextPreprocessor
    assert isinstance(cleaner, BaseTextPreprocessor)
    assert isinstance(pipeline, BaseTextPreprocessor)
    assert isinstance(length_filter, BaseTextPreprocessor)

    # Kiểm tra factory get_cleaner
    default_c = get_cleaner("default")
    assert isinstance(default_c, TextCleaner)
    pipeline_c = get_cleaner("pipeline")
    assert isinstance(pipeline_c, TextPreprocessingPipeline)
    pass_c = get_cleaner("none")
    assert isinstance(pass_c, PassthroughCleaner)


def test_cleaner_registry_extensibility(tmp_path):
    # Kiểm tra gemini đã đăng ký tự động vào CleanerRegistry
    assert "gemini" in CleanerRegistry.list_available()
    gemini_c = CleanerRegistry.create("gemini", cache_dir=str(tmp_path / "gemini_cache"))
    assert isinstance(gemini_c, GeminiTextCleaner)

    # Thử nghiệm tính năng Disk Cache SHA-256 của GeminiTextCleaner
    sample_text = "1.. Trăm năm trong cõi người ta,"
    cleaned_1 = gemini_c(sample_text)
    assert "1.." not in cleaned_1
    assert "Trăm năm trong cõi người ta" in cleaned_1
    assert gemini_c.get_stats()["cache_hits"] == 0

    # Lần 2: Phải hit disk cache ngay tức thì
    cleaned_2 = gemini_c(sample_text)
    assert cleaned_2 == cleaned_1
    assert gemini_c.get_stats()["cache_hits"] == 1

    # Thử đăng ký một Cleaner mới động hoàn toàn không chạm file cũ
    @CleanerRegistry.register("my_custom_ai")
    class MyCustomAICleaner(BaseTextPreprocessor):
        def process(self, text: str) -> str:
            return "CUSTOM_AI: " + text.strip()

    custom_c = get_cleaner("my_custom_ai")
    assert custom_c("Hello") == "CUSTOM_AI: Hello"


def test_backward_compatibility():
    # Test remove_line_numbers
    raw = "1.. Trăm năm trong cõi người ta,\n2.. Chữ tài chữ mệnh khéo là ghét nhau.\n"
    cleaned = TextCleaner.remove_line_numbers(raw)
    assert "1.." not in cleaned
    assert "2.." not in cleaned
    assert "Trăm năm trong cõi người ta," in cleaned

    # Test normalize_whitespace
    raw_ws = "  Câu một    nhiều   khoảng trắng   \n\t  Câu hai \t  "
    cleaned_ws = TextCleaner.normalize_whitespace(raw_ws)
    assert cleaned_ws == "Câu một nhiều khoảng trắng\nCâu hai"


def test_unicode_nfc_normalization():
    # Ký tự tiếng Việt dạng NFD (ký tự gốc 'a' + dấu huyền '\u0300')
    nfd_text = "a\u0300"
    assert len(nfd_text) == 2

    # Chuẩn hóa qua TextCleaner
    nfc_text = TextCleaner.normalize_unicode(nfd_text, form="NFC")
    assert len(nfc_text) == 1
    assert nfc_text == "à"
    assert unicodedata.is_normalized("NFC", nfc_text)

    # Test form không hợp lệ
    with pytest.raises(DataPipelineError) as exc_info:
        TextCleaner.normalize_unicode("test", form="INVALID")
    assert "INVALID" in str(exc_info.value)


def test_remove_control_characters():
    # Văn bản chứa zero-width space (\u200b), byte order mark (\ufeff), và ký tự null (\x00)
    raw = "\ufeffXin\u200b chào\x00 thế giới!\nĐây là dòng mới."
    cleaned = TextCleaner.remove_control_characters(raw)
    assert "\ufeff" not in cleaned
    assert "\u200b" not in cleaned
    assert "\x00" not in cleaned
    assert "Xin chào thế giới!\nĐây là dòng mới." == cleaned


def test_strip_html_and_urls():
    raw = "<p>Truy cập <a href='https://example.com/data'>đây</a> hoặc gửi mail test@ai.vn nhé!</p>"
    cleaned = TextCleaner.strip_html_and_urls(
        raw, strip_html=True, strip_urls=True, strip_emails=True
    )
    assert "<p>" not in cleaned
    assert "href" not in cleaned
    assert "https://example.com/data" not in cleaned
    assert "test@ai.vn" not in cleaned
    assert "Truy cập" in cleaned
    assert "nhé!" in cleaned


def test_normalize_punctuation():
    raw = "“Học, học nữa, học mãi”—Lênin… ‘Cố lên’!"
    cleaned = TextCleaner.normalize_punctuation(raw)
    assert cleaned == "\"Học, học nữa, học mãi\"-Lênin... 'Cố lên'!"


def test_full_text_cleaner_process():
    cleaner = TextCleaner(
        clean_line_numbers=True,
        normalize_ws=True,
        normalize_uni=True,
        remove_control_chars=True,
        strip_html=True,
        normalize_punct=True,
    )
    raw = "1.. <div> “Trăm năm trong cõi người ta”\u200b   \n2..  Chữ tài chữ mệnh khéo là ghét nhau.</div>"
    result = cleaner(raw)
    assert "1.." not in result
    assert "2.." not in result
    assert "<div>" not in result
    assert "\u200b" not in result
    assert '"Trăm năm trong cõi người ta"' in result

    # Kiểm tra stats
    stats = cleaner.get_stats()
    assert stats["chars_in"] > 0
    assert stats["chars_out"] > 0
    assert stats["reduction_chars"] > 0


def test_cleaner_invalid_input_type():
    cleaner = TextCleaner()
    with pytest.raises(DataPipelineError) as exc_info:
        cleaner(12345)  # type: ignore
    assert "phải là chuỗi ký tự" in str(exc_info.value)


def test_line_length_filter():
    filter_fn = LineLengthFilter(min_len=5, max_len=40)
    raw = "Ngắn\nDòng này có độ dài rất phù hợp nhé\nDòng này chắc chắn là quá dài so với giới hạn tối đa 40 ký tự của chúng ta rồi"
    filtered = filter_fn(raw)
    lines = filtered.splitlines()
    assert len(lines) == 1
    assert lines[0] == "Dòng này có độ dài rất phù hợp nhé"


def test_deduplication_filter():
    # Consecutive mode
    consec_filter = DeduplicationFilter(mode="consecutive")
    raw = "Dòng 1\nDòng 1\nDòng 2\nDòng 1"
    assert consec_filter(raw) == "Dòng 1\nDòng 2\nDòng 1"

    # Global mode
    global_filter = DeduplicationFilter(mode="global")
    assert global_filter(raw) == "Dòng 1\nDòng 2"


def test_repetition_filter():
    filter_fn = RepetitionFilter(max_consecutive_chars=3)
    raw = "Chúc mừng năm mớiiiii!!!!! Ha ha haaaaaa"
    cleaned = filter_fn(raw)
    assert "mớiiii" not in cleaned
    assert "mớiii" in cleaned
    assert "!!!!" not in cleaned
    assert "!!!" in cleaned
    assert "haaa" in cleaned


def test_preprocessing_pipeline(tmp_path):
    pipeline = TextPreprocessingPipeline()
    pipeline.add_step(TextCleaner(clean_line_numbers=True, normalize_ws=True))
    pipeline.add_step(LineLengthFilter(min_len=5))
    pipeline.add_step(DeduplicationFilter(mode="consecutive"))

    raw = "1.. Hi\n2.. Đoạn văn hợp lệ thứ nhất.\n3.. Đoạn văn hợp lệ thứ nhất.\n4.. Đoạn văn hợp lệ thứ hai."
    result = pipeline(raw)
    lines = result.splitlines()

    assert len(lines) == 2
    assert lines[0] == "Đoạn văn hợp lệ thứ nhất."
    assert lines[1] == "Đoạn văn hợp lệ thứ hai."

    stats = pipeline.get_pipeline_stats()
    assert len(stats["steps"]) == 3
    assert stats["chars_in"] > 0


def test_streaming_file_cleaning(tmp_path):
    input_file = tmp_path / "raw_corpus.txt"
    output_file = tmp_path / "cleaned_corpus.txt"

    lines = [
        "1.. “Trăm năm trong cõi người ta”\n",
        "2.. Chữ tài chữ mệnh khéo là ghét nhau.\n",
        "3.. Trải qua một cuộc bể dâu\n",
    ]
    with open(input_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    cleaner = TextCleaner(clean_line_numbers=True, normalize_punct=True)
    stats = cleaner.clean_file(str(input_file), str(output_file))

    assert output_file.exists()
    assert stats["raw_file_size_bytes"] > stats["cleaned_file_size_bytes"]

    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "1.." not in content
    assert '"Trăm năm trong cõi người ta"' in content

    # Test file không tồn tại
    with pytest.raises(DataPipelineError):
        cleaner.clean_file("non_existent_file.txt", str(output_file))
