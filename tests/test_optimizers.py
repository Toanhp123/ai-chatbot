"""
Unit tests for optimizers and learning rate schedulers:
- configure_optimizer (standard tensor dim separation, weight tying, custom hyperparameters)
- Model-Delegated Optimizer pattern
- compute_scheduled_lr (cosine, linear, constant, edge cases zero division)
"""

import pytest
import torch
import torch.nn as nn

from src.core.config import TrainingConfig
from src.core.exceptions import ConfigurationError
from src.training.optimizers import compute_scheduled_lr, configure_optimizer


class SimpleModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.embedding = nn.Embedding(10, 8)
        self.fc = nn.Linear(8, 8, bias=True)
        self.ln = nn.LayerNorm(8)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.ln(self.fc(self.embedding(x)))


class ModelWithCustomOptimizer(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.fc = nn.Linear(4, 2)

    def configure_optimizers(self, config: TrainingConfig) -> torch.optim.Optimizer:
        return torch.optim.RMSprop(self.parameters(), lr=config.learning_rate)


def test_configure_optimizer_parameter_grouping() -> None:
    """Kiểm tra phân loại tensor 1D (LayerNorm, Bias) sang no_decay và 2D+ sang decay."""
    model = SimpleModel()
    config = TrainingConfig(
        weight_decay=0.1,
        learning_rate=1e-3,
        adam_beta1=0.88,
        adam_beta2=0.96,
        adam_eps=1e-7,
    )
    optimizer = configure_optimizer(model, config)

    assert isinstance(optimizer, torch.optim.AdamW)
    assert len(optimizer.param_groups) == 2

    decay_group = optimizer.param_groups[0]
    no_decay_group = optimizer.param_groups[1]

    assert decay_group["weight_decay"] == 0.1
    assert no_decay_group["weight_decay"] == 0.0

    # embedding.weight (2D), fc.weight (2D) nằm trong decay
    decay_params = set(decay_group["params"])
    assert model.embedding.weight in decay_params
    assert model.fc.weight in decay_params

    # fc.bias (1D), ln.weight (1D), ln.bias (1D) nằm trong no_decay
    no_decay_params = set(no_decay_group["params"])
    assert model.fc.bias in no_decay_params
    assert model.ln.weight in no_decay_params
    assert model.ln.bias in no_decay_params

    # Kiểm tra betas và eps tùy biến
    assert optimizer.defaults["betas"] == (0.88, 0.96)
    assert optimizer.defaults["eps"] == 1e-7


def test_model_delegated_optimizer() -> None:
    """Kiểm tra mô hình có configure_optimizers sẽ được ưu tiên sử dụng."""
    model = ModelWithCustomOptimizer()
    config = TrainingConfig(learning_rate=5e-4)
    optimizer = configure_optimizer(model, config)

    assert isinstance(optimizer, torch.optim.RMSprop)
    assert optimizer.defaults["lr"] == 5e-4


def test_configure_optimizer_sgd() -> None:
    """Kiểm tra khởi tạo SGD với sgd_momentum từ config."""
    model = SimpleModel()
    config = TrainingConfig(optimizer_type="sgd", sgd_momentum=0.85, learning_rate=1e-2)
    optimizer = configure_optimizer(model, config)

    assert isinstance(optimizer, torch.optim.SGD)
    assert optimizer.defaults["momentum"] == 0.85
    assert optimizer.defaults["lr"] == 1e-2


def test_compute_scheduled_lr_cosine() -> None:
    """Kiểm tra Cosine Annealing LR Schedule."""
    config = TrainingConfig(
        learning_rate=1e-3,
        min_lr=1e-4,
        warmup_iters=10,
        max_iters=100,
        lr_scheduler_type="cosine",
    )

    # Warmup
    lr_step0 = compute_scheduled_lr(0, config)
    assert lr_step0 == pytest.approx(1e-3 * 1 / 10)

    lr_step9 = compute_scheduled_lr(9, config)
    assert lr_step9 == pytest.approx(1e-3)

    # Giữa chặng (cosine decay)
    lr_mid = compute_scheduled_lr(55, config)
    assert 1e-4 < lr_mid < 1e-3

    # Vượt max_iters -> min_lr
    lr_over = compute_scheduled_lr(150, config)
    assert lr_over == 1e-4


def test_compute_scheduled_lr_linear() -> None:
    """Kiểm tra Linear Decay LR Schedule."""
    config = TrainingConfig(
        learning_rate=1e-3,
        min_lr=0.0,
        warmup_iters=0,
        max_iters=100,
        lr_scheduler_type="linear",
    )

    lr_start = compute_scheduled_lr(0, config)
    assert lr_start == pytest.approx(1e-3)

    lr_half = compute_scheduled_lr(50, config)
    assert lr_half == pytest.approx(5e-4)

    lr_end = compute_scheduled_lr(100, config)
    assert lr_end == pytest.approx(0.0)


def test_compute_scheduled_lr_constant() -> None:
    """Kiểm tra Constant LR Schedule."""
    config = TrainingConfig(
        learning_rate=2e-4,
        warmup_iters=5,
        max_iters=50,
        lr_scheduler_type="constant",
    )

    # Trước warmup
    assert compute_scheduled_lr(2, config) < 2e-4
    # Sau warmup giữ nguyên
    assert compute_scheduled_lr(10, config) == 2e-4
    assert compute_scheduled_lr(40, config) == 2e-4


def test_compute_scheduled_lr_zero_division_guard() -> None:
    """Kiểm tra trường hợp max_iters == warmup_iters không sinh ZeroDivisionError."""
    config = TrainingConfig(
        learning_rate=1e-3,
        min_lr=1e-4,
        warmup_iters=50,
        max_iters=50,
        lr_scheduler_type="cosine",
    )

    lr = compute_scheduled_lr(50, config)
    assert lr is not None
    assert not torch.isnan(torch.tensor(lr))


def test_training_config_validation_errors() -> None:
    """Kiểm tra validation của các siêu tham số mới trong TrainingConfig."""
    with pytest.raises(ConfigurationError, match="adam_beta1"):
        TrainingConfig(adam_beta1=1.5).validate()

    with pytest.raises(ConfigurationError, match="adam_eps"):
        TrainingConfig(adam_eps=-1e-5).validate()

    with pytest.raises(ConfigurationError, match="sgd_momentum"):
        TrainingConfig(sgd_momentum=-0.1).validate()

    with pytest.raises(ConfigurationError, match="lr_scheduler_type"):
        TrainingConfig(lr_scheduler_type="exponential").validate()


def test_configure_optimizer_honors_resolved_optimizer_override() -> None:
    model = SimpleModel()
    config = TrainingConfig(optimizer_type="8bit_adamw")

    optimizer = configure_optimizer(model, config, optimizer_type="adamw")

    assert isinstance(optimizer, torch.optim.AdamW)
