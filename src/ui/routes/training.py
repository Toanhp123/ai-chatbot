"""HTTP/SSE adapter for training application use cases."""

import asyncio
import os
import stat
from dataclasses import replace
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.application.config import ConfigRequest
from src.application.errors import AIEngineError
from src.application.training import TrainingCommand
from src.ui.path_policy import resolve_path_within_root

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


def _resolve_resume_checkpoint(path: str, checkpoint_dir: str) -> str:
    try:
        return resolve_path_within_root(path, checkpoint_dir, bare_name_in_root=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Checkpoint resume phải nằm bên trong checkpoint_dir đã cấu hình.",
        ) from exc


def _capture_resume_checkpoint_identity(path: str) -> tuple[int, int, int, int]:
    with open(path, "rb") as checkpoint_file:
        file_stat = os.fstat(checkpoint_file.fileno())
        if not stat.S_ISREG(file_stat.st_mode):
            raise OSError(f"Checkpoint resume không phải file thường: {path}")
        return (
            int(file_stat.st_dev),
            int(file_stat.st_ino),
            int(file_stat.st_size),
            int(file_stat.st_mtime_ns),
        )


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
    allowed = request.app.state.configuration_service.canonical_override_paths(
        ("system", "data", "model", "training")
    )
    try:
        return tuple(_build_overrides(req, allowed))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/check-feasibility")
async def check_feasibility_endpoint(req: CheckFeasibilityRequest, request: Request):
    plan = await asyncio.to_thread(
        request.app.state.training_application.plan,
        TrainingCommand(
            config_path=_safe_config_path(req.config_path),
            overrides=_request_overrides(req, request),
        ),
        assign_run_name=False,
    )
    feasibility = plan.feasibility
    return {
        "feasible": feasibility.feasible,
        "advisory": True,
        "message": feasibility.message,
        "estimated_gb": feasibility.estimated_gb,
        "estimated_mb": feasibility.estimated_mb,
    }


@router.post("/start")
async def start_training_endpoint(req: StartTrainingRequest, request: Request):
    training_application = request.app.state.training_application
    training_service = request.app.state.training_service
    command = TrainingCommand(
        config_path=_safe_config_path(req.config_path),
        overrides=_request_overrides(req, request),
        quick_check=req.quick_check,
    )
    plan = await asyncio.to_thread(training_application.plan, command)

    if req.resume_checkpoint:
        resume_checkpoint = _resolve_resume_checkpoint(
            req.resume_checkpoint,
            plan.requested_config.training.checkpoint_dir,
        )
        try:
            identity = _capture_resume_checkpoint_identity(resume_checkpoint)
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
        plan = replace(
            plan,
            resume_checkpoint=resume_checkpoint,
            resume_checkpoint_identity=identity,
        )

    try:
        await asyncio.to_thread(request.app.state.training_launch_service.start, plan)
    except AIEngineError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    feasibility = plan.feasibility
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
    request.app.state.training_service.stop_training()
    return {"status": "success", "message": "Đã gửi tín hiệu dừng huấn luyện an toàn."}


@router.post("/clear")
async def clear_training_endpoint(request: Request):
    try:
        request.app.state.training_service.clear_state()
        return {"status": "success", "message": "Đã làm mới thông tin huấn luyện."}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/config")
async def get_training_config_endpoint(request: Request, path: Optional[str] = None):
    config = request.app.state.configuration_service.resolve(
        ConfigRequest(source=_safe_config_path(path))
    )
    return config.to_dict()


@router.get("/status")
async def get_training_status_endpoint(request: Request):
    return request.app.state.training_service.get_state()


@router.get("/stream")
async def stream_training_metrics_endpoint(request: Request):
    return StreamingResponse(
        request.app.state.training_service.stream_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
