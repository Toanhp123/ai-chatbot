"""
Đường ống nạp, xử lý và phân phối dữ liệu huấn luyện (Data Pipeline).
Bao gồm:
- DataPipeline: Quản lý toàn trình từ đọc văn bản, làm sạch, token hóa, lưu vocab, chia train/val, và binary I/O.
"""

import os
import urllib.request
from typing import Callable, Optional, Protocol, Tuple

import numpy as np
import torch

from src.core.config import DataConfig
from src.core.exceptions import DataPipelineError, DatasetEmptyError
from src.core.logging import get_logger
from src.data.batch_provider import extract_tensor_batch
from src.data.dtypes import resolve_numpy_dtype
from src.data.tokenizers import BaseTokenizer

logger = get_logger("DataPipeline")


class TextPreprocessor(Protocol):
    """Minimal capability contract DataPipeline needs from an injected cleaner."""

    def __call__(self, text: str, /) -> str: ...


class DataPipeline:
    """Đường ống nạp, xử lý và phân phối dữ liệu huấn luyện."""

    @staticmethod
    def fetch_or_load_text(
        config: DataConfig,
        cleaner: TextPreprocessor,
        *,
        fallback_text: Optional[str] = None,
        persist_fallback: bool = False,
    ) -> str:
        """Đọc dữ liệu local hoặc tải từ URL.

        Capability này không tự quyết định fallback corpus. Caller phải truyền
        ``fallback_text`` một cách explicit nếu use case cho phép fallback.
        """
        os.makedirs(config.data_dir, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(config.input_file)), exist_ok=True)

        # 1. Existing local data is authoritative regardless of size. Never overwrite
        # a user-provided corpus merely because it is small; downstream validation
        # is responsible for rejecting genuinely insufficient datasets.
        if os.path.isfile(config.input_file):
            logger.info(f"Đọc dữ liệu từ file có sẵn: {config.input_file}")
            with open(config.input_file, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read()
            return cleaner(raw_text)

        # 2. Tải dữ liệu từ URL nếu có
        if config.source_url:
            logger.info(f"Đang tải dữ liệu từ URL: {config.source_url}")
            try:
                req = urllib.request.Request(
                    config.source_url, headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw_text = resp.read().decode("utf-8", errors="replace")
            except Exception as e:
                if fallback_text is None:
                    raise DataPipelineError(
                        f"Không thể tải corpus từ nguồn đã cấu hình: {config.source_url}",
                        details={"source_url": config.source_url},
                    ) from e
                logger.warning(
                    "Không thể tải dữ liệu từ internet (%s). "
                    "Application đã cho phép dùng corpus dự phòng.",
                    e,
                )
            else:
                # Cleaning and persistence are separate mechanisms. Their failures must
                # not be reclassified as a remote-source failure.
                cleaned_text = cleaner(raw_text)
                with open(config.input_file, "w", encoding="utf-8") as f:
                    f.write(cleaned_text)
                logger.info(
                    f"Tải và lưu thành công {len(cleaned_text):,} ký tự vào {config.input_file}"
                )
                return cleaned_text

        if fallback_text is None:
            raise DataPipelineError(
                "Không có dữ liệu local và Application không cung cấp corpus dự phòng.",
                details={"input_file": config.input_file, "source_url": config.source_url},
            )

        cleaned_fallback = cleaner(fallback_text)
        if persist_fallback:
            with open(config.input_file, "w", encoding="utf-8") as f:
                f.write(cleaned_fallback)
            logger.info(f"Đã lưu dữ liệu dự phòng tại: {config.input_file}")
        return cleaned_fallback

    @classmethod
    def setup_data(
        cls,
        config: DataConfig,
        cleaner: TextPreprocessor,
        tokenizer: Optional[BaseTokenizer] = None,
        tokenizer_factory: Optional[Callable[[str], BaseTokenizer]] = None,
        block_size: Optional[int] = None,
        *,
        fallback_text: Optional[str] = None,
        persist_fallback: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor, BaseTokenizer]:
        """Thiết lập pipeline dữ liệu hoàn chỉnh: nạp text, tokenize, lưu vocab, chia train/val.

        Cleaner phải do caller cung cấp. Tokenizer phải được caller cung cấp trực tiếp
        hoặc qua tokenizer_factory; capability này không tự chọn implementation từ config.
        """
        text = cls.fetch_or_load_text(
            config,
            cleaner=cleaner,
            fallback_text=fallback_text,
            persist_fallback=persist_fallback,
        )

        if tokenizer is None:
            if tokenizer_factory is None:
                raise DataPipelineError(
                    "Application/caller phải cung cấp tokenizer hoặc tokenizer_factory explicit."
                )
            tokenizer = tokenizer_factory(text)

        tokenizer.save_vocab(config.vocab_file)

        data_tensor = tokenizer.encode_as_tensor(text)
        if len(data_tensor) < 10:
            raise DatasetEmptyError(
                f"Tập dữ liệu quá ngắn: chỉ chứa {len(data_tensor)} tokens!"
            )

        split_idx = int(config.split_ratio * len(data_tensor))
        train_data = data_tensor[:split_idx]
        val_data = data_tensor[split_idx:]

        if block_size is not None:
            if block_size <= 0:
                raise DataPipelineError(f"block_size phải > 0, nhận được {block_size}")
            if len(train_data) <= block_size:
                raise DatasetEmptyError(
                    f"Tập train chỉ có {len(train_data)} tokens, không đủ cho block_size={block_size}."
                )
            if len(val_data) <= block_size:
                raise DatasetEmptyError(
                    f"Tập đánh giá/validation chỉ có {len(val_data)} tokens, không đủ cho block_size={block_size}."
                )

        logger.info(
            f"Dữ liệu sẵn sàng: {len(data_tensor):,} tokens | Vocab: {tokenizer.vocab_size} | "
            f"Tokenizer: {tokenizer.__class__.__name__}"
        )
        logger.info(
            f"Tập Train: {len(train_data):,} tokens | Tập Val: {len(val_data):,} tokens"
        )
        return train_data, val_data, tokenizer

    @staticmethod
    def get_batch(
        data: torch.Tensor, block_size: int, batch_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Trích xuất ngẫu nhiên mini-batch siêu tốc trực tiếp trên tensor."""
        return extract_tensor_batch(data, block_size, batch_size, device)

    @staticmethod
    def save_to_binary(
        data_tensor: torch.Tensor, filepath: str, dtype: str = "uint16"
    ) -> None:
        """Lưu trữ tensor mã token thành file nhị phân nén phẳng (.bin) cho Memmap."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        np_dtype = resolve_numpy_dtype(dtype)
        source = data_tensor.detach().cpu().numpy()
        if not np.issubdtype(source.dtype, np.integer):
            raise DataPipelineError(
                f"Tensor token phải có integer dtype trước khi lưu, nhận được '{source.dtype}'"
            )
        if source.size:
            limits = np.iinfo(np_dtype)
            min_token = int(source.min())
            max_token = int(source.max())
            if min_token < limits.min or max_token > limits.max:
                raise DataPipelineError(
                    f"Token ID ngoài range của dtype {np_dtype}: "
                    f"[{min_token}, {max_token}] không nằm trong [{limits.min}, {limits.max}]"
                )
        arr = source.astype(np_dtype, copy=False)
        arr.tofile(filepath)
        logger.info(f"Đã lưu {len(arr):,} tokens nhị phân ({dtype}) vào '{filepath}'")

    @staticmethod
    def load_binary(filepath: str, dtype: str = "uint16") -> torch.Tensor:
        """Nạp file nhị phân vào PyTorch Long Tensor."""
        if not os.path.exists(filepath):
            raise DataPipelineError(f"Không tìm thấy file nhị phân: {filepath}")
        np_dtype = resolve_numpy_dtype(dtype)
        arr = np.fromfile(filepath, dtype=np_dtype).astype(np.int64)
        return torch.from_numpy(arr)


__all__ = ["DataPipeline"]

