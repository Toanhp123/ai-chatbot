"""
Các cấu trúc dữ liệu PyTorch Dataset chuyên biệt cho AI Engine.
Bao gồm:
- TextDataset: PyTorch Dataset tiêu chuẩn cho mô hình ngôn ngữ tự hồi quy in-memory.
- MemmapDataset: Dataset đọc dữ liệu từ file nhị phân ánh xạ bộ nhớ (np.memmap) với O(1) RAM.
"""

import os
from typing import Tuple

import numpy as np
import torch
from torch.utils.data import Dataset

from src.core.exceptions import DataPipelineError, DatasetEmptyError
from src.data.dtypes import resolve_numpy_dtype


class TextDataset(Dataset[Tuple[torch.Tensor, torch.Tensor]]):
    """PyTorch Dataset tiêu chuẩn cho mô hình ngôn ngữ tự hồi quy."""

    def __init__(self, data_tensor: torch.Tensor, block_size: int) -> None:
        if len(data_tensor) <= block_size:
            raise DatasetEmptyError(
                f"Dữ liệu huấn luyện ({len(data_tensor)} tokens) ngắn hơn hoặc bằng độ dài ngữ cảnh block_size ({block_size})!"
            )
        self.data = data_tensor
        self.block_size = block_size

    def __len__(self) -> int:
        return len(self.data) - self.block_size

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.data[idx : idx + self.block_size]
        y = self.data[idx + 1 : idx + self.block_size + 1]
        return x, y


class MemmapDataset(Dataset[Tuple[torch.Tensor, torch.Tensor]]):
    """Dataset đọc dữ liệu từ file nhị phân ánh xạ bộ nhớ (np.memmap).

    Tiết kiệm RAM tối đa (O(1) bộ nhớ), phù hợp cho các tập dữ liệu quy mô hàng gigabyte.
    """

    def __init__(
        self,
        filepath: str,
        block_size: int,
        dtype: str = "uint16",
    ) -> None:
        if not os.path.exists(filepath):
            raise DataPipelineError(
                f"Không tìm thấy file dữ liệu nhị phân: {filepath}",
                details={"filepath": filepath},
                suggestion="Hãy kiểm tra lại đường dẫn file .bin hoặc chạy DataPipeline.save_to_binary() trước.",
            )

        self.filepath = filepath
        self.block_size = block_size
        self.dtype_str = dtype
        self.data = np.memmap(filepath, dtype=resolve_numpy_dtype(dtype), mode="r")

        if len(self.data) <= block_size:
            raise DatasetEmptyError(
                f"File dữ liệu nhị phân ({len(self.data)} tokens) quá ngắn so với block_size ({block_size})!"
            )

    def __len__(self) -> int:
        return len(self.data) - self.block_size

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        chunk = self.data[idx : idx + self.block_size + 1].astype(np.int64)
        x = torch.from_numpy(chunk[:-1])
        y = torch.from_numpy(chunk[1:])
        return x, y


__all__ = [
    "TextDataset",
    "MemmapDataset",
]
