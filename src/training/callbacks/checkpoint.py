"""
Model checkpoint persistence callbacks with Top-K and Last checkpoint support.
"""

import math
import os
import tempfile
from typing import Dict, List, Optional, Tuple, cast

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
        self.run_name = _validate_path_component(run_name, "run_name") if run_name else None
        self.best_score = float("inf") if mode == "min" else float("-inf")
        self.filepath = os.path.join(save_dir, self.filename)
        self.last_filepath = os.path.join(
            save_dir,
            f"{self.run_name}_last.pt" if self.run_name else "last_model.pt",
        )
        self.canonical_last_filepath = os.path.join(save_dir, "last_model.pt")
        self.top_k_checkpoints: List[Tuple[float, str]] = []
        self.last_step = 0
        self.last_eval_step = 0
        self.last_metrics: Dict[str, float] = {}

    def state_dict(self) -> Dict[str, object]:
        return {
            "best_score": self.best_score,
            "top_k_checkpoints": [[score, path] for score, path in self.top_k_checkpoints],
            "last_step": self.last_step,
            "last_eval_step": self.last_eval_step,
            "last_metrics": dict(self.last_metrics),
        }

    def load_state_dict(self, state: Dict[str, object]) -> None:
        raw_best_score = cast(
            float | int | str,
            state.get(
                "best_score",
                float("inf") if self.mode == "min" else float("-inf"),
            ),
        )
        self.best_score = float(raw_best_score)
        raw_top_k = state.get("top_k_checkpoints", [])
        restored: List[Tuple[float, str]] = []
        if isinstance(raw_top_k, list):
            for item in raw_top_k:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    restored.append((float(cast(float | int | str, item[0])), str(item[1])))
        restored = [(score, path) for score, path in restored if os.path.exists(path)]
        restored.sort(key=lambda x: x[0], reverse=(self.mode == "max"))
        self.top_k_checkpoints = restored[: self.save_top_k] if self.save_top_k > 0 else []
        self.last_step = int(cast(int | str, state.get("last_step", 0)))
        self.last_eval_step = int(cast(int | str, state.get("last_eval_step", 0)))
        raw_metrics = state.get("last_metrics", {})
        self.last_metrics = (
            {str(key): float(cast(float | int | str, value)) for key, value in raw_metrics.items()}
            if isinstance(raw_metrics, dict)
            else {}
        )

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
                        if math.isfinite(val_float):
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

    def _is_better(self, candidate: float, reference: float) -> bool:
        return candidate < reference if self.mode == "min" else candidate > reference

    def _save_state(
        self,
        trainer: TrainerProtocol,
        step: int,
        metrics: Dict[str, float],
        path: str,
        is_best: bool = False,
    ) -> None:
        val_loss = metrics.get("val_loss")
        state = dict(trainer.get_checkpoint_state())
        state.update(
            {
                "step": step,
                self.monitor: metrics.get(self.monitor),
                "val_loss": val_loss,
                "metrics": dict(metrics),
                "is_best": is_best,
                "run_name": self.run_name,
            }
        )
        _atomic_torch_save(state, path)

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: Dict[str, float]) -> None:
        self.last_step = step
        self.last_eval_step = step
        self.last_metrics = dict(metrics)

        if self.monitor not in metrics:
            # ``last`` is lifecycle persistence, independent from best/top-k ranking.
            # Persist it even when this eval cannot participate in ranking.
            if self.save_last:
                self._save_state(trainer, step, metrics, self.last_filepath)
                if self.last_filepath != self.canonical_last_filepath:
                    self._save_state(trainer, step, metrics, self.canonical_last_filepath)
            logger.warning(
                f"[ModelCheckpoint] Không tìm thấy chỉ số '{self.monitor}' trong metrics: {list(metrics.keys())}"
            )
            return

        current = float(metrics[self.monitor])
        improved = self._is_improvement(current)
        old_best = self.best_score
        if improved:
            self.best_score = current

        versioned_path: Optional[str] = None
        paths_to_remove: List[str] = []
        if self.save_top_k > 0:
            qualifies = len(self.top_k_checkpoints) < self.save_top_k
            if not qualifies and self.top_k_checkpoints:
                qualifies = self._is_better(current, self.top_k_checkpoints[-1][0])
            if qualifies:
                prefix = self.run_name if self.run_name else "checkpoint"
                versioned_filename = f"{prefix}_step{step}_val{current:.4f}.pt"
                versioned_path = os.path.join(self.save_dir, versioned_filename)
                self.top_k_checkpoints.append((current, versioned_path))
                self.top_k_checkpoints.sort(key=lambda x: x[0], reverse=(self.mode == "max"))
                while len(self.top_k_checkpoints) > self.save_top_k:
                    _, worst_path = self.top_k_checkpoints.pop()
                    if worst_path != versioned_path:
                        paths_to_remove.append(worst_path)

        # Capture runtime state only after this callback's best/top-k bookkeeping
        # has been updated, so exact resume restores a coherent callback state.
        if self.save_last:
            self._save_state(trainer, step, metrics, self.last_filepath)
            if self.last_filepath != self.canonical_last_filepath:
                self._save_state(trainer, step, metrics, self.canonical_last_filepath)

        if improved:
            self._save_state(trainer, step, metrics, self.filepath, is_best=True)
            logger.info(
                f"⭐ [Checkpoint] Kỷ lục mới xuất sắc! ({self.monitor}: {current:.4f} so với {old_best:.4f}). "
                f"Đã cập nhật vào {self.filepath}"
            )
        else:
            logger.info(
                f"ℹ️ [Checkpoint] Bước {step} ({self.monitor}: {current:.4f}) chưa vượt qua "
                f"kỷ lục tốt nhất ({self.best_score:.4f}). Giữ nguyên {self.filename}."
            )

        if versioned_path is not None:
            self._save_state(trainer, step, metrics, versioned_path)

        for worst_path in paths_to_remove:
            if os.path.exists(worst_path):
                try:
                    os.remove(worst_path)
                    logger.info(
                        f"🗑️ [Checkpoint] Đã dọn '{os.path.basename(worst_path)}' "
                        f"để duy trì top-{self.save_top_k}."
                    )
                except OSError as exc:
                    logger.warning(f"Không thể xoá checkpoint cũ '{worst_path}': {exc}")

    def on_train_end(self, trainer: TrainerProtocol) -> None:
        """Persist final weights without attaching a stale/best metric to different weights."""
        if self.save_last and self.last_step > 0:
            # on_eval_end already persisted the exact final weights and runtime state.
            # Rewriting the same checkpoint here doubles I/O for the common case where
            # the trainer always evaluates on max_iters.
            if self.last_eval_step == self.last_step:
                return
            metrics: Dict[str, float] = {}
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
