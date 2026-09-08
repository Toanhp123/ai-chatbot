from typing import Optional, Tuple

import pytest
import torch

from src.core.config import ModelConfig
from src.core.exceptions import ContextLengthExceededError, ModelNotFoundError
from src.models.architectures.llama import LlamaNano
from src.models.architectures.minigpt import MiniGPT
from src.models.base import BaseModel
from src.models.registry import ModelRegistry


def test_model_registry_and_forward():
    cfg = ModelConfig(
        name="minigpt", vocab_size=50, block_size=32, n_embd=64, n_head=4, n_layer=2, dropout=0.0
    )
    model = ModelRegistry.create("minigpt", cfg)
    assert isinstance(model, MiniGPT)
    assert isinstance(model, BaseModel)
    assert model.block_size == cfg.block_size
    assert model.vocab_size == cfg.vocab_size
    assert isinstance(model.device, torch.device)
    assert isinstance(model.dtype, torch.dtype)
    assert not model.has_active_kv_cache()
    assert model.get_num_params() > 0

    batch_size = 2
    seq_len = 16
    x = torch.randint(0, cfg.vocab_size, (batch_size, seq_len))
    y = torch.randint(0, cfg.vocab_size, (batch_size, seq_len))

    logits, loss = model(x, y)
    assert logits.shape == (batch_size, seq_len, cfg.vocab_size)
    assert loss is not None
    assert not torch.isnan(loss)
    assert not torch.isinf(loss)


def test_base_model_abstract_enforcement():
    class IncompleteModel(BaseModel):
        @property
        def block_size(self) -> int:
            return 32

    with pytest.raises(TypeError):
        IncompleteModel()  # type: ignore


def test_model_registry_multiple_aliases():
    @ModelRegistry.register("alias_model_a", "alias_model_b")
    class DummyModel(BaseModel):
        def __init__(self, config: ModelConfig) -> None:
            super().__init__()
            self._config = config

        @property
        def block_size(self) -> int:
            return 32

        @property
        def vocab_size(self) -> int:
            return 100

        def forward(
            self,
            idx: torch.Tensor,
            targets: Optional[torch.Tensor] = None,
            use_cache: bool = False,
        ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
            return idx, None

    cfg = ModelConfig(name="alias_model_a")
    m1 = ModelRegistry.create("alias_model_a", cfg)
    m2 = ModelRegistry.create("alias_model_b", cfg)
    assert isinstance(m1, DummyModel)
    assert isinstance(m2, DummyModel)


def test_model_registry_auto_discovery_and_error():
    models = ModelRegistry.list_models()
    assert "minigpt" in models
    assert "llama" in models
    assert "llama_nano" in models

    with pytest.raises(ModelNotFoundError) as exc_info:
        ModelRegistry.create("non_existent_arch_xyz", ModelConfig())
    assert "non_existent_arch_xyz" in str(exc_info.value)


def test_llama_nano_architecture_and_forward():
    cfg = ModelConfig(
        name="llama",
        vocab_size=64,
        block_size=32,
        n_embd=64,
        n_head=4,
        n_layer=2,
        dropout=0.0,
        model_kwargs={"rope_theta": 5000.0, "multiple_of": 32, "norm_eps": 1e-5},
    )
    model = ModelRegistry.create("llama", cfg)
    assert isinstance(model, LlamaNano)
    assert isinstance(model, BaseModel)
    assert model.block_size == 32
    assert model.vocab_size == 64

    # Kiểm tra tính toán số lượng tham số
    total_params = model.get_num_params(non_embedding=False)
    non_emb_params = model.get_num_params(non_embedding=True)
    assert total_params > non_emb_params

    # Forward pass
    x = torch.randint(0, cfg.vocab_size, (2, 8))
    y = torch.randint(0, cfg.vocab_size, (2, 8))
    logits, loss = model(x, y)
    assert logits.shape == (2, 8, cfg.vocab_size)
    assert loss is not None
    assert not torch.isnan(loss)


def test_minigpt_kv_cache_accuracy():
    torch.manual_seed(42)
    cfg = ModelConfig(
        name="minigpt", vocab_size=30, block_size=16, n_embd=32, n_head=2, n_layer=2, dropout=0.0
    )
    model = MiniGPT(cfg)
    model.eval()

    prompt = torch.randint(0, cfg.vocab_size, (1, 4))
    token1 = torch.randint(0, cfg.vocab_size, (1, 1))
    token2 = torch.randint(0, cfg.vocab_size, (1, 1))

    # 1. Full inference không cache
    full_seq1 = torch.cat([prompt, token1], dim=1)
    full_seq2 = torch.cat([full_seq1, token2], dim=1)

    logits_full1, _ = model(full_seq1, use_cache=False)
    logits_full2, _ = model(full_seq2, use_cache=False)

    # 2. Cached inference
    model.reset_kv_cache()
    assert not model.has_active_kv_cache()

    # Step 0: prompt
    logits_step0, _ = model(prompt, use_cache=True)
    assert logits_step0.shape == (1, 1, cfg.vocab_size)
    assert model.has_active_kv_cache()

    # Step 1: token 1
    logits_step1, _ = model(token1, use_cache=True)
    assert torch.allclose(logits_step1[:, -1, :], logits_full1[:, -1, :], atol=1e-4)

    # Step 2: token 2
    logits_step2, _ = model(token2, use_cache=True)
    assert torch.allclose(logits_step2[:, -1, :], logits_full2[:, -1, :], atol=1e-4)

    # Reset cache
    model.reset_kv_cache()
    assert not model.has_active_kv_cache()


def test_llama_kv_cache_accuracy():
    torch.manual_seed(42)
    cfg = ModelConfig(
        name="llama", vocab_size=30, block_size=16, n_embd=32, n_head=2, n_layer=2, dropout=0.0
    )
    model = LlamaNano(cfg)
    model.eval()

    prompt = torch.randint(0, cfg.vocab_size, (1, 4))
    token1 = torch.randint(0, cfg.vocab_size, (1, 1))
    token2 = torch.randint(0, cfg.vocab_size, (1, 1))

    # 1. Full inference
    full_seq1 = torch.cat([prompt, token1], dim=1)
    full_seq2 = torch.cat([full_seq1, token2], dim=1)

    logits_full1, _ = model(full_seq1, use_cache=False)
    logits_full2, _ = model(full_seq2, use_cache=False)

    # 2. Cached inference
    model.reset_kv_cache()
    logits_step0, _ = model(prompt, use_cache=True)
    assert logits_step0.shape == (1, 1, cfg.vocab_size)
    assert model.has_active_kv_cache()

    logits_step1, _ = model(token1, use_cache=True)
    assert torch.allclose(logits_step1[:, -1, :], logits_full1[:, -1, :], atol=1e-4)

    logits_step2, _ = model(token2, use_cache=True)
    assert torch.allclose(logits_step2[:, -1, :], logits_full2[:, -1, :], atol=1e-4)

    model.reset_kv_cache()
    assert not model.has_active_kv_cache()


def test_context_length_exceeded_error():
    cfg = ModelConfig(name="minigpt", block_size=8)
    model = MiniGPT(cfg)
    long_input = torch.randint(0, cfg.vocab_size, (1, 10))

    with pytest.raises(ContextLengthExceededError) as exc_info:
        model(long_input)
    assert "Độ dài chuỗi đầu vào (10) vượt quá giới hạn" in str(exc_info.value)
