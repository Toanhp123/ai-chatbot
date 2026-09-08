"""
Cơ chế mã hóa vị trí dạng quay Rotary Position Embedding (RoPE) chuẩn LLaMA / Mistral.
"""

from typing import Tuple

import torch
import torch.nn as nn


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    """Xoay nửa vector để áp dụng ma trận quay 2D: [-x2, x1]."""
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)


def apply_rotary_emb(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Áp dụng phép quay RoPE lên tensor Query hoặc Key.

    Args:
        x: Tensor đầu vào có kích thước (B, n_head, T, head_dim).
        cos: Tensor cos có kích thước (1, 1, T, head_dim) hoặc broadcastable.
        sin: Tensor sin có kích thước (1, 1, T, head_dim) hoặc broadcastable.

    Returns:
        Tensor sau khi quay cùng kích thước với x.
    """
    return (x * cos) + (rotate_half(x) * sin)


class RotaryEmbedding(nn.Module):
    """Lớp quản lý và tính toán bảng tần số RoPE cho Transformer."""

    cos_cached: torch.Tensor
    sin_cached: torch.Tensor

    def __init__(
        self,
        dim: int,
        max_seq_len: int = 2048,
        theta: float = 10000.0,
    ) -> None:
        super().__init__()
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.theta = theta

        # Tính tần số góc
        inv_freq = 1.0 / (self.theta ** (torch.arange(0, self.dim, 2).float() / self.dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

        # Khởi tạo sẵn bảng cos/sin
        self._init_cache(max_seq_len)

    def _init_cache(self, seq_len: int) -> None:
        t = torch.arange(seq_len, dtype=torch.float32)
        cast_inv_freq = getattr(self, "inv_freq", None)
        if cast_inv_freq is None:
            cast_inv_freq = 1.0 / (self.theta ** (torch.arange(0, self.dim, 2).float() / self.dim))
        freqs = torch.outer(t, cast_inv_freq)
        # Ghép đôi để khớp với head_dim: [freqs, freqs]
        emb = torch.cat((freqs, freqs), dim=-1)
        self.register_buffer("cos_cached", emb.cos()[None, None, :, :], persistent=False)
        self.register_buffer("sin_cached", emb.sin()[None, None, :, :], persistent=False)

    def forward(
        self, x: torch.Tensor, seq_len: int, offset: int = 0
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Lấy tensor (cos, sin) tương ứng với đoạn sequence [offset : offset + seq_len]."""
        end_idx = offset + seq_len
        if end_idx > self.cos_cached.size(2):
            # Mở rộng bộ nhớ đệm nếu sequence length vượt quá kích thước hiện tại
            self._init_cache(max(end_idx, self.max_seq_len * 2))

        device = x.device
        dtype = x.dtype
        cos = self.cos_cached[:, :, offset:end_idx, :].to(device=device, dtype=dtype)
        sin = self.sin_cached[:, :, offset:end_idx, :].to(device=device, dtype=dtype)
        return cos, sin


__all__ = ["RotaryEmbedding", "apply_rotary_emb", "rotate_half"]
