"""
Lớp cơ sở trừu tượng cho tất cả các kiến trúc mô hình nơ-ron ngôn ngữ (BaseModel).
Kế thừa đồng thời từ torch.nn.Module và abc.ABC để thiết lập hợp đồng giao diện chuẩn.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import torch
import torch.nn as nn


class BaseModel(nn.Module, ABC):
    """Lớp cơ sở trừu tượng cho toàn bộ các mô hình ngôn ngữ trong AI Engine."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()

    @property
    @abstractmethod
    def block_size(self) -> int:
        """Độ dài ngữ cảnh tối đa (context length) mà mô hình hỗ trợ."""
        pass

    @property
    @abstractmethod
    def vocab_size(self) -> int:
        """Kích thước bảng từ điển của mô hình."""
        pass

    @property
    def device(self) -> torch.device:
        """Thiết bị phần cứng hiện tại của mô hình (CPU, CUDA, MPS)."""
        return next(self.parameters()).device

    @property
    def dtype(self) -> torch.dtype:
        """Kiểu dữ liệu số học hiện tại của các tham số mô hình."""
        return next(self.parameters()).dtype

    def _embedding_param_count(self) -> int:
        """Return architecture-specific embedding parameters excluded by ``non_embedding``."""
        return 0

    def get_num_params(self, non_embedding: bool = False) -> int:
        """Return trainable parameter count with optional architecture-defined embedding exclusion."""
        count = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return count - self._embedding_param_count() if non_embedding else count

    def reset_kv_cache(self) -> None:
        """Đặt lại bộ nhớ đệm Key-Value (mặc định no-op cho các mô hình tính full-attention)."""
        pass

    def has_active_kv_cache(self) -> bool:
        """Kiểm tra xem mô hình hiện có đang duy trì KV-cache hay không."""
        return False

    @abstractmethod
    def forward(
        self,
        idx: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """Thực thi một bước lan truyền thuận (Forward Pass).

        Args:
            idx: Tensor chỉ số token đầu vào có kích thước (batch_size, seq_len).
            targets: Tensor chỉ số token mục tiêu có kích thước (batch_size, seq_len) hoặc None.
            use_cache: Có sử dụng và cập nhật bộ nhớ đệm KV-Cache cho suy luận hay không.

        Returns:
            Tuple gồm:
            - logits: Tensor xác suất chưa chuẩn hóa có kích thước (batch_size, seq_len, vocab_size).
            - loss: Scalar tensor mất mát Cross-Entropy (nếu có targets) hoặc None.
        """
        pass


__all__ = ["BaseModel"]
