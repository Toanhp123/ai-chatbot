"""
Kiến trúc LlamaNano: Transformer hiện đại lấy cảm hứng từ LLaMA / Mistral.
Sử dụng Rotary Position Embeddings (RoPE), RMSNorm, và SwiGLU FeedForward.
Hỗ trợ Key-Value Cache tối ưu suy luận tự hồi quy và tuân thủ hợp đồng BaseModel.
"""

from typing import Any, Dict, Optional, Tuple, cast

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

from src.core.config import ModelConfig
from src.core.exceptions import ContextLengthExceededError
from src.models.base import BaseModel
from src.models.layers.block import LlamaBlock
from src.models.layers.norm import RMSNorm
from src.models.layers.rotary import RotaryEmbedding
from src.models.registry import ModelRegistry


@ModelRegistry.register("llama", "llama_nano")
class LlamaNano(BaseModel):
    """Kiến trúc mô hình LLaMA thu nhỏ (RoPE + RMSNorm + SwiGLU + KV-Cache)."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self._block_size = config.block_size
        self._vocab_size = config.vocab_size

        # Trích xuất các siêu tham số tùy biến từ model_kwargs
        kwargs: Dict[str, Any] = config.model_kwargs
        rope_theta = float(kwargs.get("rope_theta", 10000.0))
        norm_eps = float(kwargs.get("norm_eps", 1e-6))
        intermediate_size = int(kwargs.get("intermediate_size", 0))
        multiple_of = int(kwargs.get("multiple_of", 64))

        head_dim = config.n_embd // config.n_head

        # Token Embeddings (Không cần Positional Embedding WPE nhờ RoPE)
        self.tok_embeddings = nn.Embedding(config.vocab_size, config.n_embd)
        self.drop = nn.Dropout(config.dropout) if config.dropout > 0.0 else nn.Identity()

        # Rotary Positional Embedding Generator
        self.rotary_emb = RotaryEmbedding(
            dim=head_dim,
            max_seq_len=config.block_size,
            theta=rope_theta,
        )

        # Transformer Blocks
        self.blocks = nn.ModuleList(
            [
                LlamaBlock(
                    n_embd=config.n_embd,
                    n_head=config.n_head,
                    dropout=config.dropout,
                    intermediate_size=intermediate_size,
                    multiple_of=multiple_of,
                    norm_eps=norm_eps,
                    bias=config.bias,
                )
                for _ in range(config.n_layer)
            ]
        )

        # Final RMSNorm
        self.norm = RMSNorm(config.n_embd, eps=norm_eps)

        # Output LM Head
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=config.bias)

        # Weight tying tùy chọn
        if config.tie_word_embeddings:
            self.tok_embeddings.weight = self.lm_head.weight

        self.gradient_checkpointing = False

        self.apply(self._init_weights)

    @property
    def block_size(self) -> int:
        return self._block_size

    @property
    def vocab_size(self) -> int:
        return self._vocab_size

    def set_gradient_checkpointing(self, enabled: bool) -> None:
        """Bật/tắt activation checkpointing cho các LLaMA block khi train."""
        self.gradient_checkpointing = bool(enabled)

    def reset_kv_cache(self) -> None:
        """Xóa sạch bộ nhớ đệm KV trên tất cả các block."""
        for block in self.blocks:
            lb = cast(LlamaBlock, block)
            lb.reset_kv_cache()

    def has_active_kv_cache(self) -> bool:
        """Kiểm tra xem mô hình hiện có đang duy trì KV cache hay không."""
        for block in self.blocks:
            lb = cast(LlamaBlock, block)
            if lb.has_active_kv_cache():
                return True
        return False

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def _embedding_param_count(self) -> int:
        return self.tok_embeddings.weight.numel()

    def forward(
        self,
        idx: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        _, t = idx.size()

        # Tính toán offset khi sử dụng KV-Cache
        offset = 0
        if use_cache and self.has_active_kv_cache():
            first_block = cast(LlamaBlock, self.blocks[0])
            cache_k = first_block.attn._k_cache
            if cache_k is not None:
                offset = cache_k.size(2)

        total_len = offset + t
        if total_len > self.block_size:
            raise ContextLengthExceededError(
                seq_len=total_len,
                max_block_size=self.block_size,
            )

        # Tính toán tần số cos/sin RoPE cho đoạn [offset : offset + t]
        rotary_cos, rotary_sin = self.rotary_emb(idx, seq_len=t, offset=offset)

        x = self.drop(self.tok_embeddings(idx))

        for block in self.blocks:
            lb = cast(LlamaBlock, block)
            if self.gradient_checkpointing and self.training and not use_cache:
                x = checkpoint(
                    lambda hidden, current_block=lb: current_block(
                        hidden,
                        rotary_cos=rotary_cos,
                        rotary_sin=rotary_sin,
                        use_cache=False,
                    ),
                    x,
                    use_reentrant=False,
                )
            else:
                x = lb(
                    x,
                    rotary_cos=rotary_cos,
                    rotary_sin=rotary_sin,
                    use_cache=use_cache,
                )

        x = self.norm(x)

        if targets is not None:
            logits = self.lm_head(x)
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=-1
            )
        else:
            logits = self.lm_head(x[:, [-1], :])
            loss = None

        return logits, loss


__all__ = ["LlamaNano"]
