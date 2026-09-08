"""
Inference API Routes: Quản lý sinh văn bản streaming và tải checkpoint.
"""

import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.config import GenerationConfig
from src.core.exceptions import AIEngineError

router = APIRouter(prefix="/api", tags=["Inference"])


def _resolve_config_path(path: str) -> str:
    """Normalize a config path and ensure it stays inside the real configs/ directory."""
    base_dir = os.path.abspath("configs")
    norm_path = os.path.normpath(path)
    candidate = os.path.abspath(norm_path)
    try:
        if os.path.commonpath([base_dir, candidate]) != base_dir:
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Chỉ cho phép truy cập các file cấu hình trong thư mục configs/",
        )
    return norm_path


class GenerateRequest(BaseModel):
    prompt: str = Field(default="Trăm năm trong cõi người ta,", description="Câu mồi bắt đầu")
    temperature: float = Field(default=0.75, ge=0.0, le=2.0)
    top_k: int = Field(default=40, ge=1, le=200)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    min_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0, le=2.0)
    max_new_tokens: int = Field(default=200, ge=10, le=1000)
    greedy: bool = Field(default=False)
    use_cache: bool = Field(default=True)
    backend: Optional[str] = Field(
        default=None, description="Tên Generator backend trong GeneratorRegistry"
    )
    stop_words: Optional[List[str]] = Field(
        default=None, description="Danh sách từ khóa dừng sinh văn bản"
    )


class LoadCheckpointRequest(BaseModel):
    path: str = Field(description="Đường dẫn file checkpoint .pt")
    backend: Optional[str] = Field(default=None, description="Tên Generator backend tùy chọn")


class SelectGeneratorRequest(BaseModel):
    backend: str = Field(description="Tên Generator backend (ví dụ: 'local', 'pytorch', 'default')")


@router.get("/generators")
async def list_generators_endpoint(request: Request):
    """Lấy danh sách các backend sinh văn bản đã đăng ký trong GeneratorRegistry."""
    inference_service = request.app.state.inference_service
    return {
        "generators": inference_service.list_generators(),
        "current_backend": inference_service.current_backend,
    }


@router.post("/generators/select")
async def select_generator_endpoint(req: SelectGeneratorRequest, request: Request):
    """Chuyển đổi generator backend sinh văn bản theo thời gian thực."""
    inference_service = request.app.state.inference_service
    try:
        inference_service.set_backend(req.backend)
        return {
            "status": "success",
            "message": f"Đã chuyển đổi sang generator backend '{req.backend}'.",
            "current_backend": inference_service.current_backend,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate/stream")
async def generate_stream_endpoint(req: GenerateRequest, request: Request):
    """Kênh phát sóng token theo thời gian thực (SSE) sử dụng TextIteratorStreamer."""
    inference_service = request.app.state.inference_service

    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Câu mồi prompt không được để trống.")

    requested_backend = req.backend
    if requested_backend is not None:
        requested_backend = requested_backend.lower().strip()
        if requested_backend not in inference_service.list_generators():
            raise HTTPException(
                status_code=400,
                detail=f"Generator backend không hợp lệ: '{req.backend}'.",
            )

    stop_tokens: Optional[List[int]] = None
    if req.stop_words and inference_service.tokenizer:
        token_set = set()
        for word in req.stop_words:
            if word:
                encoded = inference_service.tokenizer.encode(word)
                for tid in encoded:
                    token_set.add(tid)
        if token_set:
            stop_tokens = list(token_set)

    gen_config = GenerationConfig(
        max_new_tokens=req.max_new_tokens,
        temperature=0.0 if req.greedy else req.temperature,
        top_k=req.top_k,
        top_p=req.top_p,
        min_p=req.min_p,
        repetition_penalty=req.repetition_penalty,
        do_sample=not req.greedy,
        use_cache=req.use_cache,
        stop_tokens=stop_tokens,
    )

    generator_stream = inference_service.stream_generate(
        req.prompt, gen_config, backend=requested_backend
    )
    return StreamingResponse(
        generator_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/checkpoints")
async def list_checkpoints_endpoint(request: Request):
    """Lấy danh sách các checkpoint có sẵn."""
    inference_service = request.app.state.inference_service
    return {"checkpoints": inference_service.list_checkpoints()}


@router.post("/checkpoints/load")
async def load_checkpoint_endpoint(req: LoadCheckpointRequest, request: Request):
    """Nạp một checkpoint cụ thể vào bộ suy luận."""
    inference_service = request.app.state.inference_service
    try:
        inference_service.load_checkpoint(req.path, backend=req.backend)
        return {
            "status": "success",
            "message": f"Đã nạp checkpoint thành công: {req.path}",
            "current_checkpoint": req.path,
            "current_backend": inference_service.current_backend,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (AIEngineError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể nạp checkpoint: {e}") from e


@router.delete("/checkpoints/{filename}")
async def delete_checkpoint_endpoint(filename: str, request: Request):
    """Xóa an toàn một file checkpoint khỏi hệ thống."""
    inference_service = request.app.state.inference_service
    try:
        inference_service.delete_checkpoint(filename)
        return {"status": "success", "message": f"Đã xóa checkpoint: {filename}"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa checkpoint: {e}")


@router.get("/checkpoints/{filename}/download")
async def download_checkpoint_endpoint(filename: str):
    """Tải file checkpoint trực tiếp về máy người dùng."""
    import os

    from fastapi.responses import FileResponse

    safe_filename = os.path.basename(filename)
    checkpoint_path = os.path.join("checkpoints", safe_filename)
    if not os.path.exists(checkpoint_path) or not os.path.isfile(checkpoint_path):
        raise HTTPException(
            status_code=404, detail=f"Không tìm thấy file checkpoint: {safe_filename}"
        )

    return FileResponse(
        path=checkpoint_path,
        filename=safe_filename,
        media_type="application/octet-stream",
    )


class SaveConfigRequest(BaseModel):
    path: str = Field(
        default="configs/truyen_kieu.yaml", description="Đường dẫn file cấu hình YAML"
    )
    content: str = Field(description="Nội dung file YAML")


@router.get("/models")
async def list_models_endpoint():
    """Lấy danh sách tất cả các kiến trúc mô hình đã đăng ký trong ModelRegistry."""
    from src.models.registry import ModelRegistry

    return {"models": ModelRegistry.list_models()}


@router.get("/configs/raw")
async def get_raw_config_endpoint(path: str = "configs/truyen_kieu.yaml"):
    """Đọc nội dung thô của file cấu hình YAML."""
    norm_path = _resolve_config_path(path)
    if not os.path.exists(norm_path) or not os.path.isfile(norm_path):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy file cấu hình: {path}")

    with open(norm_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"path": norm_path, "content": content}


@router.post("/configs/save")
async def save_raw_config_endpoint(req: SaveConfigRequest):
    """Lưu nội dung chỉnh sửa vào file cấu hình YAML sau khi kiểm tra cú pháp hợp lệ."""
    import yaml

    norm_path = _resolve_config_path(req.path)

    try:
        yaml.safe_load(req.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cú pháp YAML không hợp lệ: {e}")

    os.makedirs(os.path.dirname(norm_path) or "configs", exist_ok=True)
    with open(norm_path, "w", encoding="utf-8") as f:
        f.write(req.content)

    return {"status": "success", "message": f"Đã lưu cấu hình thành công: {norm_path}"}
