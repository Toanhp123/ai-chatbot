"""
Khối Transformer Block hoàn chỉnh với Pre-LayerNorm/Pre-RMSNorm và Residual Connection.
Bao gồm:
- TransformerBlock: Khối Transformer tiêu chuẩn (GPT-2 style).
- LlamaBlock: Khối Transformer hiện đại (LLaMA style) kết hợp RMSNorm, RoPE và SwiGLU.
"""

from typing import Optional

import torch
import torch.nn as nn

from src.models.layers.attention import CausalSelfAttention, LlamaAttention
from src.models.layers.mlp import FeedForward, SwiGLUFeedForward
from src.models.layers.norm import RMSNorm


class TransformerBlock(nn.Module):
    """Khối Transformer Block tiêu chuẩn với Pre-LayerNorm và Residual Connection."""

    def __init__(
        self,
        n_embd: int,
        n_head: int,
        block_size: int,
        dropout: float = 0.1,
        bias: bool = False,
    ):
        super().__init__()
        self.ln_1 = nn.LayerNorm(n_embd)
        self.attn = CausalSelfAttention(n_embd, n_head, block_size, dropout, bias=bias)
        self.ln_2 = nn.LayerNorm(n_embd)
        self.mlp = FeedForward(n_embd, dropout, bias=bias)

    def reset_kv_cache(self) -> None:
        self.attn.reset_kv_cache()

    def has_active_kv_cache(self) -> bool:
        return self.attn.has_active_kv_cache()

    def forward(self, x: torch.Tensor, use_cache: bool = False) -> torch.Tensor:
        # Pre-LN & Residual Connection
        x = x + self.attn(self.ln_1(x), use_cache=use_cache)
        x = x + self.mlp(self.ln_2(x))
        return x


class LlamaBlock(nn.Module):
    """Khối Transformer Block hiện đại với RMSNorm, RoPE Attention và SwiGLU FeedForward."""

    def __init__(
        self,
        n_embd: int,
        n_head: int,
        dropout: float = 0.0,
        intermediate_size: int = 0,
        multiple_of: int = 64,
        norm_eps: float = 1e-6,
        bias: bool = False,
    ):
        super().__init__()
        self.attn_norm = RMSNorm(n_embd, eps=norm_eps)
        self.attn = LlamaAttention(n_embd, n_head, dropout=dropout, bias=bias)
        self.ffn_norm = RMSNorm(n_embd, eps=norm_eps)
        self.mlp = SwiGLUFeedForward(
            n_embd,
            intermediate_size=intermediate_size,
            multiple_of=multiple_of,
            dropout=dropout,
            bias=bias,
        )

    def reset_kv_cache(self) -> None:
        self.attn.reset_kv_cache()

    def has_active_kv_cache(self) -> bool:
        return self.attn.has_active_kv_cache()

    def forward(
        self,
        x: torch.Tensor,
        rotary_cos: Optional[torch.Tensor] = None,
        rotary_sin: Optional[torch.Tensor] = None,
        use_cache: bool = False,
    ) -> torch.Tensor:
        # Pre-RMSNorm & Residual
        x = x + self.attn(
            self.attn_norm(x),
            rotary_cos=rotary_cos,
            rotary_sin=rotary_sin,
            use_cache=use_cache,
        )
        x = x + self.mlp(self.ffn_norm(x))
        return x


__all__ = ["TransformerBlock", "LlamaBlock"]
