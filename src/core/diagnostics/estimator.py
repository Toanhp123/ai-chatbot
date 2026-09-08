"""Architecture-aware training memory estimator.

The estimator models the runtime that :class:`Trainer` actually executes.  It does
not instantiate model classes and therefore keeps the core -> model dependency
one-way; architecture parameter formulas are derived from the public ModelConfig
contract.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import EngineConfig, ModelConfig, SystemConfig, TrainingConfig
from src.core.diagnostics.hardware import get_gpu_info
from src.core.exceptions import ConfigurationError
from src.core.runtime import ResolvedTrainingPlan, resolve_training_plan


def calculate_approx_transformer_params(
    vocab_size: int,
    block_size: int,
    n_layer: int,
    n_head: int,
    n_embd: int,
    tie_word_embeddings: bool = True,
) -> int:
    """Backward-compatible exact MiniGPT parameter count for ``bias=False``."""
    del n_head  # retained for API compatibility; parameter count does not depend on head count.
    token_emb = vocab_size * n_embd
    pos_emb = block_size * n_embd
    head = 0 if tie_word_embeddings else vocab_size * n_embd
    # Attention 4*d^2 + GELU MLP 8*d^2 + two LayerNorms (4*d).
    per_block = 12 * (n_embd**2) + 4 * n_embd
    final_ln = 2 * n_embd
    return token_emb + pos_emb + n_layer * per_block + head + final_ln


def _llama_intermediate_size(config: ModelConfig) -> int:
    raw = int(config.model_kwargs.get("intermediate_size", 0))
    if raw > 0:
        return raw
    multiple_of = int(config.model_kwargs.get("multiple_of", 64))
    hidden = int(2 * 4 * config.n_embd / 3)
    return multiple_of * ((hidden + multiple_of - 1) // multiple_of)


def calculate_model_params(model_config: ModelConfig) -> int:
    """Return the exact trainable parameter count implied by a supported ModelConfig."""
    model_config.validate()
    name = model_config.name.lower().strip()
    d = model_config.n_embd
    vocab = model_config.vocab_size
    layers = model_config.n_layer
    bias = model_config.bias

    if name == "minigpt":
        total = calculate_approx_transformer_params(
            vocab_size=vocab,
            block_size=model_config.block_size,
            n_layer=layers,
            n_head=model_config.n_head,
            n_embd=d,
            tie_word_embeddings=model_config.tie_word_embeddings,
        )
        if bias:
            # Per block: attention biases 4*d + MLP biases 5*d.
            total += layers * 9 * d
            # Output head bias exists even when the weight matrix is tied.
            total += vocab
        return total

    if name in {"llama", "llama_nano"}:
        hidden = _llama_intermediate_size(model_config)
        token_embedding = vocab * d
        output_weight = 0 if model_config.tie_word_embeddings else vocab * d
        output_bias = vocab if bias else 0

        # Four attention projections + SwiGLU's three matrices + two RMSNorm vectors.
        per_block = 4 * (d**2) + 3 * d * hidden + 2 * d
        if bias:
            # Attention: 4*d. SwiGLU: hidden + d + hidden.
            per_block += 5 * d + 2 * hidden

        final_norm = d
        return token_embedding + layers * per_block + final_norm + output_weight + output_bias

    raise ConfigurationError(
        f"Estimator chưa có memory profile cho model architecture '{model_config.name}'.",
        {"model_name": model_config.name},
        suggestion="Đăng ký memory profile cho architecture trước khi chạy preflight VRAM.",
    )


def _effective_inputs(
    model_config: Optional[ModelConfig],
    training_config: Optional[TrainingConfig],
    *,
    vocab_size: int,
    precision: Optional[str],
    optimizer_type: Optional[str],
    gradient_accumulation_steps: Optional[int],
    gradient_checkpointing: Optional[bool],
    tie_word_embeddings: Optional[bool],
) -> Tuple[ModelConfig, TrainingConfig]:
    model = model_config or ModelConfig(vocab_size=vocab_size, n_embd=128, n_head=4)
    training = training_config or TrainingConfig(batch_size=32)

    model_overrides: Dict[str, Any] = {}
    if tie_word_embeddings is not None:
        model_overrides["tie_word_embeddings"] = tie_word_embeddings
    if model_overrides:
        model = model.copy(**model_overrides)
    else:
        model.validate()

    training_overrides: Dict[str, Any] = {}
    if precision is not None:
        training_overrides["precision"] = precision
    if optimizer_type is not None:
        training_overrides["optimizer_type"] = optimizer_type
    if gradient_accumulation_steps is not None:
        training_overrides["gradient_accumulation_steps"] = gradient_accumulation_steps
    if gradient_checkpointing is not None:
        training_overrides["gradient_checkpointing"] = gradient_checkpointing
    if training_overrides:
        training = training.copy(**training_overrides)
    else:
        training.validate()
    return model, training


def estimate_vram_budget(
    model_config: Optional[ModelConfig] = None,
    training_config: Optional[TrainingConfig] = None,
    vocab_size: int = 128,
    param_count: Optional[int] = None,
    precision: Optional[str] = None,
    optimizer_type: Optional[str] = None,
    gradient_accumulation_steps: Optional[int] = None,
    gradient_checkpointing: Optional[bool] = None,
    tie_word_embeddings: Optional[bool] = None,
    runtime_plan: Optional[ResolvedTrainingPlan] = None,
) -> Dict[str, Any]:
    """Estimate the memory budget for the same effective runtime used by Trainer."""
    model, training = _effective_inputs(
        model_config,
        training_config,
        vocab_size=vocab_size,
        precision=precision,
        optimizer_type=optimizer_type,
        gradient_accumulation_steps=gradient_accumulation_steps,
        gradient_checkpointing=gradient_checkpointing,
        tie_word_embeddings=tie_word_embeddings,
    )

    if runtime_plan is None:
        runtime_plan = resolve_training_plan(EngineConfig(model=model, training=training))

    total_params = param_count if param_count is not None else calculate_model_params(model)
    mb_divider = 1024 * 1024

    # Trainer keeps model/gradient tensors in FP32 and uses autocast for activations.
    parameter_bytes = 4
    gradient_bytes = 4
    activation_bytes = 2 if runtime_plan.use_amp else 4

    params_mb = round(total_params * parameter_bytes / mb_divider, 2)
    grads_mb = round(total_params * gradient_bytes / mb_divider, 2)

    if runtime_plan.optimizer_type == "8bit_adamw":
        optimizer_bytes = 2
    elif runtime_plan.optimizer_type == "sgd":
        # Momentum state is FP32; this intentionally overestimates when momentum is zero.
        optimizer_bytes = 4
    else:
        optimizer_bytes = 8
    optimizer_mb = round(total_params * optimizer_bytes / mb_divider, 2)

    micro_batch = runtime_plan.micro_batch_size
    base_act_bytes = (
        micro_batch * model.block_size * model.n_embd * model.n_layer * 16 * activation_bytes
    )
    if runtime_plan.gradient_checkpointing:
        act_factor = max(0.25, 1.0 / math.sqrt(model.n_layer))
        act_bytes = base_act_bytes * act_factor
    else:
        act_bytes = float(base_act_bytes)
    activations_mb = round(act_bytes / mb_divider, 2)

    cuda_overhead_mb = 450.0 if runtime_plan.device_type == "cuda" else 0.0
    total_mb = round(params_mb + grads_mb + optimizer_mb + activations_mb + cuda_overhead_mb, 2)
    total_gb = round(total_mb / 1024, 2)

    return {
        "total_parameters": total_params,
        "model_name": model.name,
        "requested_device": runtime_plan.requested_device,
        "device": runtime_plan.device,
        "requested_precision": runtime_plan.requested_precision,
        "precision": runtime_plan.precision,
        "requested_optimizer_type": runtime_plan.requested_optimizer,
        "optimizer_type": runtime_plan.optimizer_type,
        "fallback_reasons": list(runtime_plan.fallback_reasons),
        "batch_size": micro_batch,
        "micro_batch_size": micro_batch,
        "effective_batch_size": runtime_plan.effective_batch_size,
        "block_size": model.block_size,
        "gradient_accumulation_steps": runtime_plan.gradient_accumulation_steps,
        "gradient_checkpointing": runtime_plan.gradient_checkpointing,
        "tie_word_embeddings": model.tie_word_embeddings,
        "components_mb": {
            "parameters": params_mb,
            "gradients": grads_mb,
            "optimizer_states": optimizer_mb,
            "activations": activations_mb,
            "cuda_context_overhead": cuda_overhead_mb,
        },
        "total_estimated_mb": total_mb,
        "total_estimated_gb": total_gb,
    }


def analyze_vram_scenarios(
    model_config: Optional[ModelConfig] = None,
    training_config: Optional[TrainingConfig] = None,
    system_config: Optional[SystemConfig] = None,
    available_vram_gb: Optional[float] = None,
    safety_margin_gb: float = 0.5,
) -> Dict[str, Any]:
    """Compare common requested configurations against the current effective runtime."""
    model, training = _effective_inputs(
        model_config,
        training_config,
        vocab_size=128,
        precision=None,
        optimizer_type=None,
        gradient_accumulation_steps=None,
        gradient_checkpointing=None,
        tie_word_embeddings=None,
    )
    system = system_config or SystemConfig()
    system.validate()

    if available_vram_gb is None:
        gpu_data = get_gpu_info()
        primary_gpu = gpu_data.get("primary_gpu")
        available_vram_gb = float(primary_gpu.get("vram_free_gb", 0.0)) if primary_gpu else 0.0

    scenarios_def = [
        {
            "id": "fp32_baseline",
            "name": "1. Chuẩn FP32 (Baseline)",
            "precision": "float32",
            "optimizer": "adamw",
            "grad_checkpointing": False,
            "description": "Huấn luyện FP32 thuần không checkpointing.",
        },
        {
            "id": "amp_mixed",
            "name": "2. Mixed Precision (AMP FP16/BF16)",
            "precision": "amp_fp16",
            "optimizer": "adamw",
            "grad_checkpointing": False,
            "description": "Yêu cầu AMP FP16; runtime plan ghi rõ nếu phải fallback.",
        },
        {
            "id": "amp_grad_checkpointing",
            "name": "3. AMP + Gradient Checkpointing",
            "precision": "amp_fp16",
            "optimizer": "adamw",
            "grad_checkpointing": True,
            "description": "AMP kết hợp activation checkpointing.",
        },
        {
            "id": "amp_8bit_optimizer",
            "name": "4. AMP + Checkpointing + 8-bit AdamW",
            "precision": "amp_fp16",
            "optimizer": "8bit_adamw",
            "grad_checkpointing": True,
            "description": "Yêu cầu tối ưu 8-bit; runtime plan ghi rõ dependency fallback.",
        },
    ]

    results: List[Dict[str, Any]] = []
    for scenario in scenarios_def:
        scenario_training = training.copy(
            precision=scenario["precision"],
            optimizer_type=scenario["optimizer"],
            gradient_checkpointing=scenario["grad_checkpointing"],
        )
        runtime_plan = resolve_training_plan(
            EngineConfig(system=system, model=model, training=scenario_training)
        )
        budget = estimate_vram_budget(
            model_config=model,
            training_config=scenario_training,
            runtime_plan=runtime_plan,
        )
        est_gb = budget["total_estimated_gb"]
        uses_cuda = runtime_plan.device_type == "cuda"
        feasible = (
            available_vram_gb >= est_gb + safety_margin_gb
            if uses_cuda and available_vram_gb > 0
            else True
        )
        utilization_pct = (
            round(est_gb / available_vram_gb * 100, 1)
            if uses_cuda and available_vram_gb > 0
            else 0.0
        )
        results.append(
            {
                "id": scenario["id"],
                "name": scenario["name"],
                "description": scenario["description"],
                "precision": scenario["precision"],
                "effective_precision": budget["precision"],
                "optimizer": scenario["optimizer"],
                "effective_optimizer": budget["optimizer_type"],
                "effective_device": budget["device"],
                "fallback_reasons": budget["fallback_reasons"],
                "gradient_checkpointing": scenario["grad_checkpointing"],
                "batch_size": budget["micro_batch_size"],
                "estimated_mb": budget["total_estimated_mb"],
                "estimated_gb": est_gb,
                "feasible": feasible,
                "utilization_pct": utilization_pct,
                "components": budget["components_mb"],
            }
        )

    recommended = next((item for item in results if item["feasible"]), None)
    if recommended is None and results:
        recommended = results[-1]

    return {
        "available_vram_gb": available_vram_gb,
        "safety_margin_gb": safety_margin_gb,
        "scenarios": results,
        "recommended": recommended,
    }


def check_memory_feasibility(
    model_config: Optional[ModelConfig] = None,
    training_config: Optional[TrainingConfig] = None,
    available_vram_gb: Optional[float] = None,
    safety_margin_gb: float = 0.5,
    runtime_plan: Optional[ResolvedTrainingPlan] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Preflight VRAM using the same resolved runtime contract as Trainer."""
    budget = estimate_vram_budget(
        model_config=model_config,
        training_config=training_config,
        runtime_plan=runtime_plan,
    )
    estimated_gb = budget["total_estimated_gb"]

    if runtime_plan is not None and runtime_plan.device_type != "cuda":
        return (
            True,
            f"Runtime hiệu lực là {runtime_plan.device_type.upper()}, không áp dụng kiểm tra VRAM CUDA.",
            budget,
        )

    if available_vram_gb is None:
        gpu_data = get_gpu_info()
        primary_gpu = gpu_data.get("primary_gpu")
        if primary_gpu:
            available_vram_gb = float(primary_gpu.get("vram_free_gb", 0.0))
        else:
            return (
                True,
                "Runtime hiện không có GPU CUDA khả dụng; không áp dụng kiểm tra VRAM GPU.",
                budget,
            )

    required_with_margin = estimated_gb + safety_margin_gb
    is_feasible = available_vram_gb >= required_with_margin
    if not is_feasible:
        message = (
            f"CẢNH BÁO: Bộ nhớ VRAM ước tính ({estimated_gb} GB + {safety_margin_gb} GB margin) "
            f"vượt quá VRAM khả dụng hiện tại ({available_vram_gb} GB)! Nguy cơ cao gặp CUDA Out Of Memory. "
            "Khuyến nghị: giảm batch_size, bật gradient_checkpointing hoặc chọn precision phù hợp."
        )
    else:
        message = (
            f"VRAM khả dụng ({available_vram_gb} GB) đủ an toàn cho ngân sách huấn luyện ước tính "
            f"({estimated_gb} GB)."
        )
    return is_feasible, message, budget


__all__ = [
    "calculate_approx_transformer_params",
    "calculate_model_params",
    "estimate_vram_budget",
    "analyze_vram_scenarios",
    "check_memory_feasibility",
]
