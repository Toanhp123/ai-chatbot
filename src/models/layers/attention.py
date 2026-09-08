"""
Cơ chế Causal Multi-Head Self-Attention với hỗ trợ FlashAttention và Key-Value Cache.
Bao gồm:
- CausalSelfAttention: Multi-Head Attention tiêu chuẩn (GPT-style) hỗ trợ KV-Cache.
- LlamaAttention: Multi-Head Attention hiện đại (LLaMA-style) tích hợp RoPE và KV-Cache.
"""

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.core.exceptions import ModelArchitectureError
from src.models.layers.rotary import apply_rotary_emb


def _offset_causal_mask(query_len: int, key_len: int, device: torch.device) -> torch.Tensor:
    """Return a mask where query i can attend through its absolute cache position."""
    past_len = key_len - query_len
    query_positions = torch.arange(query_len, device=device).unsqueeze(1) + past_len
    key_positions = torch.arange(key_len, device=device).unsqueeze(0)
    return key_positions <= query_positions


class CausalSelfAttention(nn.Module):
    """Cơ chế Causal Self-Attention tiêu chuẩn với hỗ trợ KV-Cache."""

    bias: torch.Tensor

    def __init__(
        self,
        n_embd: int,
        n_head: int,
        block_size: int,
        dropout: float = 0.1,
        bias: bool = False,
    ):
        super().__init__()
        if n_embd % n_head != 0:
            raise ModelArchitectureError(
                f"n_embd ({n_embd}) phải chia hết cho n_head ({n_head})",
                {"n_embd": n_embd, "n_head": n_head},
            )

        self.n_head = n_head
        self.n_embd = n_embd
        self.head_dim = n_embd // n_head
        self.dropout = dropout

        # Chiếu đồng thời Query, Key, Value
        self.c_attn = nn.Linear(n_embd, 3 * n_embd, bias=bias)
        self.c_proj = nn.Linear(n_embd, n_embd, bias=bias)
        self.attn_dropout = nn.Dropout(dropout)
        self.resid_dropout = nn.Dropout(dropout)

        # Causal Mask (tam giác dưới)
        self.register_buffer(
            "bias",
            torch.tril(torch.ones(block_size, block_size)).view(1, 1, block_size, block_size),
            persistent=False,
        )

        # Bộ nhớ đệm Key-Value Cache
        self._k_cache: Optional[torch.Tensor] = None
        self._v_cache: Optional[torch.Tensor] = None

    def reset_kv_cache(self) -> None:
        """Xóa sạch bộ nhớ đệm KV."""
        self._k_cache = None
        self._v_cache = None

    def has_active_kv_cache(self) -> bool:
        """Kiểm tra trạng thái bộ nhớ đệm KV."""
        return self._k_cache is not None and self._v_cache is not None

    def forward(self, x: torch.Tensor, use_cache: bool = False) -> torch.Tensor:
        B, T, C = x.size()

        # Tính Q, K, V
        q, k, v = self.c_attn(x).split(self.n_embd, dim=2)

        # Tách n_head: (B, n_head, T, head_dim)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        had_cache = False
        if use_cache:
            if self._k_cache is not None and self._v_cache is not None:
                had_cache = True
                # Đã có cache: nối key/value mới vào đuôi cache. Query của một
                # chunk mới vẫn phải causal bên trong chính chunk đó.
                k = torch.cat([self._k_cache, k], dim=2)
                v = torch.cat([self._v_cache, v], dim=2)

            self._k_cache = k
            self._v_cache = v

        total_k_len = k.size(2)
        attn_mask = None
        use_builtin_causal = T > 1 and not had_cache
        if had_cache and T > 1:
            attn_mask = _offset_causal_mask(T, total_k_len, x.device).view(1, 1, T, total_k_len)

        # FlashAttention (PyTorch 2.x) tự động chọn nhân tối ưu nhất
        if hasattr(F, "scaled_dot_product_attention"):
            y = F.scaled_dot_product_attention(
                q,
                k,
                v,
                attn_mask=attn_mask,
                dropout_p=self.dropout if self.training else 0.0,
                is_causal=use_builtin_causal,
            )
        else:
            att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
            if use_builtin_causal:
                att = att.masked_fill(self.bias[:, :, :T, :total_k_len] == 0, float("-inf"))
            elif attn_mask is not None:
                att = att.masked_fill(~attn_mask, float("-inf"))
            att = F.softmax(att, dim=-1)
            att = self.attn_dropout(att)
            y = att @ v

        # Ghép các heads: (B, T, C)
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.resid_dropout(self.c_proj(y))


class LlamaAttention(nn.Module):
    """Cơ chế Multi-Head Attention phong cách LLaMA với Rotary Embeddings và KV-Cache."""

    def __init__(
        self,
        n_embd: int,
        n_head: int,
        dropout: float = 0.0,
        bias: bool = False,
    ):
        super().__init__()
        if n_embd % n_head != 0:
            raise ModelArchitectureError(
                f"n_embd ({n_embd}) phải chia hết cho n_head ({n_head})",
                {"n_embd": n_embd, "n_head": n_head},
            )

        self.n_head = n_head
        self.n_embd = n_embd
        self.head_dim = n_embd // n_head
        self.dropout = dropout

        self.q_proj = nn.Linear(n_embd, n_embd, bias=bias)
        self.k_proj = nn.Linear(n_embd, n_embd, bias=bias)
        self.v_proj = nn.Linear(n_embd, n_embd, bias=bias)
        self.o_proj = nn.Linear(n_embd, n_embd, bias=bias)
        self.resid_dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

        self._k_cache: Optional[torch.Tensor] = None
        self._v_cache: Optional[torch.Tensor] = None

    def reset_kv_cache(self) -> None:
        self._k_cache = None
        self._v_cache = None

    def has_active_kv_cache(self) -> bool:
        return self._k_cache is not None and self._v_cache is not None

    def forward(
        self,
        x: torch.Tensor,
        rotary_cos: Optional[torch.Tensor] = None,
        rotary_sin: Optional[torch.Tensor] = None,
        use_cache: bool = False,
    ) -> torch.Tensor:
        B, T, C = x.size()

        q = self.q_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        # Áp dụng Rotary Positional Embedding nếu được truyền
        if rotary_cos is not None and rotary_sin is not None:
            q = apply_rotary_emb(q, rotary_cos, rotary_sin)
            k = apply_rotary_emb(k, rotary_cos, rotary_sin)

        had_cache = False
        if use_cache:
            if self._k_cache is not None and self._v_cache is not None:
                had_cache = True
                k = torch.cat([self._k_cache, k], dim=2)
                v = torch.cat([self._v_cache, v], dim=2)

            self._k_cache = k
            self._v_cache = v

        total_k_len = k.size(2)
        attn_mask = None
        use_builtin_causal = T > 1 and not had_cache
        if had_cache and T > 1:
            attn_mask = _offset_causal_mask(T, total_k_len, x.device).view(1, 1, T, total_k_len)

        if hasattr(F, "scaled_dot_product_attention"):
            y = F.scaled_dot_product_attention(
                q,
                k,
                v,
                attn_mask=attn_mask,
                dropout_p=self.dropout if self.training else 0.0,
                is_causal=use_builtin_causal,
            )
        else:
            att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
            if use_builtin_causal:
                causal_mask = torch.tril(torch.ones((T, total_k_len), device=x.device)).view(
                    1, 1, T, total_k_len
                )
                att = att.masked_fill(causal_mask == 0, float("-inf"))
            elif attn_mask is not None:
                att = att.masked_fill(~attn_mask, float("-inf"))
            att = F.softmax(att, dim=-1)
            y = att @ v

        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.resid_dropout(self.o_proj(y))


__all__ = ["CausalSelfAttention", "LlamaAttention"]
