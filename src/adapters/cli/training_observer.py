"""CLI presentation adapter for transport-neutral training observations."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-train")


class ConsoleTrainingObserver:
    def on_step(self, *, step: int, loss: float, lr: float, elapsed: float, emit: bool) -> None:
        if emit:
            logger.info(
                "[Bước %4d] Train Loss: %.4f | LR: %.2e | Thời gian: %.1fs",
                step,
                loss,
                lr,
                elapsed,
            )

    def on_eval(self, *, step: int, train_loss: float, val_loss: float, lr: float) -> None:
        logger.info(
            "📊 [ĐÁNH GIÁ Bước %4d] Train Loss: %.4f | Val Loss: %.4f | LR: %.2e",
            step,
            train_loss,
            val_loss,
            lr,
        )

    def on_sample(self, *, step: int, text: str) -> None:
        # SampleGenerationCallback owns the canonical sample log; avoid duplicate console output.
        del step, text
