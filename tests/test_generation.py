import torch

from src.core.config import GenerationConfig, ModelConfig
from src.data.tokenizers.char import CharTokenizer
from src.generation.generator import TextGenerator
from src.models.architectures.llama import LlamaNano
from src.models.architectures.minigpt import MiniGPT


def test_generator_with_and_without_kv_cache():
    # Chuẩn bị tokenizer ký tự
    text = "abcdefghijklmnopqrstuvwxyz "
    tokenizer = CharTokenizer(text)

    # 1. Kiểm tra với MiniGPT
    cfg_mini = ModelConfig(
        name="minigpt",
        vocab_size=tokenizer.vocab_size,
        block_size=64,
        n_embd=32,
        n_head=2,
        n_layer=2,
    )
    model_mini = MiniGPT(cfg_mini)
    gen_mini = TextGenerator(model_mini, tokenizer, device="cpu")

    # Sinh với cache
    out_cached = gen_mini.generate("abc", config=GenerationConfig(max_new_tokens=5, use_cache=True))
    assert len(out_cached) == len("abc") + 5
    assert out_cached.startswith("abc")

    # Sinh không cache
    out_nocache = gen_mini.generate(
        "abc", config=GenerationConfig(max_new_tokens=5, use_cache=False)
    )
    assert len(out_nocache) == len("abc") + 5
    assert out_nocache.startswith("abc")

    # 2. Kiểm tra với LlamaNano
    cfg_llama = ModelConfig(
        name="llama",
        vocab_size=tokenizer.vocab_size,
        block_size=64,
        n_embd=32,
        n_head=2,
        n_layer=2,
    )
    model_llama = LlamaNano(cfg_llama)
    gen_llama = TextGenerator(model_llama, tokenizer, device="cpu")

    out_llama_cached = gen_llama.generate(
        "hello", config=GenerationConfig(max_new_tokens=10, use_cache=True)
    )
    assert len(out_llama_cached) == len("hello") + 10
    assert out_llama_cached.startswith("hello")


def test_text_generator_default_device_is_portable_auto(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    mps = getattr(torch.backends, "mps", None)
    if mps is not None:
        monkeypatch.setattr(mps, "is_available", lambda: False)

    tokenizer = CharTokenizer("abc ")
    cfg = ModelConfig(
        name="minigpt",
        vocab_size=tokenizer.vocab_size,
        block_size=8,
        n_embd=8,
        n_head=2,
        n_layer=1,
    )
    generator = TextGenerator(MiniGPT(cfg), tokenizer)

    assert generator.device == "cpu"
