"""HTTP adapter for explorer application use cases."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.ui.path_policy import resolve_path_within_root

router = APIRouter(prefix="/api/explorer", tags=["Explorer"])


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


class TokenizeRequest(BaseModel):
    text: str = Field(default="Trăm năm trong cõi người ta,")
    tokenizer_type: str = Field(default="char")
    config_path: Optional[str] = Field(default=None)


class CleanRequest(BaseModel):
    text: str
    cleaner_type: str = Field(default="default")
    clean_line_numbers: bool = Field(default=True)
    dedup: bool = Field(default=False)
    dedup_mode: str = Field(default="consecutive")
    repetition: bool = Field(default=False)
    min_length: Optional[int] = Field(default=None)
    max_length: Optional[int] = Field(default=None)


class CompareTokenizersRequest(BaseModel):
    text: str = Field(default="Trăm năm trong cõi người ta,")


@router.post("/clean")
async def clean_endpoint(req: CleanRequest, request: Request):
    return request.app.state.explorer_service.clean(**req.model_dump())


@router.post("/tokenize")
async def tokenize_endpoint(req: TokenizeRequest, request: Request):
    try:
        return request.app.state.explorer_service.tokenize(
            text=req.text,
            tokenizer_type=req.tokenizer_type,
            source=_safe_config_path(req.config_path),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dataset-sample")
async def get_dataset_sample(request: Request, config_path: Optional[str] = None):
    return await asyncio.to_thread(
        request.app.state.explorer_service.dataset_sample,
        _safe_config_path(config_path),
    )


@router.post("/export-binary")
async def export_binary_endpoint(request: Request, config_path: Optional[str] = None):
    return await asyncio.to_thread(
        request.app.state.explorer_service.export_binary,
        _safe_config_path(config_path),
    )


@router.post("/compare-tokenizers")
async def compare_tokenizers_endpoint(
    req: CompareTokenizersRequest,
    request: Request,
    config_path: Optional[str] = None,
):
    return request.app.state.explorer_service.compare_tokenizers(
        text=req.text,
        source=_safe_config_path(config_path),
    )
