"""
Explorer API Routes: Trực quan hóa Tokenizer và xem trước dữ liệu huấn luyện.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.data.cleaners import get_cleaner
from src.data.cleaners.standard import DeduplicationFilter, LineLengthFilter, RepetitionFilter
from src.data.tokenizers import ByteTokenizer, load_tokenizer
from src.data.tokenizers.gemini import GeminiTokenizer

router = APIRouter(prefix="/api/explorer", tags=["Explorer"])


class TokenizeRequest(BaseModel):
    text: str = Field(default="Trăm năm trong cõi người ta,", description="Văn bản cần token hóa")
    tokenizer_type: str = Field(
        default="char", description="Loại tokenizer: 'char', 'byte', hoặc 'gemini'"
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
    """Mã hóa văn bản thành mảng Token ID và chi tiết từng ký tự (Hỗ trợ Char, Byte & Gemini AI Tokenizer)."""
    if req.tokenizer_type == "byte":
        tokenizer = ByteTokenizer()
    elif req.tokenizer_type == "gemini":
        tokenizer = GeminiTokenizer()
    else:
        inference_service = request.app.state.inference_service
        tokenizer = inference_service.tokenizer

        if tokenizer is None:
            if os.path.exists("data/vocab.json"):
                tokenizer = load_tokenizer("data/vocab.json")
            else:
                raise HTTPException(
                    status_code=404, detail="Không tìm thấy file từ điển data/vocab.json"
                )

    token_ids = tokenizer.encode(req.text)

    # Giải mã từng token đơn lẻ để hiển thị chip
    tokens_detail: List[Dict[str, Any]] = []
    for tid in token_ids:
        try:
            char_repr = tokenizer.decode([tid])
            display_char = "␣" if char_repr == " " else ("⏎\n" if char_repr == "\n" else char_repr)
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
        "tokenizer_type": req.tokenizer_type,
        "token_ids": token_ids,
        "tokens": tokens_detail,
        "char_count": len(req.text),
        "token_count": len(token_ids),
        "vocab_size": getattr(tokenizer, "vocab_size", 0),
    }


@router.get("/dataset-sample")
async def get_dataset_sample():
    """Xem trước dữ liệu huấn luyện và thông tin từ vựng."""
    input_file = "data/input.txt"
    vocab_file = "data/vocab.json"

    sample_lines: List[str] = []
    total_chars = 0
    total_lines = 0

    if os.path.exists(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            total_lines = len(lines)
            total_chars = sum(len(line) for line in lines)
            sample_lines = [line.strip() for line in lines[:25] if line.strip()]

    vocab_size = 0
    vocab_chars: List[str] = []
    if os.path.exists(vocab_file):
        import json

        with open(vocab_file, "r", encoding="utf-8") as vf:
            vocab_data = json.load(vf)
            vocab_size = len(vocab_data)
            vocab_chars = list(vocab_data.keys())[:50]

    return {
        "input_file": input_file,
        "total_lines": total_lines,
        "total_chars": total_chars,
        "sample_lines": sample_lines,
        "vocab_size": vocab_size,
        "sample_vocab": vocab_chars,
    }


@router.post("/export-binary")
async def export_binary_endpoint():
    """Đóng gói toàn bộ tập dữ liệu thành định dạng nhị phân (.bin) cho Memmap loader siêu tốc."""
    from src.core.config import EngineConfig
    from src.data.pipeline import DataPipeline

    config = EngineConfig.from_yaml("configs/truyen_kieu.yaml")
    train_data, val_data, _ = DataPipeline.setup_data(config.data)

    data_dir = os.path.dirname(os.path.abspath(config.data.input_file))
    train_bin = os.path.join(data_dir, "train.bin")
    val_bin = os.path.join(data_dir, "val.bin")

    DataPipeline.save_to_binary(train_data, train_bin)
    DataPipeline.save_to_binary(val_data, val_bin)

    train_size_mb = round(os.path.getsize(train_bin) / (1024 * 1024), 2)
    val_size_mb = round(os.path.getsize(val_bin) / (1024 * 1024), 2)

    return {
        "status": "success",
        "message": "Đã đóng gói dữ liệu nhị phân thành công!",
        "train_tokens": len(train_data),
        "val_tokens": len(val_data),
        "train_bin": train_bin,
        "val_bin": val_bin,
        "train_size_mb": train_size_mb,
        "val_size_mb": val_size_mb,
    }


class CompareTokenizersRequest(BaseModel):
    text: str = Field(default="Trăm năm trong cõi người ta,", description="Văn bản cần so sánh")


@router.post("/compare-tokenizers")
async def compare_tokenizers_endpoint(req: CompareTokenizersRequest):
    """So sánh đồng thời 3 bộ mã hóa Char, Byte và Gemini trên cùng một chuỗi văn bản."""
    char_tok = load_tokenizer("data/vocab.json") if os.path.exists("data/vocab.json") else None
    byte_tok = ByteTokenizer()
    gemini_tok = GeminiTokenizer()

    results: Dict[str, Any] = {}
    for key, label, tok in [
        ("char", "Char Tokenizer", char_tok),
        ("byte", "Byte Tokenizer (Zero-OOV)", byte_tok),
        ("gemini", "Gemini AI Tokenizer", gemini_tok),
    ]:
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
