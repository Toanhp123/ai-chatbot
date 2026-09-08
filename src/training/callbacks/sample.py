"""
Sample text generation callback for periodic qualitative evaluation during training.
"""

from typing import Callable, Dict, Optional

import torch

from src.core.logging import get_logger
from src.training.callbacks.base import BaseCallback, TrainerProtocol

logger = get_logger("Callbacks")


class SampleGenerationCallback(BaseCallback):
    """
    Callback sinh văn bản thử nghiệm định kỳ tại các chu kỳ đánh giá (eval).

    Thiết kế theo nguyên lý Inversion of Control (IoC):
    Nhận `sample_fn: Callable[[int], str]` được đóng gói từ Composition Root (main.py),
    tách biệt hoàn toàn Tầng Training khỏi chi tiết triển khai của Tầng Generation và Data Tokenizer.
    """

    def __init__(
        self,
        sample_fn: Optional[Callable[[int], str]] = None,
        prompt: str = "Trăm năm",
        max_tokens: int = 100,
    ) -> None:
        self.sample_fn = sample_fn
        self.prompt = prompt
        self.max_tokens = max_tokens

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: Dict[str, float]) -> None:
        # Trường hợp 1 (Chuẩn Enterprise): Đã được inject sample_fn từ bên ngoài
        if self.sample_fn is not None:
            try:
                gen_text = self.sample_fn(step)
                logger.info(f"📖 [AI Sáng Tác Thử - Bước {step}]:\n{gen_text}\n" + "-" * 50)
            except Exception as e:
                logger.warning(f"[SampleGeneration] Lỗi khi sinh văn bản mẫu tại bước {step}: {e}")
            return

        # Trường hợp 2: Fallback tương thích ngược nếu trainer sở hữu model & tokenizer
        tokenizer = getattr(trainer, "tokenizer", None)
        model = getattr(trainer, "model", None)
        if tokenizer is None or model is None:
            return

        device = getattr(trainer, "device", "cpu")

        model.eval()
        tokens = tokenizer.encode(self.prompt)
        idx = torch.tensor([tokens], dtype=torch.long, device=device)
        out_tokens = list(tokens)

        with torch.no_grad():
            for _ in range(self.max_tokens):
                block_size = getattr(model, "block_size", 128)
                idx_cond = idx if idx.size(1) <= block_size else idx[:, -block_size:]
                logits, _ = model(idx_cond)
                next_tok = torch.argmax(logits[:, -1, :], dim=-1)
                idx = torch.cat((idx, next_tok.unsqueeze(0)), dim=1)
                out_tokens.append(int(next_tok.item()))

        gen_text = tokenizer.decode(out_tokens)
        model.train()
        logger.info(f"📖 [AI Sáng Tác Thử - Bước {step}]:\n{gen_text}\n" + "-" * 50)


__all__ = ["SampleGenerationCallback"]
