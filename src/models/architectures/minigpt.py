"""
Kiến trúc Mini-GPT: Decoder-only Autoregressive Transformer chuẩn PyTorch nn.Module.
Hỗ trợ Key-Value Cache tối ưu suy luận tự hồi quy và tuân thủ hợp đồng BaseModel.
"""

from typing import Optional, Tuple, cast

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

from src.core.config import ModelConfig
from src.core.exceptions import ContextLengthExceededError
from src.models.base import BaseModel
from src.models.layers.block import TransformerBlock
from src.models.registry import ModelRegistry


@ModelRegistry.register("minigpt")
class MiniGPT(BaseModel):
    """Mô hình ngôn ngữ tự hồi quy MiniGPT kế thừa chuẩn BaseModel."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self._block_size = config.block_size
        self._vocab_size = config.vocab_size

        # Embeddings
        self.wte = nn.Embedding(config.vocab_size, config.n_embd)
        self.wpe = nn.Embedding(config.block_size, config.n_embd)
        self.drop = nn.Dropout(config.dropout)

        # Transformer Blocks
        self.blocks = nn.ModuleList(
            [
                TransformerBlock(
                    config.n_embd,
                    config.n_head,
                    config.block_size,
                    config.dropout,
                    bias=config.bias,
                )
                for _ in range(config.n_layer)
            ]
        )
        self.ln_f = nn.LayerNorm(config.n_embd)

        # Output LM Head
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=config.bias)

        # Weight tying (chia sẻ trọng số giữa embedding và head)
        if config.tie_word_embeddings:
            self.wte.weight = self.lm_head.weight

        self.gradient_checkpointing = False

        # Khởi tạo trọng số chuẩn
        self.apply(self._init_weights)

    @property
    def block_size(self) -> int:
        return self._block_size

    @property
    def vocab_size(self) -> int:
        return self._vocab_size

    @property
    def device(self) -> torch.device:
        return next(self.parameters()).device

    @property
    def dtype(self) -> torch.dtype:
        return next(self.parameters()).dtype

    def set_gradient_checkpointing(self, enabled: bool) -> None:
        """Bật/tắt activation checkpointing cho các transformer block khi train."""
        self.gradient_checkpointing = bool(enabled)

    def reset_kv_cache(self) -> None:
        """Xóa trạng thái cache Key-Value trên tất cả các transformer blocks."""
        for block in self.blocks:
            tb = cast(TransformerBlock, block)
            tb.reset_kv_cache()

    def has_active_kv_cache(self) -> bool:
        """Kiểm tra xem mô hình hiện có block nào đang duy trì KV-cache hay không."""
        for block in self.blocks:
            tb = cast(TransformerBlock, block)
            if tb.has_active_kv_cache():
                return True
        return False

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def get_num_params(self, non_embedding: bool = False) -> int:
        n_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if non_embedding and hasattr(self, "wpe"):
            n_params -= self.wpe.weight.numel()
        return n_params

    def forward(
        self,
        idx: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        device = idx.device
        _, t = idx.size()

        # Xác định offset vị trí khi dùng KV Cache
        offset = 0
        if use_cache and self.has_active_kv_cache():
            first_block = cast(TransformerBlock, self.blocks[0])
            cache_k = first_block.attn._k_cache
            if cache_k is not None:
                offset = cache_k.size(2)

        total_len = offset + t
        if total_len > self.block_size:
            raise ContextLengthExceededError(
                seq_len=total_len,
                max_block_size=self.block_size,
            )

        pos = torch.arange(offset, total_len, dtype=torch.long, device=device)

        tok_emb = self.wte(idx)
        pos_emb = self.wpe(pos)
        x = self.drop(tok_emb + pos_emb)

        for block in self.blocks:
            tb = cast(TransformerBlock, block)
            if self.gradient_checkpointing and self.training and not use_cache:
                x = checkpoint(
                    lambda hidden, current_block=tb: current_block(hidden, use_cache=False),
                    x,
                    use_reentrant=False,
                )
            else:
                x = tb(x, use_cache=use_cache)
        x = self.ln_f(x)

        if targets is not None:
            logits = self.lm_head(x)
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=-1
            )
        else:
            logits = self.lm_head(x[:, [-1], :])
            loss = None

        return logits, loss


__all__ = ["MiniGPT"]
