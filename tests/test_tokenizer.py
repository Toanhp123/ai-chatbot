import json
import os

import pytest
import torch

from src.core.exceptions import DataPipelineError, VocabularyMissingError
from src.data.cleaners import TextCleaner
from src.data.tokenizers import (
    BaseTokenizer,
    ByteTokenizer,
    CharTokenizer,
    get_tokenizer,
)


def test_char_tokenizer_encode_decode():
    sample = "Trăm năm trong cõi người ta, chữ tài chữ mệnh khéo là ghét nhau."
    tokenizer = CharTokenizer(text=sample)
    tokens = tokenizer.encode(sample)
    assert len(tokens) == len(sample)
    decoded = tokenizer.decode(tokens)
    assert decoded == sample


def test_tokenizer_save_load(tmp_path):
    sample = "Thúy Kiều là chị em là Thúy Vân"
    tokenizer = CharTokenizer(text=sample)
    save_file = str(tmp_path / "vocab_test.json")
    tokenizer.save_vocab(save_file)

    loaded_tokenizer = CharTokenizer.load_vocab(save_file)
    assert loaded_tokenizer.vocab_size == tokenizer.vocab_size
    assert loaded_tokenizer.decode(loaded_tokenizer.encode(sample)) == sample


def test_text_cleaner_line_numbers():
    raw_lines = "1..Trăm năm trong cõi người ta,\n10.. Bốn phương phẳng lặng\n36 Xuân xanh sấp xỉ"
    cleaned = TextCleaner.remove_line_numbers(raw_lines)
    assert "1.." not in cleaned
    assert "10.." not in cleaned
    assert "36 " not in cleaned
    assert "Trăm năm trong cõi người ta," in cleaned


def test_tokenizer_hierarchy():
    char_tok = CharTokenizer(text="abcdef")
    byte_tok = ByteTokenizer()

    assert isinstance(char_tok, BaseTokenizer)
    assert isinstance(byte_tok, BaseTokenizer)


def test_batch_encode_decode():
    texts = ["Xin chào", "Học AI", "MiniGPT"]
    tokenizer = CharTokenizer(text="".join(texts))

    batch_ids = tokenizer.batch_encode(texts)
    assert len(batch_ids) == len(texts)

    decoded = tokenizer.batch_decode(batch_ids)
    assert decoded == texts


def test_encode_batch_tensors_with_padding():
    texts = ["Xin", "Học máy chuyên sâu"]
    tokenizer = CharTokenizer(text="".join(texts), add_special_tokens=True)

    out = tokenizer.encode_batch_tensors(texts, max_length=20, padding=True)
    input_ids = out["input_ids"]
    attention_mask = out["attention_mask"]

    assert isinstance(input_ids, torch.Tensor)
    assert isinstance(attention_mask, torch.Tensor)
    assert input_ids.shape == (2, 20)
    assert attention_mask.shape == (2, 20)

    assert attention_mask[0, 0] == 1
    assert attention_mask[0, -1] == 0


def test_char_tokenizer_special_tokens_and_oov():
    tokenizer = CharTokenizer(text="abc", add_special_tokens=True)
    assert tokenizer.pad_token == "<pad>"
    assert tokenizer.unk_token == "<unk>"
    assert tokenizer.bos_token == "<bos>"
    assert tokenizer.eos_token == "<eos>"

    encoded = tokenizer.encode("abcz")
    assert encoded[-1] == tokenizer.unk_token_id

    legacy_tok = CharTokenizer(text="abc", add_special_tokens=False)
    assert legacy_tok.pad_token_id is None
    assert legacy_tok.encode("abcz") == legacy_tok.encode("abc")


def test_byte_tokenizer():
    byte_tok = ByteTokenizer()
    assert byte_tok.vocab_size == 260
    assert byte_tok.pad_token_id == 256
    assert byte_tok.unk_token_id == 257
    assert byte_tok.bos_token_id == 258
    assert byte_tok.eos_token_id == 259

    sample = "Trăm năm trong cõi người ta! 🚀 🤖 Học AI cực kỳ thú vị."
    encoded = byte_tok.encode(sample)
    assert len(encoded) > 0
    assert all(0 <= b < 256 for b in encoded)

    decoded = byte_tok.decode(encoded)
    assert decoded == sample

    t = byte_tok.encode_as_tensor(sample)
    assert isinstance(t, torch.Tensor)
    assert t.dtype == torch.long
    assert len(t) == len(encoded)


def test_vocabulary_missing_error(tmp_path):
    fake_path = str(tmp_path / "non_existent_vocab.json")
    with pytest.raises(VocabularyMissingError) as exc_info:
        CharTokenizer.load_vocab(fake_path)
    assert "Không tìm thấy file từ điển" in str(exc_info.value)

    with pytest.raises(VocabularyMissingError):
        ByteTokenizer.load_vocab(fake_path)


def test_tokenizer_factory():
    char_tok = get_tokenizer("char", text="Hello world")
    assert isinstance(char_tok, CharTokenizer)

    byte_tok = get_tokenizer("byte")
    assert isinstance(byte_tok, ByteTokenizer)

    with pytest.raises(DataPipelineError) as exc_info:
        get_tokenizer("sentencepiece_unsupported")
    assert "Loại Tokenizer không được hỗ trợ" in str(exc_info.value)


def test_legacy_and_modern_vocab_json_compatibility(tmp_path):
    legacy_file = tmp_path / "legacy_vocab.json"
    with open(legacy_file, "w", encoding="utf-8") as f:
        json.dump(["a", "b", "c", "d"], f)

    tok1 = CharTokenizer.load_vocab(str(legacy_file))
    assert tok1.vocab_size == 4
    assert tok1.encode("abd") == [0, 1, 3]

    modern_file = tmp_path / "modern_vocab.json"
    tok2 = CharTokenizer(text="xyz", add_special_tokens=True)
    tok2.save_vocab(str(modern_file))

    tok3 = CharTokenizer.load_vocab(str(modern_file))
    assert tok3.vocab_size == tok2.vocab_size
    assert tok3.add_special_tokens is True
    assert tok3.pad_token == "<pad>"


def test_tokenizer_registry_and_polymorphic_loading(tmp_path):
    from src.data.tokenizers import (
        GeminiTokenizer,
        TokenizerRegistry,
        load_tokenizer,
    )

    available = TokenizerRegistry.list_available()
    assert "char" in available
    assert "byte" in available
    assert "gemini" in available

    # 1. Test polymorphic load for ByteTokenizer
    byte_tok = ByteTokenizer()
    byte_vocab_file = str(tmp_path / "byte_vocab.json")
    byte_tok.save_vocab(byte_vocab_file)

    loaded_byte = load_tokenizer(byte_vocab_file)
    assert isinstance(loaded_byte, ByteTokenizer)
    assert loaded_byte.vocab_size == byte_tok.vocab_size

    # 2. Test polymorphic load for CharTokenizer
    char_tok = CharTokenizer(text="hello", add_special_tokens=True)
    char_vocab_file = str(tmp_path / "char_vocab.json")
    char_tok.save_vocab(char_vocab_file)

    loaded_char = load_tokenizer(char_vocab_file)
    assert isinstance(loaded_char, CharTokenizer)

    # 3. Test polymorphic load for GeminiTokenizer
    cache_dir = str(tmp_path / "gemini_cache")
    gemini_tok = GeminiTokenizer(cache_dir=cache_dir)
    gemini_vocab_file = str(tmp_path / "gemini_vocab.json")
    gemini_tok.save_vocab(gemini_vocab_file)

    loaded_gemini = load_tokenizer(gemini_vocab_file)
    assert isinstance(loaded_gemini, GeminiTokenizer)


def test_gemini_tokenizer_caching_and_fallback(tmp_path):
    from src.data.tokenizers import GeminiTokenizer

    cache_dir = str(tmp_path / "gemini_tokens_cache")
    tokenizer = GeminiTokenizer(cache_dir=cache_dir)

    sample = "Trăm năm trong cõi người ta"
    tokens1 = tokenizer.encode(sample)
    assert len(tokens1) > 0
    assert tokenizer.decode(tokens1) == sample

    # Kiểm tra file cache SHA-256 được tạo ra
    cache_files = list(os.listdir(cache_dir))
    assert len(cache_files) == 1

    # Lần 2: Đọc từ cache
    tokens2 = tokenizer.encode(sample)
    assert tokens1 == tokens2


def test_custom_tokenizer_registration_plug_and_play():
    from src.data.tokenizers import BaseTokenizer, TokenizerRegistry, get_tokenizer

    @TokenizerRegistry.register("custom_dummy")
    class DummyTokenizer(BaseTokenizer):
        @property
        def vocab_size(self) -> int:
            return 10

        def encode(self, text: str):
            return [0, 1]

        def decode(self, tokens):
            return "dummy"

        def save_vocab(self, filepath: str) -> None:
            pass

    assert "custom_dummy" in TokenizerRegistry.list_available()
    dummy = get_tokenizer("custom_dummy")
    assert isinstance(dummy, DummyTokenizer)
    assert dummy.encode("anything") == [0, 1]


def test_tokenizer_loader_rejects_unknown_metadata_type(tmp_path) -> None:
    from src.data.tokenizers import load_tokenizer

    vocab_file = tmp_path / "vocab.json"
    vocab_file.write_text(
        json.dumps({"version": "2.0", "tokenizer_type": "mystery", "vocab": ["a", "b"]}),
        encoding="utf-8",
    )

    with pytest.raises(DataPipelineError, match="mystery|Tokenizer"):
        load_tokenizer(str(vocab_file))


def test_legacy_gemini_tokenizer_has_same_token_identity_as_byte_tokenizer(tmp_path) -> None:
    from src.data.tokenizers import GeminiTokenizer
    from src.data.tokenizers.base import get_tokenizer_identity

    byte_tokenizer = ByteTokenizer()
    gemini_tokenizer = GeminiTokenizer(
        api_key="unused-secret",
        cache_dir=str(tmp_path / "cache"),
    )

    assert get_tokenizer_identity(gemini_tokenizer) == get_tokenizer_identity(byte_tokenizer)
    assert not hasattr(gemini_tokenizer, "_client")
