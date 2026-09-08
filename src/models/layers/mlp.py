"""
Mạng nơ-ron truyền thẳng (FeedForward MLP) chuẩn Transformer với hàm kích hoạt GELU.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FeedForward(nn.Module):
    """Mạng MLP truyền thẳng cổ điển với kích hoạt GELU."""

    def __init__(self, n_embd: int, dropout: float = 0.1, bias: bool = False):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd, bias=bias),
            nn.GELU(),
            nn.Linear(4 * n_embd, n_embd, bias=bias),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class SwiGLUFeedForward(nn.Module):
    """Mạng Gated FeedForward với kích hoạt SwiGLU chuẩn LLaMA."""

    def __init__(
        self,
        n_embd: int,
        intermediate_size: int = 0,
        multiple_of: int = 64,
        dropout: float = 0.0,
        bias: bool = False,
    ) -> None:
        super().__init__()
        if intermediate_size <= 0:
            hidden = int(2 * 4 * n_embd / 3)
            intermediate_size = multiple_of * ((hidden + multiple_of - 1) // multiple_of)

        self.w1 = nn.Linear(n_embd, intermediate_size, bias=bias)
        self.w2 = nn.Linear(intermediate_size, n_embd, bias=bias)
        self.w3 = nn.Linear(n_embd, intermediate_size, bias=bias)
        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # SwiGLU: w2(SiLU(w1(x)) * w3(x))
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))


__all__ = ["FeedForward", "SwiGLUFeedForward"]
