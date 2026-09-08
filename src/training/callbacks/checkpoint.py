"""
Model checkpoint persistence callbacks with Top-K and Last checkpoint support.
"""

import os
import tempfile
from typing import Dict, List, Optional, Tuple

import torch

from src.core.logging import get_logger
from src.training.callbacks.base import BaseCallback, TrainerProtocol

logger = get_logger("Callbacks")


def _validate_path_component(value: str, field_name: str) -> str:
    """Validate a value that will be used as a single checkpoint filename component."""
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(
            f"{field_name} phải là một tên an toàn và không được chứa thành phần đường dẫn."
        )
    return value


def _atomic_torch_save(state: Dict[str, object], path: str) -> None:
    """Persist a checkpoint atomically so interrupted writes cannot corrupt the target."""
    target = os.path.abspath(path)
    target_dir = os.path.dirname(target)
    os.makedirs(target_dir, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        dir=target_dir, prefix=f".{os.path.basename(target)}.", suffix=".tmp"
    )
    os.close(fd)
    try:
        torch.save(state, temp_path)
        os.replace(temp_path, target)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


class ModelCheckpointCallback(BaseCallback):
    """
    Callback tự động lưu checkpoint mô hình với hỗ trợ:
    - Lưu mô hình tốt nhất (best_model.pt).
    - Lưu đa checkpoint theo phiên bản Top-K (save_top_k).
    - Lưu checkpoint bước cuối cùng (last_model.pt) phục vụ Resume chính xác.
    - Hỗ trợ định danh phiên huấn luyện (run_name).
    """

    def __init__(
        self,
        save_dir: str = "checkpoints",
        filename: str = "best_model.pt",
        monitor: str = "val_loss",
        mode: str = "min",
        min_delta: float = 0.0,
        save_top_k: int = 1,
        save_last: bool = True,
        run_name: Optional[str] = None,
    ) -> None:
        if mode not in ("min", "max"):
            raise ValueError(f"Chế độ mode không hợp lệ: '{mode}'. Chỉ chấp nhận 'min' hoặc 'max'.")

        self.save_dir = save_dir
        self.filename = _validate_path_component(filename, "filename")
        self.monitor = monitor
        self.mode = mode
        self.min_delta = min_delta
        self.save_top_k = max(0, save_top_k)
        self.save_last = save_last
        self.run_name = (
            _validate_path_component(run_name, "run_name") if run_name else None
        )
        self.best_score = float("inf") if mode == "min" else float("-inf")
        self.filepath = os.path.join(save_dir, self.filename)
        self.last_filepath = os.path.join(
            save_dir,
            f"{self.run_name}_last.pt" if self.run_name else "last_model.pt",
        )
        self.canonical_last_filepath = os.path.join(save_dir, "last_model.pt")
        self.top_k_checkpoints: List[Tuple[float, str]] = []
        self.last_step = 0

    def on_train_begin(self, trainer: TrainerProtocol) -> None:
        os.makedirs(self.save_dir, exist_ok=True)
        # Nạp kỷ lục tốt nhất từ checkpoint canonical hiện có nếu có trên đĩa
        if os.path.exists(self.filepath):
            try:
                state = torch.load(self.filepath, map_location="cpu", weights_only=True)
                if isinstance(state, dict):
                    saved_val = state.get(self.monitor)
                    if saved_val is None:
                        saved_val = state.get("val_loss")
                    if saved_val is not None:
                        val_float = float(saved_val)
                        import math

                        if (
                            not math.isnan(val_float)
                            and not math.isinf(val_float)
                            and val_float > 0
                        ):
                            self.best_score = val_float
                            logger.info(
                                f"🏆 [ModelCheckpoint] Đã nạp kỷ lục tốt nhất toàn cục từ '{self.filename}': "
                                f"{self.monitor}={self.best_score:.4f}"
                            )
            except Exception as e:
                logger.warning(f"[ModelCheckpoint] Không thể đọc kỷ lục từ '{self.filepath}': {e}")

    def on_step_end(self, trainer: TrainerProtocol, step: int, loss: float) -> None:
        self.last_step = step

    def _is_improvement(self, current: float) -> bool:
        if self.mode == "min":
            return current < (self.best_score - self.min_delta)
        return current > (self.best_score + self.min_delta)

    def _save_state(
        self,
        trainer: TrainerProtocol,
        step: int,
        metrics: Dict[str, float],
        path: str,
        is_best: bool = False,
    ) -> None:
        val_loss = metrics.get("val_loss")
        state = {
            "step": step,
            self.monitor: metrics.get(self.monitor),
            "val_loss": val_loss,
            "metrics": metrics,
            "is_best": is_best,
            "run_name": self.run_name,
            "model_state_dict": trainer.get_model_state_dict(),
            "optimizer_state_dict": trainer.get_optimizer_state_dict(),
            "config": trainer.get_config_dict(),
        }
        _atomic_torch_save(state, path)

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: Dict[str, float]) -> None:
        self.last_step = step
        if self.monitor not in metrics:
            logger.warning(
                f"[ModelCheckpoint] Không tìm thấy chỉ số '{self.monitor}' trong metrics: {list(metrics.keys())}"
            )
            return

        current = metrics[self.monitor]

        # 1. Luôn lưu last checkpoint nếu save_last bật (cập nhật cả last_model.pt và session_last.pt)
        if self.save_last:
            self._save_state(trainer, step, metrics, self.last_filepath)
            if self.last_filepath != self.canonical_last_filepath:
                self._save_state(trainer, step, metrics, self.canonical_last_filepath)

        # 2. Kiểm tra có cải thiện kỷ lục hay không
        if self._is_improvement(current):
            old_best = self.best_score
            self.best_score = current

            # A. Lưu canonical best checkpoint
            self._save_state(trainer, step, metrics, self.filepath, is_best=True)
            logger.info(
                f"⭐ [Checkpoint] Kỷ lục mới xuất sắc! ({self.monitor}: {current:.4f} < {old_best:.4f}). Đã cập nhật vào {self.filepath}"
            )

            # B. Lưu versioned checkpoint nếu save_top_k > 0
            if self.save_top_k > 0:
                prefix = self.run_name if self.run_name else "checkpoint"
                versioned_filename = f"{prefix}_step{step}_val{current:.4f}.pt"
                versioned_path = os.path.join(self.save_dir, versioned_filename)
                self._save_state(trainer, step, metrics, versioned_path)

                self.top_k_checkpoints.append((current, versioned_path))
                # Sắp xếp: nếu min thì loss nhỏ đứng đầu; nếu max thì score lớn đứng đầu
                self.top_k_checkpoints.sort(key=lambda x: x[0], reverse=(self.mode == "max"))

                # Dọn dẹp nếu vượt quá save_top_k
                while len(self.top_k_checkpoints) > self.save_top_k:
                    _, worst_path = self.top_k_checkpoints.pop()
                    if (
                        os.path.exists(worst_path)
                        and worst_path != self.filepath
                        and worst_path != self.last_filepath
                        and worst_path != self.canonical_last_filepath
                    ):
                        try:
                            os.remove(worst_path)
                            logger.info(
                                f"🗑️ [Checkpoint] Đã dọn dẹp checkpoint cũ '{os.path.basename(worst_path)}' để duy trì top-{self.save_top_k}."
                            )
                        except OSError as e:
                            logger.warning(f"Không thể xoá checkpoint cũ '{worst_path}': {e}")
        else:
            logger.info(
                f"ℹ️ [Checkpoint] Bước {step} ({self.monitor}: {current:.4f}) chưa vượt qua kỷ lục tốt nhất ({self.best_score:.4f}). Giữ nguyên {self.filename}."
            )

    def on_train_end(self, trainer: TrainerProtocol) -> None:
        """Đảm bảo lưu lại trạng thái bước cuối cùng khi kết thúc toàn bộ phiên huấn luyện."""
        if self.save_last and self.last_step > 0:
            best_val = (
                self.best_score
                if (
                    self.best_score != float("inf")
                    and self.best_score != float("-inf")
                    and self.best_score > 0
                )
                else None
            )
            metrics: Dict[str, float] = {}
            if best_val is not None:
                metrics["val_loss"] = best_val
            try:
                self._save_state(trainer, self.last_step, metrics, self.last_filepath)
                if self.last_filepath != self.canonical_last_filepath:
                    self._save_state(trainer, self.last_step, metrics, self.canonical_last_filepath)
                logger.info(
                    f"💾 [Checkpoint] Đã lưu trạng thái bước cuối cùng (step {self.last_step}) vào {self.last_filepath}"
                )
            except Exception as e:
                logger.warning(f"[ModelCheckpoint] Không thể lưu last checkpoint khi kết thúc: {e}")


__all__ = ["ModelCheckpointCallback"]
