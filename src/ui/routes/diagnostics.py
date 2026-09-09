"""HTTP adapter for diagnostics application use cases."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.diagnostics import VramEstimateInput
from src.ui.path_policy import resolve_path_within_root

router = APIRouter(prefix="/api/diagnostics", tags=["Diagnostics"])


class VRAMEstimateRequest(BaseModel):
    """Transport overrides; omitted fields inherit the canonical active config."""

    device: Optional[str] = Field(default=None)
    model_name: Optional[str] = Field(default=None)
    batch_size: Optional[int] = Field(default=None, ge=1, le=512)
    block_size: Optional[int] = Field(default=None, ge=16, le=2048)
    n_embd: Optional[int] = Field(default=None, ge=32, le=1024)
    n_layer: Optional[int] = Field(default=None, ge=1, le=32)
    n_head: Optional[int] = Field(default=None, ge=1, le=32)
    vocab_size: Optional[int] = Field(default=None, ge=10, le=32000)
    precision: Optional[str] = Field(default=None)
    optimizer_type: Optional[str] = Field(default=None)
    gradient_checkpointing: Optional[bool] = Field(default=None)
    gradient_accumulation_steps: Optional[int] = Field(default=None, ge=1, le=32)
    intermediate_size: Optional[int] = Field(default=None, ge=0)
    multiple_of: Optional[int] = Field(default=None, ge=1)
    tie_word_embeddings: Optional[bool] = Field(default=None)
    bias: Optional[bool] = Field(default=None)

    def to_application(self) -> VramEstimateInput:
        return VramEstimateInput(**self.model_dump())


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


@router.get("/system")
async def get_system_diagnostics(request: Request):
    return await asyncio.to_thread(request.app.state.services.diagnostics.system)


@router.post("/estimate")
async def estimate_vram_endpoint(req: VRAMEstimateRequest, request: Request):
    return await asyncio.to_thread(
        request.app.state.services.diagnostics.estimate,
        req.to_application(),
    )


@router.post("/scenarios")
async def scenarios_endpoint(req: VRAMEstimateRequest, request: Request):
    return await asyncio.to_thread(
        request.app.state.services.diagnostics.scenarios,
        req.to_application(),
    )


@router.get("/advisor")
async def get_hardware_advisor_endpoint(request: Request):
    return await asyncio.to_thread(request.app.state.services.diagnostics.advisor)


@router.post("/gates/run")
async def run_quality_gates_endpoint(request: Request):
    return await asyncio.to_thread(request.app.state.services.diagnostics.run_quality_gates)


@router.get("/inspect")
async def inspect_model_endpoint(
    request: Request,
    config_path: Optional[str] = None,
    model_name: Optional[str] = None,
    n_embd: Optional[int] = None,
    n_head: Optional[int] = None,
    n_layer: Optional[int] = None,
    block_size: Optional[int] = None,
):
    return await asyncio.to_thread(
        request.app.state.services.diagnostics.inspect,
        source=_safe_config_path(config_path),
        model_name=model_name,
        n_embd=n_embd,
        n_head=n_head,
        n_layer=n_layer,
        block_size=block_size,
    )


@router.get("/logs")
async def get_system_logs_endpoint(request: Request, lines: int = 80):
    return await asyncio.to_thread(request.app.state.services.diagnostics.logs, lines)
