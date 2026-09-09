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

import copy
import math
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import torch
import torch.nn as nn
from torch.amp import GradScaler, autocast  # pyright: ignore[reportPrivateImportUsage]

from src.core.config import EngineConfig
from src.core.exceptions import CheckpointNotFoundError, TrainingDivergedError
from src.core.logging import get_logger
from src.core.runtime import ResolvedTrainingPlan, resolve_training_plan, validate_training_plan
from src.data.api import (
    BaseBatchProvider,
    BaseTokenizer,
    TensorBatchProvider,
    get_tokenizer_identity,
    load_tokenizer_state,
)
from src.models.api import BaseModel
from src.training.callbacks import BaseCallback
from src.training.optimizers import compute_scheduled_lr, configure_optimizer
from src.utils.seed import capture_rng_state, restore_rng_state

logger = get_logger("Trainer")


class TrainingTerminationReason(str, Enum):
    """Stable terminal reason contract shared by Trainer and UI orchestration."""

    COMPLETED = "COMPLETED"
    EARLY_STOPPED = "EARLY_STOPPED"
    USER_STOPPED = "USER_STOPPED"
    ABORTED_STARTUP = "ABORTED_STARTUP"
    FAILED = "FAILED"


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
    termination_reason: TrainingTerminationReason = TrainingTerminationReason.COMPLETED


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
        tokenizer: Optional[BaseTokenizer] = None,
        runtime_plan: Optional[ResolvedTrainingPlan] = None,
        **kwargs: Any,
    ) -> None:
        if config is None:
            raise ValueError("Cần cung cấp config (EngineConfig) cho Trainer.")
        config.validate()
        self.config = config
        self.model = model
        self.callbacks = callbacks or []
        self.tokenizer = tokenizer

        # Thiết lập nguồn dữ liệu
        if batch_provider is not None:
            self.batch_provider = batch_provider
        elif train_data is not None and val_data is not None:
            self.batch_provider = TensorBatchProvider(train_data, val_data)
        else:
            raise ValueError("Cần cung cấp batch_provider hoặc cặp (train_data, val_data).")

        # Resolve one effective runtime contract shared with diagnostics/preflight.
        if runtime_plan is not None and device is not None:
            raise ValueError(
                "Không thể truyền đồng thời runtime_plan và device override cho Trainer."
            )
        if runtime_plan is not None:
            validate_training_plan(config, runtime_plan)
            self.runtime_plan = runtime_plan
        else:
            self.runtime_plan = resolve_training_plan(config, device_override=device)
        self.device = self.runtime_plan.device
        self.device_type = self.runtime_plan.device_type
        self.precision = self.runtime_plan.precision

        # Cấu hình Automatic Mixed Precision (AMP)
        if self.precision in ("amp_fp16", "float16"):
            self.amp_dtype = torch.float16
            self.use_amp = self.runtime_plan.use_amp
            self.scaler = GradScaler(self.device_type, enabled=self.use_amp)
        elif self.precision in ("amp_bf16", "bfloat16"):
            self.amp_dtype = torch.bfloat16
            self.use_amp = self.runtime_plan.use_amp
            self.scaler = GradScaler(self.device_type, enabled=False)
        else:
            self.amp_dtype = torch.float32
            self.use_amp = False
            self.scaler = GradScaler(self.device_type, enabled=False)

        self.model.to(self.device)

        gradient_checkpointing = bool(config.training.gradient_checkpointing)
        set_gradient_checkpointing = getattr(self.model, "set_gradient_checkpointing", None)
        if gradient_checkpointing and not callable(set_gradient_checkpointing):
            raise ValueError(
                "Model hiện tại không hỗ trợ gradient_checkpointing nhưng cấu hình đã bật."
            )
        if callable(set_gradient_checkpointing):
            set_gradient_checkpointing(gradient_checkpointing)

        # Hỗ trợ Dependency Injection cho Optimizer
        if optimizer is not None:
            self.optimizer = optimizer
        else:
            self.optimizer = configure_optimizer(
                self.model,
                config.training,
                optimizer_type=self.runtime_plan.optimizer_type,
            )

        self.current_lr = config.training.learning_rate
        self.should_stop = False
        self._stop_reason: Optional[TrainingTerminationReason] = None
        self.start_step = 1
        self.best_val_loss: Optional[float] = None

    @property
    def max_iters(self) -> int:
        """Tổng số bước huấn luyện tối đa được cấu hình."""
        return self.config.training.max_iters

    def _request_stop_with_reason(self, reason: TrainingTerminationReason) -> None:
        self.should_stop = True
        # An explicit user stop has precedence if it races an early-stopping callback.
        if self._stop_reason is None or reason is TrainingTerminationReason.USER_STOPPED:
            self._stop_reason = reason

    def request_stop(self) -> None:
        """Yêu cầu dừng do người dùng/caller chủ động."""
        self._request_stop_with_reason(TrainingTerminationReason.USER_STOPPED)

    def request_early_stop(self) -> None:
        """Yêu cầu dừng do convergence policy, không phải user interruption."""
        self._request_stop_with_reason(TrainingTerminationReason.EARLY_STOPPED)

    def get_model_state_dict(self) -> Dict[str, Any]:
        """Lấy bản sao state dict của mô hình."""
        return self.model.state_dict()

    def get_optimizer_state_dict(self) -> Optional[Dict[str, Any]]:
        """Lấy state dict của optimizer nếu đã khởi tạo."""
        return self.optimizer.state_dict() if hasattr(self, "optimizer") else None

    def get_config_dict(self) -> Dict[str, Any]:
        """Lấy cấu hình hiện tại dưới dạng dictionary."""
        return self.config.to_dict()

    @staticmethod
    def _callback_key(callback: BaseCallback) -> str:
        callback_type = type(callback)
        return f"{callback_type.__module__}.{callback_type.__qualname__}"

    def get_runtime_state(self) -> Dict[str, Any]:
        """Capture stochastic/runtime state required to continue the same trajectory."""
        callback_states = []
        for callback in self.callbacks:
            state = callback.state_dict()
            if state:
                callback_states.append({"type": self._callback_key(callback), "state": state})

        provider_state = self.batch_provider.state_dict()
        return {
            "trainer": {"best_val_loss": self.best_val_loss},
            "rng": capture_rng_state(),
            "grad_scaler": self.scaler.state_dict(),
            "batch_provider": {
                "type": f"{type(self.batch_provider).__module__}.{type(self.batch_provider).__qualname__}",
                "supports_exact_resume": self.batch_provider.supports_exact_resume,
                "state": provider_state,
            },
            "callbacks": callback_states,
        }

    def get_checkpoint_state(self) -> Dict[str, Any]:
        """Build a portable checkpoint payload from trainer-owned runtime state."""
        tokenizer_identity = (
            get_tokenizer_identity(self.tokenizer) if self.tokenizer is not None else None
        )
        tokenizer_state = (
            dict(tokenizer_identity["payload"]) if tokenizer_identity is not None else None
        )
        checkpoint_version = 3 if tokenizer_state is not None else 1
        return {
            "checkpoint_version": checkpoint_version,
            "model_state_dict": self.get_model_state_dict(),
            "optimizer_state_dict": self.get_optimizer_state_dict(),
            "config": self.get_config_dict(),
            "tokenizer_identity": tokenizer_identity,
            "tokenizer_state": tokenizer_state,
            "runtime_state": self.get_runtime_state(),
        }

    @staticmethod
    def _resume_trajectory_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Strip fields that may change without altering the resumed training trajectory."""
        normalized = copy.deepcopy(config_dict)
        normalized.pop("generation", None)
        training = normalized.get("training")
        if isinstance(training, dict):
            for key in (
                "max_iters",
                "checkpoint_dir",
                "checkpoint_name",
                "run_name",
                "save_top_k",
                "save_last",
            ):
                training.pop(key, None)
        system = normalized.get("system")
        if isinstance(system, dict):
            system.pop("log_level", None)
            system.pop("log_file", None)
        return normalized

    @staticmethod
    def _first_config_diff(
        saved: Any, current: Any, path: str = "config"
    ) -> Optional[tuple[str, Any, Any]]:
        if isinstance(saved, dict) and isinstance(current, dict):
            for key in sorted(set(saved) | set(current)):
                child_path = f"{path}.{key}"
                if key not in saved:
                    return child_path, None, current[key]
                if key not in current:
                    return child_path, saved[key], None
                diff = Trainer._first_config_diff(saved[key], current[key], child_path)
                if diff is not None:
                    return diff
            return None
        if saved != current:
            return path, saved, current
        return None

    def _validate_checkpoint_config_compatibility(self, saved_config: Any) -> None:
        if not isinstance(saved_config, dict):
            logger.warning(
                "Checkpoint legacy không có config đầy đủ; bỏ qua semantic config compatibility check."
            )
            return

        # Only full Trainer checkpoints can promise exact semantic resume. Partial
        # inference-oriented checkpoints remain loadable through the legacy path.
        required_domains = {"system", "data", "model", "training"}
        if not required_domains.issubset(saved_config):
            logger.warning(
                "Checkpoint legacy chỉ chứa config một phần; bỏ qua semantic config compatibility check."
            )
            return

        current_config = self.get_config_dict()
        saved_training = saved_config.get("training")
        current_training = current_config.get("training")
        if isinstance(saved_training, dict) and isinstance(current_training, dict):
            saved_max = saved_training.get("max_iters")
            current_max = current_training.get("max_iters")
            if (
                isinstance(saved_max, int)
                and isinstance(current_max, int)
                and current_max < saved_max
            ):
                raise ValueError(
                    "Resume config không tương thích: training.max_iters không được giảm "
                    f"({saved_max} -> {current_max})."
                )

        saved_trajectory = self._resume_trajectory_config(saved_config)
        current_trajectory = self._resume_trajectory_config(current_config)
        diff = self._first_config_diff(saved_trajectory, current_trajectory)
        if diff is not None:
            path, saved_value, current_value = diff
            raise ValueError(
                "Resume config không tương thích với trajectory checkpoint tại "
                f"{path}: {saved_value!r} != {current_value!r}."
            )

    def _validate_runtime_state_compatibility(self, runtime_state: Dict[str, Any]) -> None:
        """Preflight runtime-owned contracts before any checkpoint state is committed."""
        provider_state = runtime_state.get("batch_provider")
        if not isinstance(provider_state, dict):
            return
        saved_type = provider_state.get("type")
        current_type = (
            f"{type(self.batch_provider).__module__}.{type(self.batch_provider).__qualname__}"
        )
        if saved_type and saved_type != current_type:
            raise ValueError(
                f"Batch provider checkpoint không khớp: {saved_type} != {current_type}."
            )
        if provider_state.get("supports_exact_resume") is False:
            raise ValueError("Checkpoint được tạo bởi batch provider không hỗ trợ exact resume.")

    def _restore_runtime_state(self, runtime_state: Dict[str, Any]) -> None:
        trainer_state = runtime_state.get("trainer")
        if isinstance(trainer_state, dict):
            raw_best = trainer_state.get("best_val_loss")
            self.best_val_loss = float(raw_best) if raw_best is not None else None

        scaler_state = runtime_state.get("grad_scaler")
        if isinstance(scaler_state, dict):
            self.scaler.load_state_dict(scaler_state)

        self._validate_runtime_state_compatibility(runtime_state)
        provider_state = runtime_state.get("batch_provider")
        if isinstance(provider_state, dict):
            raw_provider_state = provider_state.get("state")
            if isinstance(raw_provider_state, dict):
                self.batch_provider.load_state_dict(raw_provider_state)

        saved_callbacks = runtime_state.get("callbacks", [])
        if isinstance(saved_callbacks, list):
            remaining = list(self.callbacks)
            for item in saved_callbacks:
                if not isinstance(item, dict) or not isinstance(item.get("state"), dict):
                    continue
                saved_type = item.get("type")
                for index, callback in enumerate(remaining):
                    if self._callback_key(callback) == saved_type:
                        callback.load_state_dict(item["state"])
                        remaining.pop(index)
                        break

        rng_state = runtime_state.get("rng")
        if isinstance(rng_state, dict):
            # Restore last: initialization/state loading above must not perturb the resumed stream.
            restore_rng_state(rng_state)

    def resume_from_checkpoint(
        self,
        checkpoint_path: str,
        expected_identity: Optional[tuple[int, int, int, int]] = None,
    ) -> int:
        """Load one exact checkpoint revision for semantic resume.

        When ``expected_identity`` is supplied by the Start request, bind the payload
        to the same opened file descriptor used for ``torch.load``. Atomic pathname
        replacement after Start is therefore rejected instead of silently resuming a
        different artifact.
        """
        try:
            with open(checkpoint_path, "rb") as checkpoint_file:
                file_stat = os.fstat(checkpoint_file.fileno())
                actual_identity = (
                    int(file_stat.st_dev),
                    int(file_stat.st_ino),
                    int(file_stat.st_size),
                    int(file_stat.st_mtime_ns),
                )
                if expected_identity is not None and actual_identity != expected_identity:
                    raise ValueError(
                        "Checkpoint resume đã thay đổi revision sau khi yêu cầu Start được chốt; "
                        "từ chối nạp artifact khác với artifact đã chọn."
                    )
                state = torch.load(checkpoint_file, map_location=self.device, weights_only=True)
        except FileNotFoundError as exc:
            raise CheckpointNotFoundError(checkpoint_path=checkpoint_path) from exc

        # Validate semantic compatibility before mutating model/optimizer/runtime state.
        # A rejected resume must be atomic from the caller's perspective.
        checkpoint_version = int(state.get("checkpoint_version", 1))
        self._validate_checkpoint_config_compatibility(state.get("config"))
        checkpoint_identity = state.get("tokenizer_identity")
        resume_tokenizer = self.tokenizer
        if checkpoint_version >= 2:
            if not isinstance(checkpoint_identity, dict):
                raise ValueError("Checkpoint v2+ thiếu tokenizer identity bắt buộc.")
            if checkpoint_version >= 3:
                embedded_state = state.get("tokenizer_state")
                if not isinstance(embedded_state, dict):
                    raise ValueError("Checkpoint v3 thiếu tokenizer state bắt buộc.")
                embedded_tokenizer = load_tokenizer_state(embedded_state)
                embedded_identity = get_tokenizer_identity(embedded_tokenizer)
                if checkpoint_identity.get("fingerprint") != embedded_identity.get("fingerprint"):
                    raise ValueError(
                        "Tokenizer state nhúng không khớp tokenizer identity của checkpoint."
                    )
                if resume_tokenizer is None:
                    resume_tokenizer = embedded_tokenizer
            if resume_tokenizer is None:
                raise ValueError("Trainer phải được cung cấp tokenizer để xác minh checkpoint v2.")
            current_identity = get_tokenizer_identity(resume_tokenizer)
            if checkpoint_identity.get("fingerprint") != current_identity.get("fingerprint"):
                raise ValueError("Tokenizer hiện tại không khớp tokenizer identity của checkpoint.")
        elif resume_tokenizer is not None and isinstance(checkpoint_identity, dict):
            current_identity = get_tokenizer_identity(resume_tokenizer)
            if checkpoint_identity.get("fingerprint") != current_identity.get("fingerprint"):
                raise ValueError("Tokenizer hiện tại không khớp tokenizer identity của checkpoint.")

        runtime_state = state.get("runtime_state")
        if isinstance(runtime_state, dict):
            self._validate_runtime_state_compatibility(runtime_state)

        if "model_state_dict" in state:
            self.model.load_state_dict(state["model_state_dict"])
        if "optimizer_state_dict" in state and state["optimizer_state_dict"] is not None:
            self.optimizer.load_state_dict(state["optimizer_state_dict"])
        if self.tokenizer is None and resume_tokenizer is not None:
            self.tokenizer = resume_tokenizer

        if isinstance(runtime_state, dict):
            self._restore_runtime_state(runtime_state)
        else:
            logger.warning(
                "Checkpoint legacy không có runtime_state; chỉ model/optimizer được khôi phục, "
                "không thể đảm bảo trajectory lossless."
            )

        resumed_step = int(state.get("step", 0))
        self.start_step = resumed_step + 1
        logger.info(
            f"Phục hồi trạng thái huấn luyện thành công từ bước {resumed_step} (Checkpoint: {checkpoint_path})"
        )
        return resumed_step

    @torch.no_grad()
    def evaluate(self) -> Dict[str, float]:
        """Đánh giá loss trung bình và khôi phục mode mô hình của caller."""
        was_training = bool(self.model.training)
        self.model.eval()
        eval_iters = self.config.training.eval_iters
        block_size = self.config.model.block_size
        batch_size = self.config.training.batch_size

        metrics: Dict[str, float] = {}
        try:
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
        finally:
            self.model.train(was_training)

        return metrics

    def train(
        self,
        resume_checkpoint: Optional[str] = None,
        resume_checkpoint_identity: Optional[tuple[int, int, int, int]] = None,
    ) -> TrainOutput:
        """Vòng lặp huấn luyện chính với Gradient Accumulation, AMP và Graceful Shutdown."""
        start_time = time.time()

        # Initialize callback-owned resources/default state before restoring a resume
        # checkpoint.  Restoring first would let on_train_begin() overwrite the
        # checkpointed callback state immediately afterwards.
        for cb in self.callbacks:
            cb.on_train_begin(self)

        if resume_checkpoint is not None:
            self.resume_from_checkpoint(
                resume_checkpoint, expected_identity=resume_checkpoint_identity
            )

        max_iters = self.config.training.max_iters
        eval_interval = self.config.training.eval_interval
        block_size = self.config.model.block_size
        batch_size = self.config.training.batch_size
        grad_clip = self.config.training.grad_clip
        accum_steps = max(1, self.config.training.gradient_accumulation_steps)

        termination_reason = TrainingTerminationReason.COMPLETED
        last_step = self.start_step - 1
        effective_step_loss = 0.0
        last_metrics: Dict[str, float] = {}

        self.model.train()
        try:
            for step in range(self.start_step, max_iters + 1):
                if self.should_stop:
                    logger.info(
                        f"Đã nhận tín hiệu dừng sớm (request_stop) tại bước {step}. Đang ngắt vòng lặp an toàn."
                    )
                    termination_reason = self._stop_reason or TrainingTerminationReason.USER_STOPPED
                    break

                last_step = step
                # Scheduler uses zero-based update indices; public training steps remain one-based.
                self.current_lr = compute_scheduled_lr(step - 1, self.config.training)
                for param_group in self.optimizer.param_groups:
                    param_group["lr"] = self.current_lr

                # 2. Vòng lặp tích lũy Gradient (Gradient Accumulation)
                self.optimizer.zero_grad(set_to_none=True)
                accumulated_loss: Optional[torch.Tensor] = None

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

                    detached_loss = loss.detach()
                    accumulated_loss = (
                        detached_loss
                        if accumulated_loss is None
                        else accumulated_loss + detached_loss
                    )
                    self.scaler.scale(loss_scaled).backward()

                assert accumulated_loss is not None
                # One scalar read per optimizer update instead of one GPU sync per
                # accumulation microbatch.  Python-side finiteness validation keeps
                # NaN/Inf loss fatal without interfering with GradScaler overflow.
                effective_step_loss = float((accumulated_loss / accum_steps).item())
                if not math.isfinite(effective_step_loss):
                    raise TrainingDivergedError(
                        "Phát hiện giá trị NaN/Inf trong Training Loss!",
                        {"tensor_name": "Training Loss"},
                    )

                # 3. Unscale một lần trước gradient clipping. Recoverable fp16
                # overflow is owned by GradScaler; do not pre-empt it with a
                # per-parameter NaN/Inf scan that synchronizes the GPU.
                scaler_enabled = self.scaler.is_enabled()
                if scaler_enabled:
                    self.scaler.unscale_(self.optimizer)

                try:
                    if grad_clip > 0:
                        torch.nn.utils.clip_grad_norm_(
                            self.model.parameters(),
                            max_norm=grad_clip,
                            error_if_nonfinite=not scaler_enabled,
                        )
                    elif not scaler_enabled:
                        # Validate non-AMP gradients without changing them. One
                        # global norm reduction replaces N parameter-level syncs.
                        torch.nn.utils.clip_grad_norm_(
                            self.model.parameters(),
                            max_norm=float("inf"),
                            error_if_nonfinite=True,
                        )
                except RuntimeError as exc:
                    if "non-finite" in str(exc).lower():
                        raise TrainingDivergedError(
                            "Phát hiện gradient NaN/Inf trong bước huấn luyện."
                        ) from exc
                    raise

                self.scaler.step(self.optimizer)
                self.scaler.update()

                # 4. Trigger hook on_step_end
                for cb in self.callbacks:
                    cb.on_step_end(self, step, effective_step_loss)

                # 5. Đánh giá định kỳ
                if step % eval_interval == 0 or step == max_iters:
                    last_metrics = self.evaluate()
                    val_loss = last_metrics.get("val_loss")
                    if val_loss is not None:
                        self.best_val_loss = (
                            val_loss
                            if self.best_val_loss is None
                            else min(self.best_val_loss, val_loss)
                        )
                    for cb in self.callbacks:
                        cb.on_eval_end(self, step, last_metrics)

        except KeyboardInterrupt:
            logger.warning(
                f"\n⚠️ Quá trình huấn luyện bị ngắt bởi người dùng (KeyboardInterrupt) tại bước {last_step}."
            )
            termination_reason = TrainingTerminationReason.USER_STOPPED
        finally:
            # Trigger hook on_train_end và dọn dẹp bộ nhớ GPU
            for cb in self.callbacks:
                cb.on_train_end(self)
            if self.device_type == "cuda":
                torch.cuda.empty_cache()

        elapsed_time = time.time() - start_time
        return TrainOutput(
            global_step=last_step,
            total_steps=max(0, last_step - self.start_step + 1),
            final_train_loss=effective_step_loss,
            best_val_loss=self.best_val_loss,
            metrics=last_metrics,
            elapsed_time_sec=elapsed_time,
            interrupted=termination_reason is TrainingTerminationReason.USER_STOPPED,
            termination_reason=termination_reason,
        )


__all__ = ["Trainer", "TrainOutput", "TrainingTerminationReason"]
