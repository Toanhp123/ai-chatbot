"""HTTP adapter for inference, checkpoint and config use cases."""

import asyncio
import os
from typing import Annotated, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.application.errors import AIEngineError, ConfigurationError
from src.application.inference import GenerationCommand, GenerationOverrides
from src.ui.path_policy import resolve_path_within_root
from src.ui.responses import GenerationStreamingResponse

router = APIRouter(prefix="/api", tags=["Inference"])


def _safe_config_path(path: Optional[str]) -> Optional[str]:
    if path is None:
        return None
    try:
        return resolve_path_within_root(path, "configs")
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Chỉ cho phép truy cập các file cấu hình trong thư mục configs/",
        ) from exc


class GenerateRequest(BaseModel):
    prompt: str = Field(default="Trăm năm trong cõi người ta,", max_length=65_536)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_k: Optional[int] = Field(default=None, ge=0, le=200)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: Optional[float] = Field(default=None, ge=1.0, le=2.0)
    max_new_tokens: Optional[int] = Field(default=None, ge=1, le=1000)
    greedy: Optional[bool] = Field(default=None)
    use_cache: Optional[bool] = Field(default=None)
    backend: Optional[str] = Field(default=None)
    stop_words: Optional[List[Annotated[str, Field(max_length=256)]]] = Field(
        default=None, max_length=64
    )

    def to_application(self) -> GenerationCommand:
        return GenerationCommand.create(
            prompt=self.prompt,
            overrides=GenerationOverrides(
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p,
                min_p=self.min_p,
                repetition_penalty=self.repetition_penalty,
                max_new_tokens=self.max_new_tokens,
                greedy=self.greedy,
                use_cache=self.use_cache,
            ),
            backend=self.backend,
            stop_words=self.stop_words,
        )


class LoadCheckpointRequest(BaseModel):
    path: str
    backend: Optional[str] = None


class SelectGeneratorRequest(BaseModel):
    backend: str


class SaveConfigRequest(BaseModel):
    path: Optional[str] = Field(default=None)
    content: str


@router.get("/generators")
async def list_generators_endpoint(request: Request):
    service = request.app.state.services.inference
    return {"generators": service.list_generators(), "current_backend": service.current_backend}


@router.get("/inference/state")
async def get_inference_state_endpoint(request: Request):
    return await asyncio.to_thread(request.app.state.services.inference.get_runtime_state)


@router.post("/generators/select")
async def select_generator_endpoint(req: SelectGeneratorRequest, request: Request):
    service = request.app.state.services.inference
    try:
        service.set_backend(req.backend)
        return {
            "status": "success",
            "message": f"Đã chuyển đổi sang generator backend '{req.backend}'.",
            "current_backend": service.current_backend,
        }
    except AIEngineError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate/stream")
async def generate_stream_endpoint(req: GenerateRequest, request: Request):
    session = await asyncio.to_thread(
        request.app.state.services.inference.begin_generation_command,
        req.to_application(),
    )
    return GenerationStreamingResponse(
        session=session,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/checkpoints")
async def list_checkpoints_endpoint(request: Request):
    return {
        "checkpoints": await asyncio.to_thread(
            request.app.state.services.inference.list_checkpoints
        )
    }


@router.post("/checkpoints/load")
async def load_checkpoint_endpoint(req: LoadCheckpointRequest, request: Request):
    service = request.app.state.services.inference
    try:
        await asyncio.to_thread(
            service.load_checkpoint,
            req.path,
            backend=req.backend,
            require_managed=True,
        )
        state = service.get_runtime_state()
        return {
            "status": "success",
            "message": f"Đã nạp checkpoint thành công: {req.path}",
            "current_checkpoint": state["current_checkpoint"],
            "current_checkpoint_revision": state["current_checkpoint_revision"],
            "current_backend": state["current_backend"],
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AIEngineError:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể nạp checkpoint: {exc}") from exc


@router.delete("/checkpoints/{filename}")
async def delete_checkpoint_endpoint(filename: str, request: Request):
    try:
        request.app.state.services.inference.delete_checkpoint(filename)
        return {"status": "success", "message": f"Đã xóa checkpoint: {filename}"}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa checkpoint: {exc}") from exc


@router.get("/checkpoints/{filename}/download")
async def download_checkpoint_endpoint(filename: str, request: Request):
    safe_filename = os.path.basename(filename)
    try:
        path = request.app.state.services.inference.resolve_checkpoint_path(
            safe_filename, filename_only=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404, detail=f"Không tìm thấy file checkpoint: {safe_filename}"
        )
    return FileResponse(path=path, filename=safe_filename, media_type="application/octet-stream")


@router.get("/models")
async def list_models_endpoint(request: Request):
    return {"models": request.app.state.services.inference.list_models()}


@router.get("/configs/raw")
async def get_raw_config_endpoint(request: Request, path: Optional[str] = None):
    try:
        resolved_path, content = request.app.state.services.config.read_raw(_safe_config_path(path))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"path": resolved_path, "content": content}


@router.post("/configs/save")
async def save_raw_config_endpoint(req: SaveConfigRequest, request: Request):
    source = _safe_config_path(req.path)
    try:
        path = request.app.state.services.config.save_raw(req.content, source)
    except ConfigurationError:
        raise
    return {"status": "success", "message": f"Đã lưu cấu hình thành công: {path}", "path": path}
