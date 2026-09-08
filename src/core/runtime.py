"""Resolve requested engine configuration into one effective training runtime plan."""

from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

import torch

from src.core.config import EngineConfig
from src.core.exceptions import ConfigurationError, CudaUnavailableError, HardwareError


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Runtime features that may change requested training semantics."""

    cuda_available: bool
    mps_available: bool
    bf16_supported: bool
    bitsandbytes_available: bool


@dataclass(frozen=True)
class ResolvedTrainingPlan:
    """Single source of truth for the runtime the trainer will actually execute."""

    requested_device: str
    device: str
    device_type: str
    requested_precision: str
    precision: str
    use_amp: bool
    requested_optimizer: str
    optimizer_type: str
    micro_batch_size: int
    gradient_accumulation_steps: int
    effective_batch_size: int
    gradient_checkpointing: bool
    fallback_reasons: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _mps_available() -> bool:
    mps = getattr(torch.backends, "mps", None)
    is_available = getattr(mps, "is_available", None)
    return bool(callable(is_available) and is_available())


def detect_runtime_capabilities() -> RuntimeCapabilities:
    """Inspect optional accelerator/runtime dependencies once for planning."""
    cuda_available = bool(torch.cuda.is_available())
    bf16_supported = False
    if cuda_available:
        try:
            is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
            if callable(is_bf16_supported):
                bf16_supported = bool(is_bf16_supported())
        except Exception:
            bf16_supported = False
    return RuntimeCapabilities(
        cuda_available=cuda_available,
        mps_available=_mps_available(),
        bf16_supported=bf16_supported,
        bitsandbytes_available=importlib.util.find_spec("bitsandbytes") is not None,
    )


def _resolve_device(requested: str, capabilities: RuntimeCapabilities) -> str:
    if requested == "auto":
        if capabilities.cuda_available:
            return "cuda"
        if capabilities.mps_available:
            return "mps"
        return "cpu"
    if requested == "cuda":
        if not capabilities.cuda_available:
            raise CudaUnavailableError(
                "Cấu hình yêu cầu CUDA nhưng runtime hiện tại không có CUDA khả dụng."
            )
        return "cuda"
    if requested == "mps":
        if not capabilities.mps_available:
            raise HardwareError(
                "Cấu hình yêu cầu MPS nhưng runtime hiện tại không có MPS khả dụng.",
                details={"device": "mps"},
                suggestion="Chuyển system.device sang 'auto' hoặc 'cpu' trên máy không hỗ trợ MPS.",
            )
        return "mps"
    return "cpu"


def resolve_training_plan(
    config: EngineConfig,
    capabilities: Optional[RuntimeCapabilities] = None,
    device_override: Optional[str] = None,
) -> ResolvedTrainingPlan:
    """Resolve config plus runtime capabilities into deterministic effective behavior."""
    config.validate()
    caps = capabilities or detect_runtime_capabilities()
    requested_device = (device_override or config.system.device).lower().strip()
    if requested_device not in {"auto", "cuda", "mps", "cpu"}:
        raise HardwareError(
            f"Thiết bị runtime không hợp lệ: {requested_device!r}",
            details={"device": requested_device},
        )
    device = _resolve_device(requested_device, caps)
    device_type = "cuda" if device.startswith("cuda") else ("mps" if device == "mps" else "cpu")

    fallback_reasons = []
    requested_precision = config.training.precision.lower().strip()
    precision = requested_precision
    use_amp = False
    if device_type != "cuda" and requested_precision != "float32":
        precision = "float32"
        fallback_reasons.append(
            f"Precision '{requested_precision}' không được runtime trainer hỗ trợ trên {device_type}; dùng float32."
        )
    elif device_type == "cuda":
        if requested_precision in {"float16", "amp_fp16"}:
            use_amp = True
        elif requested_precision in {"bfloat16", "amp_bf16"}:
            if caps.bf16_supported:
                use_amp = True
            else:
                precision = "float32"
                fallback_reasons.append(
                    f"Precision '{requested_precision}' yêu cầu BF16 CUDA nhưng phần cứng không hỗ trợ; dùng float32."
                )

    requested_optimizer = config.training.optimizer_type.lower().strip()
    optimizer_type = requested_optimizer
    if requested_optimizer == "8bit_adamw":
        if device_type != "cuda":
            optimizer_type = "adamw"
            fallback_reasons.append(
                "Optimizer 8bit_adamw chỉ được chọn cho runtime CUDA; dùng AdamW chuẩn."
            )
        elif not caps.bitsandbytes_available:
            optimizer_type = "adamw"
            fallback_reasons.append(
                "bitsandbytes không khả dụng nên 8bit_adamw được resolve thành AdamW chuẩn."
            )

    micro_batch_size = config.training.batch_size
    accumulation = config.training.gradient_accumulation_steps

    return ResolvedTrainingPlan(
        requested_device=requested_device,
        device=device,
        device_type=device_type,
        requested_precision=requested_precision,
        precision=precision,
        use_amp=use_amp,
        requested_optimizer=requested_optimizer,
        optimizer_type=optimizer_type,
        micro_batch_size=micro_batch_size,
        gradient_accumulation_steps=accumulation,
        effective_batch_size=micro_batch_size * accumulation,
        gradient_checkpointing=bool(config.training.gradient_checkpointing),
        fallback_reasons=tuple(fallback_reasons),
    )


def validate_training_plan(config: EngineConfig, plan: ResolvedTrainingPlan) -> None:
    """Reject a resolved plan that no longer matches its runtime-affecting config."""
    config.validate()
    expected = {
        "requested_device": config.system.device.lower().strip(),
        "requested_precision": config.training.precision.lower().strip(),
        "requested_optimizer": config.training.optimizer_type.lower().strip(),
        "micro_batch_size": config.training.batch_size,
        "gradient_accumulation_steps": config.training.gradient_accumulation_steps,
        "gradient_checkpointing": bool(config.training.gradient_checkpointing),
    }
    actual = {
        "requested_device": plan.requested_device,
        "requested_precision": plan.requested_precision,
        "requested_optimizer": plan.requested_optimizer,
        "micro_batch_size": plan.micro_batch_size,
        "gradient_accumulation_steps": plan.gradient_accumulation_steps,
        "gradient_checkpointing": plan.gradient_checkpointing,
    }
    mismatches = {
        key: {"expected": expected[key], "actual": actual[key]}
        for key in expected
        if expected[key] != actual[key]
    }
    if mismatches:
        raise ConfigurationError(
            "Resolved runtime plan không còn khớp với cấu hình huấn luyện hiện tại.",
            details={"mismatches": mismatches},
            suggestion="Resolve lại runtime plan sau mọi thay đổi cấu hình ảnh hưởng runtime.",
        )


__all__ = [
    "RuntimeCapabilities",
    "ResolvedTrainingPlan",
    "detect_runtime_capabilities",
    "resolve_training_plan",
    "validate_training_plan",
]
