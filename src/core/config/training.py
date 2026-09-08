"""
Cấu hình siêu tham số và vòng lặp huấn luyện (Training Configuration).
"""

from dataclasses import dataclass
from typing import Optional

from src.core.config.base import BaseConfig
from src.core.exceptions import ConfigurationError


def _validate_filename_component(value: str, field_name: str) -> None:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ConfigurationError(
            f"{field_name} phải là một tên an toàn và không được chứa thành phần đường dẫn"
        )


@dataclass
class TrainingConfig(BaseConfig):
    batch_size: int = 64
    max_iters: int = 3000
    eval_interval: int = 300
    eval_iters: int = 50
    learning_rate: float = 3e-4
    min_lr: float = 3e-5
    warmup_iters: int = 100
    weight_decay: float = 0.1
    grad_clip: float = 1.0
    checkpoint_dir: str = "checkpoints"
    checkpoint_name: str = "best_model.pt"
    run_name: Optional[str] = None
    save_top_k: int = 3
    save_last: bool = True
    early_stopping_patience: int = 10
    gradient_accumulation_steps: int = 1
    gradient_checkpointing: bool = False
    precision: str = "float32"
    optimizer_type: str = "adamw"
    adam_beta1: float = 0.9
    adam_beta2: float = 0.95
    adam_eps: float = 1e-8
    sgd_momentum: float = 0.9
    lr_scheduler_type: str = "cosine"

    def validate(self) -> None:
        if self.batch_size <= 0:
            raise ConfigurationError(f"batch_size phải > 0, nhận được {self.batch_size}")
        if self.max_iters <= 0:
            raise ConfigurationError(f"max_iters phải > 0, nhận được {self.max_iters}")
        if self.eval_interval <= 0:
            raise ConfigurationError(f"eval_interval phải > 0, nhận được {self.eval_interval}")
        if self.eval_iters <= 0:
            raise ConfigurationError(f"eval_iters phải > 0, nhận được {self.eval_iters}")
        if self.learning_rate <= 0:
            raise ConfigurationError(f"learning_rate phải > 0, nhận được {self.learning_rate}")
        if self.min_lr < 0:
            raise ConfigurationError(f"min_lr phải >= 0, nhận được {self.min_lr}")
        if self.min_lr > self.learning_rate:
            raise ConfigurationError(
                f"min_lr ({self.min_lr}) không được lớn hơn learning_rate ({self.learning_rate})",
                {"min_lr": self.min_lr, "learning_rate": self.learning_rate},
            )
        if self.warmup_iters < 0:
            raise ConfigurationError(f"warmup_iters phải >= 0, nhận được {self.warmup_iters}")
        if self.weight_decay < 0:
            raise ConfigurationError(f"weight_decay phải >= 0, nhận được {self.weight_decay}")
        if self.grad_clip < 0:
            raise ConfigurationError(f"grad_clip phải >= 0, nhận được {self.grad_clip}")
        if not self.checkpoint_dir:
            raise ConfigurationError("checkpoint_dir không được để trống!")
        _validate_filename_component(self.checkpoint_name, "checkpoint_name")
        if self.run_name is not None:
            _validate_filename_component(self.run_name, "run_name")
        if self.save_top_k < 0:
            raise ConfigurationError(f"save_top_k phải >= 0, nhận được {self.save_top_k}")
        if self.gradient_accumulation_steps <= 0:
            raise ConfigurationError(
                f"gradient_accumulation_steps phải >= 1, nhận được {self.gradient_accumulation_steps}"
            )
        if not isinstance(self.gradient_checkpointing, bool):
            raise ConfigurationError(
                f"gradient_checkpointing phải là boolean, nhận được {type(self.gradient_checkpointing).__name__}"
            )
        valid_precisions = ("float32", "float16", "bfloat16", "amp_fp16", "amp_bf16")
        if self.precision.lower() not in valid_precisions:
            raise ConfigurationError(
                f"precision '{self.precision}' không hợp lệ. Hỗ trợ: {', '.join(valid_precisions)}"
            )
        valid_optimizers = ("adamw", "8bit_adamw", "sgd")
        if self.optimizer_type.lower() not in valid_optimizers:
            raise ConfigurationError(
                f"optimizer_type '{self.optimizer_type}' không hợp lệ. Hỗ trợ: {', '.join(valid_optimizers)}"
            )
        if not (0.0 <= self.adam_beta1 < 1.0):
            raise ConfigurationError(
                f"adam_beta1 phải nằm trong [0.0, 1.0), nhận được {self.adam_beta1}"
            )
        if not (0.0 <= self.adam_beta2 < 1.0):
            raise ConfigurationError(
                f"adam_beta2 phải nằm trong [0.0, 1.0), nhận được {self.adam_beta2}"
            )
        if self.adam_eps <= 0:
            raise ConfigurationError(f"adam_eps phải > 0, nhận được {self.adam_eps}")
        if not (0.0 <= self.sgd_momentum < 1.0):
            raise ConfigurationError(
                f"sgd_momentum phải nằm trong [0.0, 1.0), nhận được {self.sgd_momentum}"
            )
        valid_schedulers = ("cosine", "linear", "constant")
        if self.lr_scheduler_type.lower() not in valid_schedulers:
            raise ConfigurationError(
                f"lr_scheduler_type '{self.lr_scheduler_type}' không hợp lệ. Hỗ trợ: {', '.join(valid_schedulers)}"
            )
