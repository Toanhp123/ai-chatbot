"""
Training API Routes: Bắt đầu, dừng và truyền dữ liệu biểu đồ huấn luyện thời gian thực qua SSE.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.exceptions import AIEngineError

router = APIRouter(prefix="/api/training", tags=["Training"])


class StartTrainingRequest(BaseModel):
    config_path: str = Field(
        default="configs/truyen_kieu.yaml", description="Đường dẫn file cấu hình YAML"
    )
    quick_check: bool = Field(
        default=False, description="Chạy thử nghiệm 50 bước kiểm tra pipeline"
    )
    batch_size: Optional[int] = Field(default=None, description="Ghi đè batch size")
    learning_rate: Optional[float] = Field(default=None, description="Ghi đè learning rate")
    max_iters: Optional[int] = Field(default=None, description="Ghi đè số bước tối đa")
    precision: Optional[str] = Field(
        default=None, description="Độ chính xác: float32, amp_fp16, amp_bf16"
    )
    optimizer_type: Optional[str] = Field(
        default=None, description="Loại optimizer: adamw, 8bit_adamw, sgd"
    )
    gradient_accumulation_steps: Optional[int] = Field(
        default=None, description="Số bước tích lũy gradient"
    )
    resume_checkpoint: Optional[str] = Field(
        default=None, description="Đường dẫn file checkpoint để tiếp tục huấn luyện"
    )
    run_name: Optional[str] = Field(
        default=None, description="Tên phiên huấn luyện (prefix đặt tên checkpoint)"
    )
    save_top_k: Optional[int] = Field(
        default=None, description="Số lượng checkpoint tốt nhất cần lưu giữ"
    )
    model_name: Optional[str] = Field(
        default=None, description="Tên kiến trúc mô hình: minigpt hoặc llama"
    )
    lr_scheduler_type: Optional[str] = Field(
        default=None, description="Loại scheduler: cosine, linear, constant"
    )
    warmup_iters: Optional[int] = Field(default=None, description="Số bước khởi động warmup")
    min_lr: Optional[float] = Field(default=None, description="Tốc độ học tối thiểu")
    weight_decay: Optional[float] = Field(default=None, description="Hệ số suy giảm trọng số")
    grad_clip: Optional[float] = Field(default=None, description="Ngưỡng cắt tỉa gradient")
    early_stopping_patience: Optional[int] = Field(
        default=None, description="Số lần eval không cải thiện trước khi dừng sớm"
    )
    cleaner_type: Optional[str] = Field(
        default=None, description="Loại cleaner dữ liệu: default, gemini, passthrough"
    )
    tokenizer_type: Optional[str] = Field(
        default=None, description="Loại tokenizer: char, byte; gemini là alias legacy của byte"
    )
    gradient_checkpointing: Optional[bool] = Field(
        default=None, description="Bật gradient checkpointing (giảm 70% VRAM)"
    )
    eval_interval: Optional[int] = Field(default=None, description="Chu kỳ bước đánh giá loss")
    eval_iters: Optional[int] = Field(default=None, description="Số batch lấy mẫu khi đánh giá")
    save_last: Optional[bool] = Field(
        default=None, description="Lưu checkpoint cuối cùng last_model.pt"
    )
    split_ratio: Optional[float] = Field(
        default=None, description="Tỉ lệ chia tập train/val (0.0 - 1.0)"
    )
    batch_provider_type: Optional[str] = Field(
        default=None, description="Loại batch provider: tensor hoặc dataloader"
    )
    n_layer: Optional[int] = Field(default=None, description="Số tầng Transformer")
    n_embd: Optional[int] = Field(default=None, description="Kích thước vector embedding")
    n_head: Optional[int] = Field(default=None, description="Số attention heads")
    dropout: Optional[float] = Field(default=None, description="Hệ số dropout chống overfitting")
    block_size: Optional[int] = Field(
        default=None, description="Độ dài ngữ cảnh tối đa (context window)"
    )
    seed: Optional[int] = Field(default=None, description="Hạt giống ngẫu nhiên (seed)")


class CheckFeasibilityRequest(BaseModel):
    config_path: str = Field(default="configs/truyen_kieu.yaml")
    batch_size: Optional[int] = None
    precision: Optional[str] = None
    optimizer_type: Optional[str] = None
    gradient_checkpointing: Optional[bool] = None
    gradient_accumulation_steps: Optional[int] = None
    model_name: Optional[str] = None
    n_layer: Optional[int] = None
    n_embd: Optional[int] = None
    n_head: Optional[int] = None
    block_size: Optional[int] = None


@router.post("/check-feasibility")
async def check_feasibility_endpoint(req: CheckFeasibilityRequest):
    """Kiểm tra tính khả thi của bộ nhớ VRAM trước khi huấn luyện để chủ động phòng tránh lỗi OOM."""
    from src.core.config import EngineConfig
    from src.core.diagnostics.estimator import check_memory_feasibility
    from src.core.runtime import resolve_training_plan

    overrides = []
    if req.batch_size is not None:
        overrides.append(f"training.batch_size={req.batch_size}")
    if req.precision:
        overrides.append(f"training.precision={req.precision}")
    if req.optimizer_type:
        overrides.append(f"training.optimizer_type={req.optimizer_type}")
    if req.gradient_checkpointing is not None:
        overrides.append(f"training.gradient_checkpointing={req.gradient_checkpointing}")
    if req.gradient_accumulation_steps is not None:
        overrides.append(f"training.gradient_accumulation_steps={req.gradient_accumulation_steps}")
    if req.model_name:
        overrides.append(f"model.name={req.model_name.strip().lower()}")
    if req.n_layer is not None:
        overrides.append(f"model.n_layer={req.n_layer}")
    if req.n_embd is not None:
        overrides.append(f"model.n_embd={req.n_embd}")
    if req.n_head is not None:
        overrides.append(f"model.n_head={req.n_head}")
    if req.block_size is not None:
        overrides.append(f"model.block_size={req.block_size}")

    config = EngineConfig.from_yaml(req.config_path, overrides=overrides if overrides else None)
    runtime_plan = resolve_training_plan(config)
    feasible, msg, budget = check_memory_feasibility(
        model_config=config.model,
        training_config=config.training,
        runtime_plan=runtime_plan,
    )

    return {
        "feasible": feasible,
        "message": msg,
        "estimated_gb": budget.get("total_estimated_gb", 0.0),
        "estimated_mb": budget.get("total_estimated_mb", 0.0),
    }


@router.post("/start")
async def start_training_endpoint(req: StartTrainingRequest, request: Request):
    """Khởi chạy phiên huấn luyện nền."""
    training_service = request.app.state.training_service

    overrides: List[str] = []
    if req.model_name is not None and req.model_name.strip():
        overrides.append(f"model.name={req.model_name.strip().lower()}")
    if req.cleaner_type is not None and req.cleaner_type.strip():
        overrides.append(f"data.cleaner_type={req.cleaner_type.strip().lower()}")
    if req.tokenizer_type is not None and req.tokenizer_type.strip():
        overrides.append(f"data.tokenizer_type={req.tokenizer_type.strip().lower()}")
    if req.batch_size is not None:
        overrides.append(f"training.batch_size={req.batch_size}")
    if req.learning_rate is not None:
        overrides.append(f"training.learning_rate={req.learning_rate}")
    if req.max_iters is not None:
        overrides.append(f"training.max_iters={req.max_iters}")
    if req.precision is not None:
        overrides.append(f"training.precision={req.precision}")
    if req.optimizer_type is not None:
        overrides.append(f"training.optimizer_type={req.optimizer_type}")
    if req.gradient_accumulation_steps is not None:
        overrides.append(f"training.gradient_accumulation_steps={req.gradient_accumulation_steps}")
    if req.gradient_checkpointing is not None:
        overrides.append(f"training.gradient_checkpointing={req.gradient_checkpointing}")
    if req.eval_interval is not None:
        overrides.append(f"training.eval_interval={req.eval_interval}")
    if req.eval_iters is not None:
        overrides.append(f"training.eval_iters={req.eval_iters}")
    if req.save_last is not None:
        overrides.append(f"training.save_last={req.save_last}")
    if req.split_ratio is not None:
        overrides.append(f"data.split_ratio={req.split_ratio}")
    if req.batch_provider_type is not None and req.batch_provider_type.strip():
        overrides.append(f"data.batch_provider_type={req.batch_provider_type.strip().lower()}")
    if req.n_layer is not None:
        overrides.append(f"model.n_layer={req.n_layer}")
    if req.n_embd is not None:
        overrides.append(f"model.n_embd={req.n_embd}")
    if req.n_head is not None:
        overrides.append(f"model.n_head={req.n_head}")
    if req.dropout is not None:
        overrides.append(f"model.dropout={req.dropout}")
    if req.lr_scheduler_type is not None and req.lr_scheduler_type.strip():
        overrides.append(f"training.lr_scheduler_type={req.lr_scheduler_type.strip().lower()}")
    if req.warmup_iters is not None:
        overrides.append(f"training.warmup_iters={req.warmup_iters}")
    if req.min_lr is not None:
        overrides.append(f"training.min_lr={req.min_lr}")
    if req.weight_decay is not None:
        overrides.append(f"training.weight_decay={req.weight_decay}")
    if req.grad_clip is not None:
        overrides.append(f"training.grad_clip={req.grad_clip}")
    if req.early_stopping_patience is not None:
        overrides.append(f"training.early_stopping_patience={req.early_stopping_patience}")
    import time

    if req.run_name is not None and req.run_name.strip():
        overrides.append(f"training.run_name={req.run_name.strip()}")
    else:
        auto_run_name = f"kieu_{time.strftime('%Y%m%d_%H%M%S')}"
        overrides.append(f"training.run_name={auto_run_name}")
    if req.save_top_k is not None:
        overrides.append(f"training.save_top_k={req.save_top_k}")
    if req.block_size is not None:
        overrides.append(f"model.block_size={req.block_size}")
    if req.seed is not None:
        overrides.append(f"system.seed={req.seed}")

    if req.resume_checkpoint:
        import os

        if not os.path.exists(req.resume_checkpoint):
            raise HTTPException(
                status_code=400,
                detail=f"Không tìm thấy file checkpoint để resume: '{req.resume_checkpoint}'",
            )

    # Pre-flight Memory Feasibility Check
    from src.core.config import EngineConfig
    from src.core.diagnostics.estimator import check_memory_feasibility
    from src.core.runtime import resolve_training_plan

    chk_config = EngineConfig.from_yaml(req.config_path, overrides=overrides if overrides else None)
    runtime_plan = resolve_training_plan(chk_config)
    feasible, mem_msg, budget = check_memory_feasibility(
        model_config=chk_config.model,
        training_config=chk_config.training,
        runtime_plan=runtime_plan,
    )

    try:
        training_service.start_training(
            config_path=req.config_path,
            overrides=overrides if overrides else None,
            quick_check=req.quick_check,
            resume_checkpoint=req.resume_checkpoint,
            runtime_plan=runtime_plan,
        )
        request.app.state.inference_service.set_checkpoint_dir(chk_config.training.checkpoint_dir)
        request.app.state.inference_service.set_vocab_path(chk_config.data.vocab_file)
        return {
            "status": "success",
            "message": "Đã khởi chạy huấn luyện trên luồng nền.",
            "preflight": {
                "feasible": feasible,
                "message": mem_msg,
                "estimated_gb": budget.get("total_estimated_gb", 0.0),
            },
            "state": training_service.get_state(),
        }
    except AIEngineError:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop_training_endpoint(request: Request):
    """Yêu cầu ngắt huấn luyện an toàn."""
    training_service = request.app.state.training_service
    training_service.stop_training()
    return {"status": "success", "message": "Đã gửi tín hiệu dừng huấn luyện an toàn."}


@router.post("/clear")
async def clear_training_endpoint(request: Request):
    """Xóa sạch thông tin số liệu và biểu đồ huấn luyện, đặt lại trạng thái IDLE."""
    training_service = request.app.state.training_service
    try:
        training_service.clear_state()
        return {"status": "success", "message": "Đã làm mới thông tin huấn luyện."}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def get_training_status_endpoint(request: Request):
    """Lấy trạng thái và các mẫu văn bản mới nhất."""
    training_service = request.app.state.training_service
    return training_service.get_state()


@router.get("/stream")
async def stream_training_metrics_endpoint(request: Request):
    """Kênh phát sóng số đo loss và sample preview theo thời gian thực (SSE)."""
    training_service = request.app.state.training_service
    return StreamingResponse(
        training_service.stream_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
