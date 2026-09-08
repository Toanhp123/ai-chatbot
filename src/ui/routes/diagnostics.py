"""
Diagnostics API Routes: Lấy thông số hệ thống, phần cứng và tính toán ngân sách VRAM theo thời gian thực.
"""

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.config.model import ModelConfig
from src.core.config.training import TrainingConfig
from src.core.diagnostics.estimator import estimate_vram_budget
from src.core.diagnostics.hardware import (
    check_attention_backends,
    get_cpu_info,
    get_gpu_info,
    get_memory_info,
)
from src.core.diagnostics.storage import get_disk_info, verify_directory_permissions
from src.core.diagnostics.system import get_system_info

router = APIRouter(prefix="/api/diagnostics", tags=["Diagnostics"])


class VRAMEstimateRequest(BaseModel):
    model_name: str = Field(default="minigpt")
    batch_size: int = Field(default=64, ge=1, le=512)
    block_size: int = Field(default=128, ge=16, le=2048)
    n_embd: int = Field(default=192, ge=32, le=1024)
    n_layer: int = Field(default=4, ge=1, le=32)
    n_head: int = Field(default=6, ge=1, le=32)
    vocab_size: int = Field(default=129, ge=10, le=32000)
    precision: str = Field(default="float32")
    optimizer_type: str = Field(default="adamw")
    gradient_checkpointing: bool = Field(default=False)
    gradient_accumulation_steps: int = Field(default=1, ge=1, le=32)
    intermediate_size: Optional[int] = Field(default=None, ge=0)
    multiple_of: int = Field(default=64, ge=1)
    tie_word_embeddings: bool = Field(default=True)
    bias: bool = Field(default=False)


@router.get("/system")
async def get_system_diagnostics():
    """Thu thập thông số phần cứng hiện tại của máy tính."""
    cpu = get_cpu_info()
    mem = get_memory_info()
    gpu = get_gpu_info()
    sys_info = get_system_info()

    return {
        "cpu": cpu,
        "memory": mem,
        "gpu": gpu,
        "system": sys_info,
    }


@router.post("/estimate")
async def estimate_vram_endpoint(req: VRAMEstimateRequest):
    """Mô phỏng và tính toán chi tiết ngân sách bộ nhớ VRAM."""
    from src.core.config import EngineConfig
    from src.core.runtime import resolve_training_plan

    model_kwargs = {"multiple_of": req.multiple_of}
    if req.intermediate_size is not None:
        model_kwargs["intermediate_size"] = req.intermediate_size
    model_cfg = ModelConfig(
        name=req.model_name.strip().lower(),
        vocab_size=req.vocab_size,
        block_size=req.block_size,
        n_embd=req.n_embd,
        n_layer=req.n_layer,
        n_head=req.n_head,
        model_kwargs=model_kwargs,
        tie_word_embeddings=req.tie_word_embeddings,
        bias=req.bias,
    )
    training_cfg = TrainingConfig(
        batch_size=req.batch_size,
        precision=req.precision,
        optimizer_type=req.optimizer_type,
        gradient_checkpointing=req.gradient_checkpointing,
        gradient_accumulation_steps=req.gradient_accumulation_steps,
    )
    engine_cfg = EngineConfig(model=model_cfg, training=training_cfg)
    engine_cfg.validate()
    runtime_plan = resolve_training_plan(engine_cfg)

    budget = estimate_vram_budget(
        model_config=model_cfg,
        training_config=training_cfg,
        runtime_plan=runtime_plan,
    )

    # Làm phẳng dữ liệu cho UI tiêu thụ trực tiếp
    comps = budget.get("components_mb", {})
    budget["peak_vram_mb"] = budget.get("total_estimated_mb", 0.0)
    budget["peak_vram_gb"] = budget.get("total_estimated_gb", 0.0)
    budget["model_weights_mb"] = comps.get("parameters", 0.0)
    budget["gradients_mb"] = comps.get("gradients", 0.0)
    budget["optimizer_states_mb"] = comps.get("optimizer_states", 0.0)
    budget["activations_mb"] = comps.get("activations", 0.0)
    budget["cuda_overhead_mb"] = comps.get("cuda_context_overhead", 0.0)

    return budget


@router.post("/scenarios")
async def scenarios_endpoint(req: VRAMEstimateRequest):
    """Phân tích và so sánh đồng thời 4 kịch bản huấn luyện VRAM."""
    from src.core.diagnostics.estimator import analyze_vram_scenarios

    model_cfg = ModelConfig(
        name=req.model_name.strip().lower(),
        vocab_size=req.vocab_size,
        block_size=req.block_size,
        n_embd=req.n_embd,
        n_layer=req.n_layer,
        n_head=req.n_head,
        model_kwargs={
            "multiple_of": req.multiple_of,
            **(
                {"intermediate_size": req.intermediate_size}
                if req.intermediate_size is not None
                else {}
            ),
        },
        tie_word_embeddings=req.tie_word_embeddings,
        bias=req.bias,
    )
    training_cfg = TrainingConfig(
        batch_size=req.batch_size,
        gradient_accumulation_steps=req.gradient_accumulation_steps,
    )

    scenarios = analyze_vram_scenarios(
        model_config=model_cfg,
        training_config=training_cfg,
    )
    return scenarios


@router.get("/advisor")
async def get_hardware_advisor_endpoint():
    """Cố vấn cấu hình phần cứng tự động, kiểm tra nhân attention, phân quyền lưu trữ và trạng thái sức khỏe."""
    from src.core.diagnostics.runner import DiagnosticsRunner

    runner = DiagnosticsRunner()
    report = runner.run(test_tensor_allocation=True)
    gpu = get_gpu_info()
    backends = check_attention_backends()
    disk = get_disk_info(".")
    permissions = verify_directory_permissions(["logs", "checkpoints", "data", "configs"])

    return {
        "gpu": gpu,
        "backends": backends,
        "disk": disk,
        "permissions": permissions,
        "recommendations": gpu.get("recommendations", {}),
        "health_status": report.status.value,
        "warnings": report.warnings,
        "suggestions": report.suggestions,
    }


@router.post("/gates/run")
async def run_quality_gates_endpoint():
    """Chạy toàn diện 6 Quality Gates chuẩn Enterprise và trả về kết quả chi tiết."""
    import time

    from scripts.check_all import (
        run_architecture_gate,
        run_diagnostics_gate,
        run_format_gate,
        run_lint_gate,
        run_test_suite_gate,
        run_type_gate,
    )

    gates = [
        run_format_gate,
        run_lint_gate,
        run_type_gate,
        run_architecture_gate,
        run_diagnostics_gate,
        run_test_suite_gate,
    ]

    t0 = time.time()
    results = []
    for gate_fn in gates:
        res = gate_fn()
        results.append(res)
    total_elapsed = round(time.time() - t0, 2)
    all_passed = all(r.get("passed", False) for r in results)

    return {
        "all_passed": all_passed,
        "total_elapsed": total_elapsed,
        "results": results,
    }


@router.get("/inspect")
async def inspect_model_endpoint(
    config_path: str = "configs/truyen_kieu.yaml",
    model_name: Optional[str] = None,
    n_embd: Optional[int] = None,
    n_head: Optional[int] = None,
    n_layer: Optional[int] = None,
    block_size: Optional[int] = None,
):
    """Phân tích chi tiết kiến trúc mô hình và phân bổ tham số từng tầng."""
    from src.core.config import EngineConfig
    from src.models.registry import ModelRegistry

    config = EngineConfig.from_yaml(config_path)
    actual_model_name = (
        model_name.strip().lower() if model_name and model_name.strip() else config.model.name
    )
    model_overrides: Dict[str, Any] = {"name": actual_model_name}
    if n_embd is not None and n_embd > 0:
        model_overrides["n_embd"] = n_embd
    if n_head is not None and n_head > 0:
        model_overrides["n_head"] = n_head
    if n_layer is not None and n_layer > 0:
        model_overrides["n_layer"] = n_layer
    if block_size is not None and block_size > 0:
        model_overrides["block_size"] = block_size
    model_config = config.model.copy(**model_overrides)

    model = ModelRegistry.create(actual_model_name, model_config)

    layers_info = []
    total_params = 0
    for name, param in model.named_parameters():
        num_p = param.numel()
        total_params += num_p
        layers_info.append(
            {
                "name": name,
                "shape": list(param.shape),
                "params": num_p,
                "trainable": param.requires_grad,
                "memory_kb": round((num_p * param.element_size()) / 1024, 2),
            }
        )

    return {
        "model_name": actual_model_name,
        "total_parameters": total_params,
        "total_parameters_formatted": f"{total_params:,}",
        "vocab_size": model_config.vocab_size,
        "block_size": config.model.block_size,
        "n_embd": config.model.n_embd,
        "n_head": config.model.n_head,
        "n_layer": config.model.n_layer,
        "layers": layers_info[:35],  # Top 35 layers tiêu biểu
    }


@router.get("/logs")
async def get_system_logs_endpoint(lines: int = 80):
    """Lấy N dòng nhật ký hệ thống mới nhất từ logs/train.log hoặc logs/engine.log."""
    candidate_files = ["logs/train.log", "logs/engine.log"]
    log_file = None
    for cf in candidate_files:
        if os.path.exists(cf):
            log_file = cf
            break

    if not log_file and os.path.exists("logs"):
        logs_in_dir = [os.path.join("logs", f) for f in os.listdir("logs") if f.endswith(".log")]
        if logs_in_dir:
            logs_in_dir.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            log_file = logs_in_dir[0]

    if not log_file or not os.path.exists(log_file):
        return {
            "logs": [],
            "total_lines": 0,
            "file": "logs/train.log",
        }

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        tail = [line.rstrip() for line in all_lines[-lines:] if line.strip()]
        return {"logs": tail, "total_lines": len(all_lines), "file": log_file.replace("\\", "/")}
    except Exception as e:
        return {
            "logs": [f"Lỗi khi đọc file log: {e}"],
            "total_lines": 0,
            "file": log_file.replace("\\", "/"),
        }
