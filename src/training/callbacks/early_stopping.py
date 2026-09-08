"""
Early stopping callback to prevent overfitting and save resources.
"""

from typing import Dict, cast

from src.core.logging import get_logger
from src.training.callbacks.base import BaseCallback, TrainerProtocol

logger = get_logger("Callbacks")


class EarlyStoppingCallback(BaseCallback):
    """
    Callback dừng sớm quá trình huấn luyện khi chỉ số theo dõi (monitor)
    không còn cải thiện sau một số chu kỳ đánh giá (patience).
    Hỗ trợ cả 2 chế độ:
    - mode="min": Theo dõi chỉ số cần giảm (val_loss, perplexity).
    - mode="max": Theo dõi chỉ số cần tăng (accuracy, f1, bleu).
    """

    def __init__(
        self,
        monitor: str = "val_loss",
        mode: str = "min",
        patience: int = 10,
        min_delta: float = 1e-4,
    ) -> None:
        if patience <= 0:
            raise ValueError(f"patience phải > 0, nhận được {patience}")
        if mode not in ("min", "max"):
            raise ValueError(f"Chế độ mode không hợp lệ: '{mode}'. Chỉ chấp nhận 'min' hoặc 'max'.")

        self.monitor = monitor
        self.mode = mode
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_score = float("inf") if mode == "min" else float("-inf")

    def state_dict(self) -> Dict[str, float | int]:
        return {"counter": self.counter, "best_score": self.best_score}

    def load_state_dict(self, state: Dict[str, object]) -> None:
        self.counter = int(cast(int | str, state.get("counter", 0)))
        self.best_score = float(
            cast(
                float | int | str,
                state.get("best_score", float("inf") if self.mode == "min" else float("-inf")),
            )
        )

    def _is_improvement(self, current: float) -> bool:
        if self.mode == "min":
            return current < (self.best_score - self.min_delta)
        return current > (self.best_score + self.min_delta)

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: Dict[str, float]) -> None:
        if self.monitor not in metrics:
            logger.warning(
                f"[EarlyStopping] Không tìm thấy chỉ số '{self.monitor}' trong metrics: {list(metrics.keys())}"
            )
            return

        current = metrics[self.monitor]
        if self._is_improvement(current):
            self.best_score = current
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                logger.warning(
                    f"🛑 [Early Stopping] Dừng sớm tại bước {step} do chỉ số '{self.monitor}' "
                    f"không cải thiện sau {self.patience} lần đánh giá liên tiếp (Kỷ lục: {self.best_score:.4f})."
                )
                trainer.request_stop()


__all__ = ["EarlyStoppingCallback"]
