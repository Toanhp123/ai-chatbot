"""HTTP/SSE adapter for training application use cases."""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from src.application.config import ConfigRequest
from src.application.errors import AIEngineError
from src.application.training import TrainingCommand
from src.ui.path_policy import resolve_path_within_root
from src.ui.responses import TrainingStreamingResponse

router = APIRouter(prefix="/api/training", tags=["Training"])


def _safe_config_path(path: Optional[str]) -> Optional[str]:
    if path is None:
        return None
    try:
        return resolve_path_within_root(path, "configs")
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Chỉ cho phép dùng file cấu hình trong thư mục configs/",
        ) from exc


class TrainingConfigRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    config_path: Optional[str] = Field(default=None)
    overrides: Dict[str, Any] = Field(default_factory=dict)


class StartTrainingRequest(TrainingConfigRequest):
    quick_check: bool = Field(default=False)
    resume_checkpoint: Optional[str] = Field(default=None)


class CheckFeasibilityRequest(TrainingConfigRequest):
    pass


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


def _override_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None or isinstance(value, (dict, list, tuple, set)):
        raise ValueError("Training override chỉ hỗ trợ scalar khác null.")
    return str(value)


def _build_overrides(req: TrainingConfigRequest, allowed_paths: set[str]) -> List[str]:
    extras = req.model_extra or {}
    ignored = {"quick_check", "resume_checkpoint"}
    unknown_legacy = sorted(set(extras) - set(_LEGACY_OVERRIDE_PATHS) - ignored)
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
        if path not in allowed_paths:
            raise ValueError(f"Training override key không hợp lệ: '{path}'.")
        values[path] = value
    return [f"{path}={_override_value(value)}" for path, value in values.items()]


def _request_overrides(req: TrainingConfigRequest, request: Request) -> tuple[str, ...]:
    allowed = request.app.state.services.config.canonical_override_paths(
        ("system", "data", "model", "training")
    )
    try:
        return tuple(_build_overrides(req, allowed))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/check-feasibility")
async def check_feasibility_endpoint(req: CheckFeasibilityRequest, request: Request):
    feasibility = await asyncio.to_thread(
        request.app.state.services.training.check_feasibility,
        TrainingCommand(
            config_path=_safe_config_path(req.config_path),
            overrides=_request_overrides(req, request),
        ),
    )
    return {
        "feasible": feasibility.feasible,
        "advisory": True,
        "message": feasibility.message,
        "estimated_gb": feasibility.estimated_gb,
        "estimated_mb": feasibility.estimated_mb,
    }


@router.post("/start")
async def start_training_endpoint(req: StartTrainingRequest, request: Request):
    training_service = request.app.state.services.training
    command = TrainingCommand(
        config_path=_safe_config_path(req.config_path),
        overrides=_request_overrides(req, request),
        quick_check=req.quick_check,
        resume_checkpoint=req.resume_checkpoint,
    )

    try:
        start_result = await asyncio.to_thread(
            request.app.state.services.training.start,
            command,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Không tìm thấy file checkpoint để resume: '{req.resume_checkpoint}'",
        ) from exc
    except (IsADirectoryError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Không thể chốt revision checkpoint để resume; file có thể đã bị "
                f"thay thế hoặc không còn hợp lệ: '{req.resume_checkpoint}'"
            ),
        ) from exc
    except HTTPException:
        raise
    except AIEngineError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    feasibility = start_result.feasibility
    return {
        "status": "success",
        "message": "Đã khởi chạy huấn luyện trên luồng nền.",
        "preflight": {
            "feasible": feasibility.feasible,
            "advisory": True,
            "message": feasibility.message,
            "estimated_gb": feasibility.estimated_gb,
            "estimated_mb": feasibility.estimated_mb,
        },
        "state": training_service.get_state(),
    }


@router.post("/stop")
async def stop_training_endpoint(request: Request):
    request.app.state.services.training.stop()
    return {"status": "success", "message": "Đã gửi tín hiệu dừng huấn luyện an toàn."}


@router.post("/clear")
async def clear_training_endpoint(request: Request):
    try:
        request.app.state.services.training.clear()
        return {"status": "success", "message": "Đã làm mới thông tin huấn luyện."}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/config")
async def get_training_config_endpoint(request: Request, path: Optional[str] = None):
    return request.app.state.services.config.resolve_mapping(
        ConfigRequest(source=_safe_config_path(path))
    )


@router.get("/status")
async def get_training_status_endpoint(request: Request):
    return request.app.state.services.training.get_state()


@router.get("/stream")
async def stream_training_metrics_endpoint(request: Request):
    return TrainingStreamingResponse(
        events=request.app.state.services.training.iter_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
