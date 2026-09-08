"""
Training API Routes: Bắt đầu, dừng và truyền dữ liệu biểu đồ huấn luyện thời gian thực qua SSE.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.core.exceptions import AIEngineError
from src.ui.path_policy import resolve_path_within_root

router = APIRouter(prefix="/api/training", tags=["Training"])


def _resolve_training_config_path(path: str) -> str:
    try:
        return resolve_path_within_root(path, "configs")
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Chỉ cho phép dùng file cấu hình trong thư mục configs/",
        ) from exc


def _resolve_resume_checkpoint(path: str, checkpoint_dir: str) -> str:
    try:
        return resolve_path_within_root(
            path,
            checkpoint_dir,
            bare_name_in_root=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Checkpoint resume phải nằm bên trong checkpoint_dir đã cấu hình.",
        ) from exc


class TrainingConfigRequest(BaseModel):
    """Canonical config envelope shared by training planning endpoints.

    New clients send dotted ``overrides``. ``extra=allow`` keeps historical
    flat override fields readable through one compatibility table.
    """

    model_config = ConfigDict(extra="allow")

    config_path: str = Field(
        default="configs/truyen_kieu.yaml", description="Đường dẫn file cấu hình YAML"
    )
    overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="Canonical EngineConfig overrides in dotted-path form.",
    )


class StartTrainingRequest(TrainingConfigRequest):
    """Training start command plus lifecycle-only options."""

    quick_check: bool = Field(
        default=False, description="Chạy thử nghiệm 50 bước kiểm tra pipeline"
    )
    resume_checkpoint: Optional[str] = Field(
        default=None, description="Đường dẫn file checkpoint để tiếp tục huấn luyện"
    )


class CheckFeasibilityRequest(TrainingConfigRequest):
    """Feasibility accepts config overrides without lifecycle-only start fields."""


_LEGACY_OVERRIDE_PATHS = {
    "model_name": "model.name",
    "cleaner_type": "data.cleaner_type",
    "tokenizer_type": "data.tokenizer_type",
    "batch_size": "training.batch_size",
    "learning_rate": "training.learning_rate",
    "max_iters": "training.max_iters",
    "precision": "training.precision",
    "optimizer_type": "training.optimizer_type",
    "gradient_accumulation_steps": "training.gradient_accumulation_steps",
    "gradient_checkpointing": "training.gradient_checkpointing",
    "eval_interval": "training.eval_interval",
    "eval_iters": "training.eval_iters",
    "save_last": "training.save_last",
    "split_ratio": "data.split_ratio",
    "batch_provider_type": "data.batch_provider_type",
    "n_layer": "model.n_layer",
    "n_embd": "model.n_embd",
    "n_head": "model.n_head",
    "dropout": "model.dropout",
    "lr_scheduler_type": "training.lr_scheduler_type",
    "warmup_iters": "training.warmup_iters",
    "min_lr": "training.min_lr",
    "weight_decay": "training.weight_decay",
    "grad_clip": "training.grad_clip",
    "early_stopping_patience": "training.early_stopping_patience",
    "run_name": "training.run_name",
    "save_top_k": "training.save_top_k",
    "block_size": "model.block_size",
    "seed": "system.seed",
}


def _canonical_override_paths() -> set[str]:
    from src.core.config import EngineConfig

    result: set[str] = set()
    raw = EngineConfig().to_dict()
    for domain in ("system", "data", "model", "training"):
        values = raw.get(domain, {})
        if isinstance(values, dict):
            result.update(f"{domain}.{key}" for key in values)
    return result


_CANONICAL_OVERRIDE_PATHS = _canonical_override_paths()


def _override_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None or isinstance(value, (dict, list, tuple, set)):
        raise ValueError("Training override chỉ hỗ trợ scalar khác null.")
    return str(value)


def _build_overrides(req: TrainingConfigRequest, *, auto_run_name: bool = False) -> List[str]:
    extras = req.model_extra or {}
    ignored_legacy_envelope_fields = {"quick_check", "resume_checkpoint"}
    unknown_legacy = sorted(
        set(extras) - set(_LEGACY_OVERRIDE_PATHS) - ignored_legacy_envelope_fields
    )
    if unknown_legacy:
        raise ValueError("Training override top-level không hợp lệ: " + ", ".join(unknown_legacy))

    values: Dict[str, Any] = {}
    for field_name, path in _LEGACY_OVERRIDE_PATHS.items():
        value = getattr(req, field_name, None)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
            if path in {
                "model.name",
                "data.cleaner_type",
                "data.tokenizer_type",
                "data.batch_provider_type",
                "training.lr_scheduler_type",
            }:
                value = value.lower()
        if value is not None:
            values[path] = value

    for path, value in req.overrides.items():
        if path not in _CANONICAL_OVERRIDE_PATHS:
            raise ValueError(f"Training override key không hợp lệ: '{path}'.")
        values[path] = value

    if auto_run_name and "training.run_name" not in values:
        import time

        values["training.run_name"] = f"kieu_{time.strftime('%Y%m%d_%H%M%S')}"

    return [f"{path}={_override_value(value)}" for path, value in values.items()]


@router.post("/check-feasibility")
async def check_feasibility_endpoint(req: CheckFeasibilityRequest):
    """Ước tính VRAM trước training; đây là advisory vì runtime tokenizer có thể đổi vocab size."""
    from src.core.config import EngineConfig
    from src.core.diagnostics.estimator import check_memory_feasibility
    from src.core.runtime import resolve_training_plan

    try:
        overrides = _build_overrides(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    config_path = _resolve_training_config_path(req.config_path)
    config = EngineConfig.from_yaml(config_path, overrides=overrides if overrides else None)
    runtime_plan = resolve_training_plan(config)
    feasible, msg, budget = check_memory_feasibility(
        model_config=config.model,
        training_config=config.training,
        runtime_plan=runtime_plan,
    )

    return {
        "feasible": feasible,
        "advisory": True,
        "message": msg,
        "estimated_gb": budget.get("total_estimated_gb", 0.0),
        "estimated_mb": budget.get("total_estimated_mb", 0.0),
    }


@router.post("/start")
async def start_training_endpoint(req: StartTrainingRequest, request: Request):
    """Khởi chạy phiên huấn luyện nền."""
    training_service = request.app.state.training_service

    try:
        overrides = _build_overrides(req, auto_run_name=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Pre-flight Memory Feasibility Check
    from src.core.config import EngineConfig
    from src.core.diagnostics.estimator import check_memory_feasibility
    from src.core.runtime import resolve_training_plan

    config_path = _resolve_training_config_path(req.config_path)
    chk_config = EngineConfig.from_yaml(config_path, overrides=overrides if overrides else None)
    resume_checkpoint = None
    if req.resume_checkpoint:
        import os

        resume_checkpoint = _resolve_resume_checkpoint(
            req.resume_checkpoint, chk_config.training.checkpoint_dir
        )
        if not os.path.isfile(resume_checkpoint):
            raise HTTPException(
                status_code=400,
                detail=f"Không tìm thấy file checkpoint để resume: '{req.resume_checkpoint}'",
            )
    runtime_plan = resolve_training_plan(chk_config)
    feasible, mem_msg, budget = check_memory_feasibility(
        model_config=chk_config.model,
        training_config=chk_config.training,
        runtime_plan=runtime_plan,
    )

    try:
        training_service.start_training(
            config_path=config_path,
            overrides=overrides if overrides else None,
            quick_check=req.quick_check,
            resume_checkpoint=resume_checkpoint,
            runtime_plan=runtime_plan,
        )
        request.app.state.inference_service.set_checkpoint_dir(chk_config.training.checkpoint_dir)
        request.app.state.inference_service.set_vocab_path(chk_config.data.vocab_file)
        return {
            "status": "success",
            "message": "Đã khởi chạy huấn luyện trên luồng nền.",
            "preflight": {
                "feasible": feasible,
                "advisory": True,
                "message": mem_msg,
                "estimated_gb": budget.get("total_estimated_gb", 0.0),
                "estimated_mb": budget.get("total_estimated_mb", 0.0),
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


@router.get("/config")
async def get_training_config_endpoint(path: str = "configs/truyen_kieu.yaml"):
    """Return the canonical validated EngineConfig used by training."""
    from src.core.config import EngineConfig

    return EngineConfig.from_yaml(_resolve_training_config_path(path)).to_dict()


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
