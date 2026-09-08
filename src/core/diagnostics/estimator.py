"""
Bộ ước tính Ngân sách VRAM (Model VRAM Budget Estimator Pro):
- Tính toán ước lượng bộ nhớ VRAM chuẩn xác cho mô hình Transformer
- Bóc tách chi tiết: Tham số (Parameters), Gradients, Trạng thái Optimizer (AdamW FP32/8-bit),
  Activations (chuẩn và Gradient Checkpointing) và CUDA Overhead
- Hỗ trợ Weight Tying, Mixed Precision (AMP FP16/BF16), Gradient Accumulation
- Phân tích đa kịch bản (Multi-Scenario Analysis) và tự động đề xuất cấu hình an toàn nhất
- Cảnh báo rủi ro Out Of Memory (OOM) trước khi bắt đầu huấn luyện thực tế
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from src.core.config.model import ModelConfig
from src.core.config.training import TrainingConfig
from src.core.diagnostics.hardware import get_gpu_info


def calculate_approx_transformer_params(
    vocab_size: int,
    block_size: int,
    n_layer: int,
    n_head: int,
    n_embd: int,
    tie_word_embeddings: bool = True,
) -> int:
    """Ước tính số lượng tham số lý thuyết của mô hình Transformer kiến trúc Decoder-Only.

    Nếu tie_word_embeddings=True (mặc định cho MiniGPT), trọng số của lm_head chia sẻ
    hoàn toàn với token embedding (wte) nên không làm tăng thêm số tham số.
    """
    token_emb = vocab_size * n_embd
    pos_emb = block_size * n_embd
    # Khi dùng weight tying, lm_head tái sử dụng ma trận wte
    head = 0 if tie_word_embeddings else (vocab_size * n_embd)

    # Mỗi Transformer Block gồm: Multi-Head Attention (4 * d^2) + MLP (8 * d^2) + LayerNorms
    per_block = (4 * (n_embd**2)) + (8 * (n_embd**2)) + (4 * n_embd)
    total_blocks = n_layer * per_block

    return token_emb + pos_emb + total_blocks + head + (2 * n_embd)


def estimate_vram_budget(
    model_config: Optional[ModelConfig] = None,
    training_config: Optional[TrainingConfig] = None,
    vocab_size: int = 128,
    param_count: Optional[int] = None,
    precision: str = "float32",
    optimizer_type: str = "adamw",
    gradient_accumulation_steps: int = 1,
    gradient_checkpointing: bool = False,
    tie_word_embeddings: bool = True,
) -> Dict[str, Any]:
    """Tính toán chi tiết ngân sách bộ nhớ GPU (MB và GB) cho quá trình huấn luyện.

    Hỗ trợ các chế độ:
    - precision: 'float32', 'float16', 'bfloat16', 'amp_fp16', 'amp_bf16'
    - optimizer_type: 'adamw' (FP32), '8bit_adamw' (bitsandbytes)
    - gradient_accumulation_steps: giảm micro_batch_size
    - gradient_checkpointing: giảm 70% bộ nhớ activations
    - tie_word_embeddings: trừ số tham số trùng lặp
    """
    # Lấy thông số từ ModelConfig hoặc mặc định
    if model_config is not None:
        vocab_size = getattr(model_config, "vocab_size", vocab_size) or vocab_size
        block_size = model_config.block_size
        n_layer = model_config.n_layer
        n_head = model_config.n_head
        n_embd = model_config.n_embd
    else:
        block_size = 128
        n_layer = 4
        n_head = 4
        n_embd = 128

    # Lấy thông số từ TrainingConfig hoặc mặc định
    batch_size = training_config.batch_size if training_config is not None else 32

    # 1. Tính số tham số
    if param_count is None:
        total_params = calculate_approx_transformer_params(
            vocab_size=vocab_size,
            block_size=block_size,
            n_layer=n_layer,
            n_head=n_head,
            n_embd=n_embd,
            tie_word_embeddings=tie_word_embeddings,
        )
    else:
        total_params = param_count

    mb_divider = 1024 * 1024
    is_mixed = precision in ("float16", "bfloat16", "amp_fp16", "amp_bf16")

    # 2. Bộ nhớ trọng số mô hình (Parameters)
    bytes_per_param = 2 if is_mixed else 4
    params_mb = round((total_params * bytes_per_param) / mb_divider, 2)

    # 3. Bộ nhớ Gradients
    grads_bytes_per_param = 2 if is_mixed else 4
    grads_mb = round((total_params * grads_bytes_per_param) / mb_divider, 2)

    # 4. Bộ nhớ Trạng thái Optimizer
    # Mixed precision cần thêm 4 bytes Master Weights (FP32)
    master_weights_mb = round((total_params * 4) / mb_divider, 2) if is_mixed else 0.0

    if optimizer_type in ("8bit_adamw", "8bit"):
        # 8-bit AdamW chỉ tốn 1 byte cho m và 1 byte cho v = 2 bytes/param
        opt_states_mb = round((total_params * 2) / mb_divider, 2)
    else:
        # AdamW chuẩn lưu m và v ở FP32 = 8 bytes/param
        opt_states_mb = round((total_params * 8) / mb_divider, 2)

    total_optimizer_mb = round(master_weights_mb + opt_states_mb, 2)

    # 5. Bộ nhớ Activations
    # Tính micro_batch_size khi có Gradient Accumulation
    grad_acc_steps = max(1, gradient_accumulation_steps)
    micro_batch = max(1, batch_size // grad_acc_steps)

    # Xấp xỉ activation memory: micro_batch * seq_len * n_embd * n_layer * factor * bytes
    base_act_bytes = micro_batch * block_size * n_embd * n_layer * 16 * bytes_per_param
    if gradient_checkpointing:
        # Gradient Checkpointing chỉ lưu activations ở ranh giới giữa các block (tiết kiệm ~70%)
        act_factor = max(0.25, 1.0 / math.sqrt(n_layer))
        act_bytes = base_act_bytes * act_factor
    else:
        act_bytes = float(base_act_bytes)

    activations_mb = round(act_bytes / mb_divider, 2)

    # 6. Overhead cố định của PyTorch CUDA Driver Context
    cuda_overhead_mb = 450.0

    total_mb = round(
        params_mb + grads_mb + total_optimizer_mb + activations_mb + cuda_overhead_mb, 2
    )
    total_gb = round(total_mb / 1024, 2)

    return {
        "total_parameters": total_params,
        "precision": precision,
        "optimizer_type": optimizer_type,
        "batch_size": batch_size,
        "micro_batch_size": micro_batch,
        "block_size": block_size,
        "gradient_accumulation_steps": grad_acc_steps,
        "gradient_checkpointing": gradient_checkpointing,
        "tie_word_embeddings": tie_word_embeddings,
        "components_mb": {
            "parameters": params_mb,
            "gradients": grads_mb,
            "optimizer_states": total_optimizer_mb,
            "activations": activations_mb,
            "cuda_context_overhead": cuda_overhead_mb,
        },
        "total_estimated_mb": total_mb,
        "total_estimated_gb": total_gb,
    }


def analyze_vram_scenarios(
    model_config: Optional[ModelConfig] = None,
    training_config: Optional[TrainingConfig] = None,
    available_vram_gb: Optional[float] = None,
    safety_margin_gb: float = 0.5,
) -> Dict[str, Any]:
    """Phân tích 4 kịch bản huấn luyện chính và tự động đề xuất kịch bản tối ưu nhất."""
    if available_vram_gb is None:
        gpu_data = get_gpu_info()
        primary_gpu = gpu_data.get("primary_gpu")
        if primary_gpu:
            available_vram_gb = float(primary_gpu.get("vram_free_gb", 0.0))
        else:
            available_vram_gb = 0.0

    scenarios_def = [
        {
            "id": "fp32_baseline",
            "name": "1. Chuẩn FP32 (Baseline)",
            "precision": "float32",
            "optimizer": "adamw",
            "grad_checkpointing": False,
            "description": "Huấn luyện FP32 thuần không checkpointing (tốc độ cao nhất, ngốn VRAM nhất)",
        },
        {
            "id": "amp_mixed",
            "name": "2. Mixed Precision (AMP FP16/BF16)",
            "precision": "float16",
            "optimizer": "adamw",
            "grad_checkpointing": False,
            "description": "Bật AMP FP16/BF16 (tiết kiệm 50% Activation, tăng tốc tính toán)",
        },
        {
            "id": "amp_grad_checkpointing",
            "name": "3. AMP + Gradient Checkpointing",
            "precision": "float16",
            "optimizer": "adamw",
            "grad_checkpointing": True,
            "description": "Bật AMP và Gradient Checkpointing (giảm 70% Activation, đổi ~25% tốc độ)",
        },
        {
            "id": "amp_8bit_optimizer",
            "name": "4. AMP + Checkpointing + 8-bit AdamW",
            "precision": "float16",
            "optimizer": "8bit_adamw",
            "grad_checkpointing": True,
            "description": "Tối ưu hóa tối đa (tiết kiệm cả Activation và 75% Optimizer States)",
        },
    ]

    scenarios_results: List[Dict[str, Any]] = []
    recommended_scenario = None

    for sc in scenarios_def:
        budget = estimate_vram_budget(
            model_config=model_config,
            training_config=training_config,
            precision=sc["precision"],
            optimizer_type=sc["optimizer"],
            gradient_checkpointing=sc["grad_checkpointing"],
        )
        est_gb = budget["total_estimated_gb"]
        required_with_margin = est_gb + safety_margin_gb
        feasible = available_vram_gb >= required_with_margin if available_vram_gb > 0 else True
        utilization_pct = (
            round((est_gb / available_vram_gb) * 100, 1) if available_vram_gb > 0 else 0.0
        )

        item = {
            "id": sc["id"],
            "name": sc["name"],
            "description": sc["description"],
            "precision": sc["precision"],
            "optimizer": sc["optimizer"],
            "gradient_checkpointing": sc["grad_checkpointing"],
            "estimated_mb": budget["total_estimated_mb"],
            "estimated_gb": est_gb,
            "feasible": feasible,
            "utilization_pct": utilization_pct,
            "components": budget["components_mb"],
        }
        scenarios_results.append(item)

    # Thuật toán Auto-Recommendation: Chọn kịch bản nhanh nhất mà vẫn khả thi an toàn
    for item in scenarios_results:
        if item["feasible"]:
            recommended_scenario = item
            break

    if recommended_scenario is None and scenarios_results:
        recommended_scenario = scenarios_results[-1]  # Chọn kịch bản tiết kiệm nhất

    return {
        "available_vram_gb": available_vram_gb,
        "safety_margin_gb": safety_margin_gb,
        "scenarios": scenarios_results,
        "recommended": recommended_scenario,
    }


def check_memory_feasibility(
    model_config: Optional[ModelConfig] = None,
    training_config: Optional[TrainingConfig] = None,
    available_vram_gb: Optional[float] = None,
    safety_margin_gb: float = 0.5,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Kiểm tra tính khả thi của bộ nhớ trước khi huấn luyện để chủ động phòng tránh lỗi OOM."""
    budget = estimate_vram_budget(model_config=model_config, training_config=training_config)
    estimated_gb = budget["total_estimated_gb"]

    if available_vram_gb is None:
        gpu_data = get_gpu_info()
        primary_gpu = gpu_data.get("primary_gpu")
        if primary_gpu:
            available_vram_gb = primary_gpu.get("vram_free_gb", 0.0)
        else:
            return True, "Chạy trên CPU, không áp dụng kiểm tra VRAM GPU.", budget

    required_with_margin = estimated_gb + safety_margin_gb
    is_feasible = available_vram_gb >= required_with_margin

    if not is_feasible:
        message = (
            f"CẢNH BÁO: Bộ nhớ VRAM ước tính ({estimated_gb} GB + {safety_margin_gb} GB margin) "
            f"vượt quá VRAM khả dụng hiện tại ({available_vram_gb} GB)! Nguy cơ cao gặp CUDA Out Of Memory. "
            "Khuyến nghị: Hãy giảm 'batch_size', bật 'gradient_checkpointing' hoặc dùng Mixed Precision."
        )
    else:
        message = (
            f"VRAM khả dụng ({available_vram_gb} GB) đủ an toàn cho ngân sách huấn luyện ước tính "
            f"({estimated_gb} GB)."
        )

    return is_feasible, message, budget
