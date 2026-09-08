"""
Trainer Engine: Điều phối quy trình huấn luyện, tối ưu hóa và đánh giá mô hình ngôn ngữ.
Hỗ trợ:
- Tích lũy Gradient (Gradient Accumulation) qua gradient_accumulation_steps.
- Huấn luyện độ chính xác hỗn hợp Automatic Mixed Precision (AMP với GradScaler).
- Chuẩn hóa chu trình Unscale Gradient trước khi thanh tra và Gradient Clipping.
- Dependency Injection cho Optimizer (cho phép inject Custom Optimizer bên ngoài).
- Phục hồi trạng thái huấn luyện không tổn thất (Lossless Checkpoint Resumption).
- Graceful Shutdown khi bị ngắt (KeyboardInterrupt / Ctrl+C).
- Trả về đối tượng tổng kết TrainOutput chuẩn công nghiệp.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import torch
import torch.nn as nn
from torch.amp import GradScaler, autocast  # pyright: ignore[reportPrivateImportUsage]

from src.core.config import EngineConfig
from src.core.exceptions import CheckpointNotFoundError
from src.core.logging import get_logger
from src.data.batch_provider import BaseBatchProvider, TensorBatchProvider
from src.models.base import BaseModel
from src.training.callbacks import BaseCallback
from src.training.optimizers import compute_scheduled_lr, configure_optimizer
from src.utils.tensor_inspector import assert_valid_tensor, check_model_gradients

logger = get_logger("Trainer")


@dataclass
class TrainOutput:
    """Đối tượng đóng gói toàn bộ kết quả sau phiên huấn luyện."""

    global_step: int
    total_steps: int
    final_train_loss: float
    best_val_loss: Optional[float] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    elapsed_time_sec: float = 0.0
    interrupted: bool = False


class Trainer:
    """Bộ điều phối huấn luyện mô hình ngôn ngữ chuẩn Enterprise."""

    def __init__(
        self,
        model: Union[BaseModel, nn.Module],
        batch_provider: Optional[BaseBatchProvider] = None,
        train_data: Optional[torch.Tensor] = None,
        val_data: Optional[torch.Tensor] = None,
        config: Optional[EngineConfig] = None,
        callbacks: Optional[List[BaseCallback]] = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
        device: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if config is None:
            raise ValueError("Cần cung cấp config (EngineConfig) cho Trainer.")
        self.config = config
        self.model = model
        self.callbacks = callbacks or []

        # Thiết lập nguồn dữ liệu
        if batch_provider is not None:
            self.batch_provider = batch_provider
        elif train_data is not None and val_data is not None:
            self.batch_provider = TensorBatchProvider(train_data, val_data)
        else:
            raise ValueError("Cần cung cấp batch_provider hoặc cặp (train_data, val_data).")

        # Xác định thiết bị
        if device is None:
            if config.system.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = config.system.device
        else:
            self.device = device

        self.device_type = (
            "cuda" if "cuda" in self.device else ("mps" if "mps" in self.device else "cpu")
        )
        self.precision = config.training.precision.lower().strip()

        # Cấu hình Automatic Mixed Precision (AMP)
        if self.precision in ("amp_fp16", "float16"):
            self.amp_dtype = torch.float16
            self.use_amp = self.device_type == "cuda"
            self.scaler = GradScaler(self.device_type, enabled=self.use_amp)
        elif self.precision in ("amp_bf16", "bfloat16"):
            self.amp_dtype = torch.bfloat16
            self.use_amp = (self.device_type == "cuda") and torch.cuda.is_bf16_supported()
            self.scaler = GradScaler(self.device_type, enabled=False)
        else:
            self.amp_dtype = torch.float32
            self.use_amp = False
            self.scaler = GradScaler(self.device_type, enabled=False)

        self.model.to(self.device)

        # Hỗ trợ Dependency Injection cho Optimizer
        if optimizer is not None:
            self.optimizer = optimizer
        else:
            self.optimizer = configure_optimizer(self.model, config.training)

        self.current_lr = config.training.learning_rate
        self.should_stop = False
        self.start_step = 1

    @property
    def max_iters(self) -> int:
        """Tổng số bước huấn luyện tối đa được cấu hình."""
        return self.config.training.max_iters

    def request_stop(self) -> None:
        """Kích hoạt cờ yêu cầu dừng sớm vòng lặp huấn luyện."""
        self.should_stop = True

    def get_model_state_dict(self) -> Dict[str, Any]:
        """Lấy bản sao state dict của mô hình."""
        return self.model.state_dict()

    def get_optimizer_state_dict(self) -> Optional[Dict[str, Any]]:
        """Lấy state dict của optimizer nếu đã khởi tạo."""
        return self.optimizer.state_dict() if hasattr(self, "optimizer") else None

    def get_config_dict(self) -> Dict[str, Any]:
        """Lấy cấu hình hiện tại dưới dạng dictionary."""
        return self.config.to_dict()

    def resume_from_checkpoint(self, checkpoint_path: str) -> int:
        """Nạp trọng số mô hình và trạng thái optimizer từ checkpoint để tiếp tục huấn luyện."""
        if not os.path.exists(checkpoint_path):
            raise CheckpointNotFoundError(checkpoint_path=checkpoint_path)

        state = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
        if "model_state_dict" in state:
            self.model.load_state_dict(state["model_state_dict"])
        if "optimizer_state_dict" in state and state["optimizer_state_dict"] is not None:
            self.optimizer.load_state_dict(state["optimizer_state_dict"])

        resumed_step = int(state.get("step", 0))
        self.start_step = resumed_step + 1
        logger.info(
            f"Phục hồi trạng thái huấn luyện thành công từ bước {resumed_step} (Checkpoint: {checkpoint_path})"
        )
        return resumed_step

    @torch.no_grad()
    def evaluate(self) -> Dict[str, float]:
        """Đánh giá loss trung bình trên tập train và val thông qua batch_provider."""
        self.model.eval()
        eval_iters = self.config.training.eval_iters
        block_size = self.config.model.block_size
        batch_size = self.config.training.batch_size

        metrics: Dict[str, float] = {}
        for split_name, getter in [
            ("train", self.batch_provider.get_train_batch),
            ("val", self.batch_provider.get_val_batch),
        ]:
            losses = torch.zeros(eval_iters)
            for k in range(eval_iters):
                X, Y = getter(batch_size, block_size, self.device)
                with autocast(
                    device_type=self.device_type,
                    dtype=self.amp_dtype,
                    enabled=self.use_amp,
                ):
                    _, loss = self.model(X, Y)
                assert loss is not None, "Evaluation step returned None loss"
                losses[k] = loss.item()
            metrics[f"{split_name}_loss"] = float(losses.mean().item())

        self.model.train()
        return metrics

    def train(self, resume_checkpoint: Optional[str] = None) -> TrainOutput:
        """Vòng lặp huấn luyện chính với Gradient Accumulation, AMP và Graceful Shutdown."""
        start_time = time.time()
        if resume_checkpoint is not None:
            self.resume_from_checkpoint(resume_checkpoint)

        max_iters = self.config.training.max_iters
        eval_interval = self.config.training.eval_interval
        block_size = self.config.model.block_size
        batch_size = self.config.training.batch_size
        grad_clip = self.config.training.grad_clip
        accum_steps = max(1, self.config.training.gradient_accumulation_steps)

        interrupted = False
        last_step = self.start_step - 1
        effective_step_loss = 0.0
        last_metrics: Dict[str, float] = {}

        # Trigger hook on_train_begin
        for cb in self.callbacks:
            cb.on_train_begin(self)

        self.model.train()
        try:
            for step in range(self.start_step, max_iters + 1):
                last_step = step
                if self.should_stop:
                    logger.info(
                        f"Đã nhận tín hiệu dừng sớm (request_stop) tại bước {step}. Đang ngắt vòng lặp an toàn."
                    )
                    interrupted = True
                    break

                # 1. Cập nhật Learning Rate
                self.current_lr = compute_scheduled_lr(step, self.config.training)
                for param_group in self.optimizer.param_groups:
                    param_group["lr"] = self.current_lr

                # 2. Vòng lặp tích lũy Gradient (Gradient Accumulation)
                self.optimizer.zero_grad(set_to_none=True)
                accum_loss = 0.0

                for _ in range(accum_steps):
                    xb, yb = self.batch_provider.get_train_batch(
                        batch_size, block_size, self.device
                    )
                    with autocast(
                        device_type=self.device_type,
                        dtype=self.amp_dtype,
                        enabled=self.use_amp,
                    ):
                        _, loss = self.model(xb, yb)
                        assert loss is not None, "Model forward returned None loss during training"
                        loss_scaled = loss / accum_steps

                    accum_loss += loss.item()
                    self.scaler.scale(loss_scaled).backward()

                effective_step_loss = accum_loss / accum_steps
                assert_valid_tensor(torch.tensor(effective_step_loss), "Training Loss")

                # 3. Chuẩn hóa Unscale trước khi kiểm tra Gradients & Clipping
                if self.use_amp:
                    self.scaler.unscale_(self.optimizer)

                check_model_gradients(self.model)

                if grad_clip > 0:
                    if not self.use_amp:
                        self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=grad_clip)

                self.scaler.step(self.optimizer)
                self.scaler.update()

                # 4. Trigger hook on_step_end
                for cb in self.callbacks:
                    cb.on_step_end(self, step, effective_step_loss)

                # 5. Đánh giá định kỳ
                if step % eval_interval == 0 or step == max_iters:
                    last_metrics = self.evaluate()
                    for cb in self.callbacks:
                        cb.on_eval_end(self, step, last_metrics)

        except KeyboardInterrupt:
            logger.warning(
                f"\n⚠️ Quá trình huấn luyện bị ngắt bởi người dùng (KeyboardInterrupt) tại bước {last_step}."
            )
            interrupted = True
        finally:
            # Trigger hook on_train_end và dọn dẹp bộ nhớ GPU
            for cb in self.callbacks:
                cb.on_train_end(self)
            if self.device_type == "cuda":
                torch.cuda.empty_cache()

        elapsed_time = time.time() - start_time
        best_val_loss = last_metrics.get("val_loss")

        return TrainOutput(
            global_step=last_step,
            total_steps=max(0, last_step - self.start_step + 1),
            final_train_loss=effective_step_loss,
            best_val_loss=best_val_loss,
            metrics=last_metrics,
            elapsed_time_sec=elapsed_time,
            interrupted=interrupted,
        )


__all__ = ["Trainer", "TrainOutput"]
