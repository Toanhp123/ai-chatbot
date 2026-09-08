"""
Factory khởi tạo Optimizer và Learning Rate Scheduler:
- Tách biệt trọng số (weight decay) không áp dụng lên LayerNorm, RMSNorm, Bias và Tied Embeddings.
- Hỗ trợ ủy quyền cho mô hình tự cấu hình (Model-Delegated Optimizer Pattern).
- Đảm bảo thứ tự tham số (deterministic parameter ordering) 100% để phục hồi checkpoint chính xác.
- Hỗ trợ đa dạng Optimizer: AdamW, SGD, 8-bit AdamW (bitsandbytes) với siêu tham số tùy biến qua config.
- Hỗ trợ đa dạng Scheduler: Cosine Annealing, Linear Decay, Constant kết hợp Linear Warmup và chống ZeroDivision.
"""

import math
from typing import Any, List

import torch
import torch.nn as nn

from src.core.config import TrainingConfig
from src.core.logging import get_logger

logger = get_logger("OptimizerFactory")


def configure_optimizer(
    model: nn.Module,
    config: TrainingConfig,
    *,
    optimizer_type: str | None = None,
) -> torch.optim.Optimizer:
    """
    Khởi tạo Optimizer tối ưu cho mô hình ngôn ngữ:
    1. Ưu tiên kiểm tra nếu mô hình có phương thức tự cấu hình `model.configure_optimizers(config)`.
    2. Nếu không, tự động phân loại tensor tham số:
       - 2D+ tensors (Linear weights, Embedding weights): Áp dụng Weight Decay.
       - 1D tensors (LayerNorm weights, RMSNorm weights, Biases): Loại bỏ Weight Decay (0.0).
    3. Bảo toàn 100% thứ tự duyệt tham số theo `model.named_parameters()` để checkpoint phục hồi chuẩn xác.
    """
    effective_config = (
        config.copy(optimizer_type=optimizer_type) if optimizer_type is not None else config
    )

    # 1. Model-Delegated Optimizer Pattern (chuẩn nanoGPT / PyTorch Lightning)
    if hasattr(model, "configure_optimizers") and callable(getattr(model, "configure_optimizers")):
        custom_optim = getattr(model, "configure_optimizers")(effective_config)
        if isinstance(custom_optim, torch.optim.Optimizer):
            logger.info(
                "Sử dụng optimizer được cấu hình tùy biến từ chính mô hình (Model Delegation)."
            )
            return custom_optim

    # 2. Phân loại tham số tiêu chuẩn theo số chiều tensor (không phụ thuộc string matching heuristic)
    decay: List[nn.Parameter] = []
    no_decay: List[nn.Parameter] = []
    seen = set()

    for pn, p in model.named_parameters():
        if not p.requires_grad:
            continue
        # Tránh xử lý trùng lặp tham số đã được chia sẻ (ví dụ: Weight Tying giữa lm_head và tok_embeddings)
        if id(p) in seen:
            continue
        seen.add(id(p))

        # Phân loại: Biases và 1D tensors (LayerNorm, RMSNorm scale/shift, Positional Embeddings 1D) không decay
        if p.ndim < 2 or pn.endswith(".bias") or pn.endswith("bias"):
            no_decay.append(p)
        else:
            decay.append(p)

    optim_groups = [
        {"params": decay, "weight_decay": effective_config.weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]

    opt_type = effective_config.optimizer_type.lower().strip()
    if opt_type == "sgd":
        return torch.optim.SGD(
            optim_groups,
            lr=effective_config.learning_rate,
            momentum=effective_config.sgd_momentum,
        )

    if opt_type == "8bit_adamw":
        try:
            import bitsandbytes as bnb  # type: ignore[import-untyped]

            bnb_adamw: Any = getattr(bnb.optim, "AdamW8bit", None)
            if bnb_adamw is not None:
                return bnb_adamw(
                    optim_groups,
                    lr=effective_config.learning_rate,
                    betas=(effective_config.adam_beta1, effective_config.adam_beta2),
                    eps=effective_config.adam_eps,
                )
        except ImportError as exc:
            raise RuntimeError(
                "8bit_adamw đã được chọn làm optimizer hiệu lực nhưng bitsandbytes không khả dụng. "
                "Hãy resolve runtime plan trước khi gọi configure_optimizer()."
            ) from exc
        raise RuntimeError("bitsandbytes không cung cấp bnb.optim.AdamW8bit như kỳ vọng.")

    # Mặc định sử dụng AdamW chuẩn
    return torch.optim.AdamW(
        optim_groups,
        lr=effective_config.learning_rate,
        betas=(effective_config.adam_beta1, effective_config.adam_beta2),
        eps=effective_config.adam_eps,
    )


def compute_scheduled_lr(step: int, config: TrainingConfig) -> float:
    """
    Tính toán Learning Rate tức thời theo chiến lược Warmup + Scheduler:
    - Warmup: Tuyến tính từ 0 đến learning_rate (nếu warmup_iters > 0).
    - Sau max_iters: Trả về min_lr.
    - Trong giai đoạn decay (tùy thuộc `config.lr_scheduler_type`):
      - "constant": Giữ nguyên learning_rate.
      - "linear": Giảm tuyến tính về min_lr.
      - "cosine": Giảm dần theo Cosine Annealing về min_lr (mặc định).
    - Guard triệt tiêu hoàn toàn nguy cơ ZeroDivisionError khi max_iters == warmup_iters.
    """
    # 1. Giai đoạn Linear Warmup. Short smoke/quick runs may intentionally
    # lower max_iters below the configured warmup; bound the effective warmup
    # to the run length instead of leaving the whole run at a tiny LR.
    effective_warmup = min(config.warmup_iters, config.max_iters)
    if effective_warmup > 0 and step < effective_warmup:
        return config.learning_rate * (step + 1) / effective_warmup

    # 2. Giai đoạn Decay. Training steps use zero-based update indices
    # [0, max_iters - 1], so the final optimizer update must already reach min_lr.
    scheduler_type = config.lr_scheduler_type.lower().strip()
    if scheduler_type == "constant":
        return config.learning_rate

    if effective_warmup < config.max_iters and step >= config.max_iters - 1:
        return config.min_lr

    # Preserve the public scheduler curve (which is defined over [0, max_iters])
    # for all interior points. The zero-based trainer loop has one fewer index, so
    # the final update is handled explicitly above instead of compressing the
    # entire decay curve and changing historical midpoint values.
    denom = max(1, config.max_iters - effective_warmup)
    decay_ratio = min(1.0, max(0.0, float(step - effective_warmup) / float(denom)))

    if scheduler_type == "linear":
        return config.min_lr + (1.0 - decay_ratio) * (config.learning_rate - config.min_lr)

    # Mặc định: Cosine Annealing Schedule
    coeff = 0.5 * (1.0 + math.cos(math.pi * decay_ratio))
    return config.min_lr + coeff * (config.learning_rate - config.min_lr)


__all__ = ["configure_optimizer", "compute_scheduled_lr"]
