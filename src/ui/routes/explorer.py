"""
Explorer API Routes: Trực quan hóa Tokenizer và xem trước dữ liệu huấn luyện.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.data.cleaners import get_cleaner
from src.data.cleaners.standard import DeduplicationFilter, LineLengthFilter, RepetitionFilter
from src.data.tokenizers import ByteTokenizer, load_tokenizer
from src.data.tokenizers.gemini import GeminiTokenizer
from src.ui.path_policy import resolve_path_within_root

router = APIRouter(prefix="/api/explorer", tags=["Explorer"])


def _serialize_api_path(path: str) -> str:
    """Use a stable slash convention for filesystem paths crossing the HTTP boundary."""
    return str(path).replace("\\", "/")


def _load_engine_config(request: Request, config_path: Optional[str] = None):
    from src.core.config import EngineConfig

    if config_path is None:
        return request.app.state.inference_service.get_engine_config()
    try:
        path = resolve_path_within_root(config_path, "configs")
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Chỉ cho phép dùng file cấu hình trong thư mục configs/",
        ) from exc
    return EngineConfig.from_yaml(path)


class TokenizeRequest(BaseModel):
    text: str = Field(default="Trăm năm trong cõi người ta,", description="Văn bản cần token hóa")
    tokenizer_type: str = Field(
        default="char",
        description="Loại tokenizer: 'char', 'byte'; 'gemini' chỉ là alias legacy của byte",
    )
    config_path: Optional[str] = Field(
        default=None,
        description="Config override tùy chọn; mặc định dùng effective runtime config",
    )


class CleanRequest(BaseModel):
    text: str = Field(description="Văn bản thô cần làm sạch")
    cleaner_type: str = Field(
        default="default", description="Loại cleaner: 'default', 'gemini', hoặc 'passthrough'"
    )
    clean_line_numbers: bool = Field(default=True, description="Loại bỏ số thứ tự đầu dòng")
    dedup: bool = Field(default=False, description="Lọc khử trùng lặp dòng")
    dedup_mode: str = Field(
        default="consecutive", description="Chế độ khử trùng: 'consecutive' hoặc 'global'"
    )
    repetition: bool = Field(default=False, description="Khử lặp ký tự thừa")
    min_length: Optional[int] = Field(default=None, description="Độ dài tối thiểu của dòng")
    max_length: Optional[int] = Field(default=None, description="Độ dài tối đa của dòng")


@router.post("/clean")
async def clean_endpoint(req: CleanRequest):
    """Làm sạch văn bản thô theo chuẩn Unicode NFC và các bộ lọc nâng cao."""
    cleaner = get_cleaner(req.cleaner_type, clean_line_numbers=req.clean_line_numbers)
    cleaned = cleaner.process(req.text)

    if req.repetition:
        cleaned = RepetitionFilter().process(cleaned)

    if req.min_length is not None or req.max_length is not None:
        min_l = req.min_length if req.min_length is not None else 1
        max_l = req.max_length if req.max_length is not None else 4096
        cleaned = LineLengthFilter(min_len=min_l, max_len=max_l).process(cleaned)

    if req.dedup:
        mode = req.dedup_mode if req.dedup_mode in ("consecutive", "global") else "consecutive"
        cleaned = DeduplicationFilter(mode=mode).process(cleaned)

    return {
        "raw": req.text,
        "cleaned": cleaned,
        "raw_length": len(req.text),
        "cleaned_length": len(cleaned),
        "diff_chars": len(req.text) - len(cleaned),
    }


@router.post("/tokenize")
async def tokenize_endpoint(req: TokenizeRequest, request: Request):
    """Mã hóa văn bản thành Token ID; ``gemini`` được giữ như alias legacy của ByteTokenizer."""
    requested_type = req.tokenizer_type.strip().lower()
    if requested_type == "byte":
        tokenizer = ByteTokenizer()
    elif requested_type == "gemini":
        tokenizer = GeminiTokenizer()
    elif requested_type == "char":
        config = _load_engine_config(request, req.config_path)
        if not os.path.isfile(config.data.vocab_file):
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy file từ điển {config.data.vocab_file}",
            )
        tokenizer = load_tokenizer(config.data.vocab_file)
    else:
        raise HTTPException(
            status_code=400, detail=f"Tokenizer không được hỗ trợ: {requested_type}"
        )

    token_ids = tokenizer.encode(req.text)

    # Byte token IDs are UTF-8 bytes, not standalone Unicode characters.
    # Rendering each byte through decode([id]) would display replacement glyphs for
    # multibyte Vietnamese/emoji sequences, so expose non-ASCII bytes as hex chips.
    byte_semantics = tokenizer.identity_payload().get("tokenizer_type") == "byte"
    tokens_detail: List[Dict[str, Any]] = []
    for tid in token_ids:
        try:
            if byte_semantics and 0 <= tid < 256:
                if tid == 32:
                    display_char = "␣"
                elif tid == 10:
                    display_char = "⏎\n"
                elif 33 <= tid <= 126:
                    display_char = chr(tid)
                else:
                    display_char = f"0x{tid:02X}"
            else:
                char_repr = tokenizer.decode([tid])
                display_char = (
                    "␣" if char_repr == " " else ("⏎\n" if char_repr == "\n" else char_repr)
                )
        except Exception:
            display_char = f"<{tid}>"

        tokens_detail.append(
            {
                "id": tid,
                "raw": display_char,
            }
        )

    return {
        "text": req.text,
        "tokenizer_type": (
            "gemini"
            if requested_type == "gemini"
            else str(tokenizer.identity_payload().get("tokenizer_type", requested_type))
        ),
        "token_ids": token_ids,
        "tokens": tokens_detail,
        "char_count": len(req.text),
        "token_count": len(token_ids),
        "vocab_size": getattr(tokenizer, "vocab_size", 0),
    }


@router.get("/dataset-sample")
async def get_dataset_sample(request: Request, config_path: Optional[str] = None):
    """Preview the effective runtime dataset, or an explicitly requested config."""
    config = _load_engine_config(request, config_path)
    input_file = config.data.input_file
    vocab_file = config.data.vocab_file

    sample_lines: List[str] = []
    total_chars = 0
    total_lines = 0

    if os.path.isfile(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            total_lines = len(lines)
            total_chars = sum(len(line) for line in lines)
            sample_lines = [line.strip() for line in lines[:25] if line.strip()]

    vocab_size = 0
    vocab_chars: List[str] = []
    if os.path.isfile(vocab_file):
        tokenizer = load_tokenizer(vocab_file)
        vocab_size = tokenizer.vocab_size
        payload = tokenizer.identity_payload()
        raw_vocab = payload.get("vocab")
        if isinstance(raw_vocab, list):
            vocab_chars = [str(token) for token in raw_vocab[:50]]

    return {
        "input_file": _serialize_api_path(input_file),
        "vocab_file": _serialize_api_path(vocab_file),
        "total_lines": total_lines,
        "total_chars": total_chars,
        "sample_lines": sample_lines,
        "vocab_size": vocab_size,
        "sample_vocab": vocab_chars,
    }


@router.post("/export-binary")
async def export_binary_endpoint(request: Request, config_path: Optional[str] = None):
    """Package the effective dataset without blocking the API loop."""
    from src.data.pipeline import DataPipeline

    config = _load_engine_config(request, config_path)

    def _export() -> Dict[str, Any]:
        train_data, val_data, _ = DataPipeline.setup_data(config.data)
        data_dir = os.path.dirname(os.path.abspath(config.data.input_file))
        train_bin = os.path.join(data_dir, "train.bin")
        val_bin = os.path.join(data_dir, "val.bin")
        DataPipeline.save_to_binary(train_data, train_bin)
        DataPipeline.save_to_binary(val_data, val_bin)
        return {
            "status": "success",
            "message": "Đã đóng gói dữ liệu nhị phân thành công!",
            "train_tokens": len(train_data),
            "val_tokens": len(val_data),
            "train_bin": train_bin,
            "val_bin": val_bin,
            "train_size_mb": round(os.path.getsize(train_bin) / (1024 * 1024), 2),
            "val_size_mb": round(os.path.getsize(val_bin) / (1024 * 1024), 2),
        }

    return await asyncio.to_thread(_export)


class CompareTokenizersRequest(BaseModel):
    text: str = Field(default="Trăm năm trong cõi người ta,", description="Văn bản cần so sánh")


@router.post("/compare-tokenizers")
async def compare_tokenizers_endpoint(
    req: CompareTokenizersRequest, request: Request, config_path: Optional[str] = None
):
    """Compare effective canonical tokenizer semantics with byte tokenization."""
    config = _load_engine_config(request, config_path)
    configured_tok = (
        load_tokenizer(config.data.vocab_file) if os.path.isfile(config.data.vocab_file) else None
    )
    byte_tok = ByteTokenizer()
    candidates = []
    if configured_tok is not None:
        configured_type = str(configured_tok.identity_payload().get("tokenizer_type", "configured"))
        if configured_type != "byte":
            candidates.append(
                (configured_type, f"{configured_type.title()} Tokenizer", configured_tok)
            )
    candidates.append(("byte", "Byte Tokenizer (Zero-OOV)", byte_tok))

    results: Dict[str, Any] = {}
    for key, label, tok in candidates:
        if tok is None:
            continue
        token_ids = tok.encode(req.text)
        token_count = len(token_ids)
        char_count = len(req.text)
        compression = round(char_count / max(token_count, 1), 2)
        results[key] = {
            "label": label,
            "vocab_size": getattr(tok, "vocab_size", 0),
            "token_count": token_count,
            "compression_ratio": compression,
            "sample_token_ids": token_ids[:15],
        }

    return {
        "text": req.text,
        "char_count": len(req.text),
        "comparisons": results,
    }
