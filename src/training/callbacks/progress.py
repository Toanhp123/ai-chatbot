"""
Progress tracking and console logging callbacks.
"""

import time
from typing import Dict

from src.core.logging import get_logger
from src.training.callbacks.base import BaseCallback, TrainerProtocol
from src.utils.tensor_inspector import get_cuda_memory_mb

logger = get_logger("Callbacks")


class ConsoleProgressCallback(BaseCallback):
    """Callback in tiến trình huấn luyện lên console và file log."""

    def __init__(self, log_interval: int = 100) -> None:
        self.log_interval = log_interval
        self.start_time = 0.0

    def on_train_begin(self, trainer: TrainerProtocol) -> None:
        self.start_time = time.time()
        logger.info(f"Bắt đầu huấn luyện mô hình ({trainer.max_iters} bước)...")

    def on_step_end(self, trainer: TrainerProtocol, step: int, loss: float) -> None:
        if step % self.log_interval == 0:
            elapsed = time.time() - self.start_time
            lr = trainer.current_lr
            mem = get_cuda_memory_mb()
            vram_str = f" | VRAM: {mem['allocated_mb']}MB" if mem["allocated_mb"] > 0 else ""
            logger.info(
                f"[Bước {step:4d}/{trainer.max_iters}] Train Loss: {loss:.4f} | LR: {lr:.2e} | Thời gian: {elapsed:.1f}s{vram_str}"
            )

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: Dict[str, float]) -> None:
        elapsed = time.time() - self.start_time
        logger.info(
            f"📊 [ĐÁNH GIÁ Bước {step:4d}] Train Loss: {metrics.get('train_loss', 0.0):.4f} | "
            f"Val Loss: {metrics.get('val_loss', 0.0):.4f} | Thời gian: {elapsed:.1f}s"
        )

    def on_train_end(self, trainer: TrainerProtocol) -> None:
        total_time = time.time() - self.start_time
        logger.info(f" Huấn luyện hoàn thành trong {total_time:.1f}s (~{total_time / 60:.1f} phút)")


__all__ = ["ConsoleProgressCallback"]
