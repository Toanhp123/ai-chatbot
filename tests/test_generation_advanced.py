"""
Unit tests for advanced generation features:
- Repetition penalty
- Greedy search and Min-P sampling
- Stop tokens and EOS token detection
- TextIteratorStreamer
- GenerationOutput metadata and TPS calculation
"""

from typing import List

import torch
import torch.nn as nn

from src.core.config import GenerationConfig
from src.generation import (
    GenerationOutput,
    TextGenerator,
    TextIteratorStreamer,
    apply_repetition_penalty,
    sample_next_token,
)


class MockTokenizer:
    def __init__(self) -> None:
        self.vocab = {f"c{i}": i for i in range(20)}
        self.inv_vocab = {i: f"c{i}" for i in range(20)}

    def encode(self, text: str) -> List[int]:
        return [0, 1]

    def decode(self, tokens: List[int]) -> str:
        return "".join([self.inv_vocab.get(t, "?") for t in tokens])


class MockModel(nn.Module):
    def __init__(self, vocab_size: int = 20) -> None:
        super().__init__()
        self.block_size = 32
        self.vocab_size = vocab_size

    def forward(self, x: torch.Tensor, use_cache: bool = False):
        batch_size, seq_len = x.shape
        # Tạo logits giả định
        logits = torch.zeros(batch_size, seq_len, self.vocab_size)
        # Token 5 có logit cao nhất
        logits[:, :, 5] = 10.0
        # Token 7 có logit cao nhì
        logits[:, :, 7] = 5.0
        return logits, None


def test_apply_repetition_penalty() -> None:
    """Kiểm tra áp dụng hệ số phạt lặp từ làm giảm điểm số logit của token cũ."""
    logits = torch.tensor([[10.0, -4.0, 5.0]])
    # Phạt token 0 (logit 10.0 > 0) và token 1 (logit -4.0 < 0)
    penalized = apply_repetition_penalty(logits.clone(), generated_tokens=[0, 1], penalty=2.0)

    assert penalized[0, 0].item() == 5.0  # 10.0 / 2.0
    assert penalized[0, 1].item() == -8.0  # -4.0 * 2.0
    assert penalized[0, 2].item() == 5.0  # không bị phạt


def test_sample_next_token_greedy() -> None:
    """Kiểm tra Greedy Search chọn chính xác token có logit cao nhất."""
    logits = torch.tensor([[1.0, 2.0, 15.0, 3.0]])
    # Greedy search với temperature = 0
    token = sample_next_token(logits, temperature=0.0)
    assert int(token.item()) == 2

    # Greedy search với do_sample = False
    token_no_sample = sample_next_token(logits, do_sample=False)
    assert int(token_no_sample.item()) == 2


def test_sample_next_token_min_p() -> None:
    """Kiểm tra Min-P sampling loại bỏ các token có xác suất dưới ngưỡng."""
    # Token 0 cực cao, các token khác rất thấp
    logits = torch.tensor([[10.0, 0.0, -5.0]])
    # Với min_p = 0.5, chỉ token 0 được giữ lại
    token = sample_next_token(logits, temperature=1.0, min_p=0.5)
    assert int(token.item()) == 0


def test_text_iterator_streamer() -> None:
    """Kiểm tra TextIteratorStreamer thu thập và yield từng token."""
    streamer = TextIteratorStreamer()
    streamer.on_prompt("Prompt")
    streamer.on_token("Hello")
    streamer.on_token(" ")
    streamer.on_token("World")
    streamer.on_finish()

    tokens = list(streamer)
    assert tokens == ["Hello", " ", "World"]


def test_text_generator_eos_stopping() -> None:
    """Kiểm tra dừng sớm khi gặp EOS Token."""
    model = MockModel()
    tokenizer = MockTokenizer()
    generator = TextGenerator(model, tokenizer, device="cpu")

    # Đặt token 5 là EOS token (vì mock model luôn sinh token 5)
    config = GenerationConfig(max_new_tokens=10, eos_token_id=5, temperature=0.0)
    output = generator.generate("start", config=config, return_output=True)

    assert isinstance(output, GenerationOutput)
    assert output.finish_reason == "eos_token"
    # Dừng ngay tại bước đầu tiên khi phát hiện EOS token
    assert output.tokens_generated == 0  # Dừng trước khi append token 5


def test_text_generator_stop_tokens() -> None:
    """Kiểm tra dừng sớm khi gặp token trong stop_tokens."""
    model = MockModel()
    tokenizer = MockTokenizer()
    generator = TextGenerator(model, tokenizer, device="cpu")

    config = GenerationConfig(max_new_tokens=10, stop_tokens=[5], temperature=0.0)
    output = generator.generate("start", config=config, return_output=True)

    assert isinstance(output, GenerationOutput)
    assert output.finish_reason == "stop_sequence"


def test_text_generator_output_metadata() -> None:
    """Kiểm tra các trường metadata trong GenerationOutput."""
    model = MockModel()
    tokenizer = MockTokenizer()
    generator = TextGenerator(model, tokenizer, device="cpu")

    config = GenerationConfig(max_new_tokens=5, temperature=0.0)
    output = generator.generate("prompt", config=config, return_output=True)

    assert isinstance(output, GenerationOutput)
    assert output.tokens_generated == 5
    assert output.tokens_per_second > 0
    assert output.elapsed_time_sec >= 0.0
    assert output.finish_reason == "length"
    assert str(output) == output.text


def test_generator_registry_and_factory() -> None:
    """Kiểm tra GeneratorRegistry đăng ký và khởi tạo qua factory get_generator."""
    from src.core.exceptions import AIEngineError
    from src.generation import GeneratorRegistry, LocalTextGenerator, get_generator

    # 1. Kiểm tra các bí danh mặc định
    generators = GeneratorRegistry.list_generators()
    assert "local" in generators
    assert "pytorch" in generators
    assert "default" in generators

    model = MockModel()
    tokenizer = MockTokenizer()

    # 2. Khởi tạo qua GeneratorRegistry.create
    gen1 = GeneratorRegistry.create("local", model, tokenizer, device="cpu")
    assert isinstance(gen1, LocalTextGenerator)

    # 3. Khởi tạo qua get_generator helper
    gen2 = get_generator("default", model, tokenizer, device="cpu")
    assert isinstance(gen2, LocalTextGenerator)

    # 4. Kiểm tra ném lỗi khi backend không tồn tại
    import pytest

    with pytest.raises(AIEngineError, match="Không tìm thấy Generator"):
        GeneratorRegistry.get("non_existent_engine")


def test_text_generator_stops_on_full_multi_token_sequence_without_emitting_it() -> None:
    class SequenceModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.block_size = 16
            self._next = [2, 3, 4]
            self._index = 0

        def forward(self, x: torch.Tensor, use_cache: bool = False):
            logits = torch.full((x.size(0), x.size(1), 8), -100.0)
            token = self._next[min(self._index, len(self._next) - 1)]
            self._index += 1
            logits[:, -1, token] = 100.0
            return logits, None

    class SequenceTokenizer:
        def encode(self, text: str) -> List[int]:
            return [0]

        def decode(self, tokens: List[int]) -> str:
            return "".join({2: "a", 3: "b", 4: "c"}.get(t, "") for t in tokens)

    streamer = TextIteratorStreamer()
    generator = TextGenerator(SequenceModel(), SequenceTokenizer(), device="cpu")
    config = GenerationConfig(
        max_new_tokens=3,
        temperature=0.0,
        stop_sequences=[[2, 3]],
    )

    output = generator.generate("P", config=config, streamer=streamer, return_output=True)

    assert output.finish_reason == "stop_sequence"
    assert output.generated_text == ""
    assert output.token_ids == []
    assert list(streamer) == []


def test_text_generator_incrementally_decodes_multibyte_utf8() -> None:
    from src.data.tokenizers import ByteTokenizer

    class ByteSequenceModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.block_size = 16
            self._next = [196, 131]  # UTF-8 bytes for "ă"
            self._index = 0

        def forward(self, x: torch.Tensor, use_cache: bool = False):
            logits = torch.full((x.size(0), x.size(1), 260), -100.0)
            token = self._next[min(self._index, 1)]
            self._index += 1
            logits[:, -1, token] = 100.0
            return logits, None

    streamer = TextIteratorStreamer()
    generator = TextGenerator(ByteSequenceModel(), ByteTokenizer(), device="cpu")
    output = generator.generate(
        "x",
        config=GenerationConfig(max_new_tokens=2, temperature=0.0),
        streamer=streamer,
        return_output=True,
    )

    assert output.generated_text == "ă"
    assert "".join(list(streamer)) == "ă"


def test_text_generator_restores_model_training_mode_after_generation() -> None:
    model = MockModel()
    model.train()
    generator = TextGenerator(model, MockTokenizer(), device="cpu")
    # Constructor switches to eval for standalone inference; simulate Trainer owning the same model.
    model.train()

    generator.generate("start", config=GenerationConfig(max_new_tokens=1, temperature=0.0))

    assert model.training is True


def test_internal_model_type_error_is_not_retried_without_use_cache() -> None:
    class BrokenModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.block_size = 8
            self.calls = 0

        def forward(self, x: torch.Tensor, use_cache: bool = False):
            self.calls += 1
            raise TypeError("internal bug")

    model = BrokenModel()
    generator = TextGenerator(model, MockTokenizer(), device="cpu")

    import pytest

    with pytest.raises(TypeError, match="internal bug"):
        generator.generate("x", config=GenerationConfig(max_new_tokens=1, use_cache=True))

    assert model.calls == 1
