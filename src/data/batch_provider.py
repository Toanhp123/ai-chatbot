"""
Các cơ chế cung cấp lô dữ liệu (Batch Providers) cho AI Engine.
Bao gồm:
- BaseBatchProvider: Lớp cơ sở trừu tượng cho các nhà cung cấp batch.
- TensorBatchProvider: Bộ trích xuất mini-batch ngẫu nhiên siêu tốc trực tiếp trên in-memory Tensor.
- DataLoaderBatchProvider: Bộ cung cấp mini-batch bằng PyTorch DataLoader chuẩn (multi-workers & pin_memory).
- get_batch_provider: Factory khởi tạo batch provider linh hoạt theo cấu hình.
"""

from abc import ABC, abstractmethod
from collections.abc import Sized
from typing import Any, Iterator, Optional, Tuple

import torch
from torch.utils.data import DataLoader, Dataset

from src.core.exceptions import DataPipelineError, DatasetEmptyError
from src.data.dataset import TextDataset


def extract_tensor_batch(
    data: torch.Tensor, block_size: int, batch_size: int, device: str
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Trích xuất ngẫu nhiên mini-batch siêu tốc trực tiếp trên tensor."""
    if len(data) <= block_size:
        raise DatasetEmptyError(
            f"Kích thước tensor ({len(data)}) không đủ để trích xuất block_size ({block_size})!"
        )
    ix = torch.randint(len(data) - block_size, (batch_size,))
    x = torch.stack([data[i : i + block_size] for i in ix])
    y = torch.stack([data[i + 1 : i + block_size + 1] for i in ix])
    return x.to(device), y.to(device)


class BaseBatchProvider(ABC):
    """Lớp cơ sở trừu tượng cung cấp các lô dữ liệu (Batch Provider)."""

    def state_dict(self) -> dict[str, Any]:
        """State required for exact resume; stateless providers return an empty dict."""
        return {}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        """Restore provider state; stateless providers intentionally ignore it."""
        del state

    @property
    def supports_exact_resume(self) -> bool:
        return True


    @abstractmethod
    def get_train_batch(
        self, batch_size: int, block_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Trích xuất một batch dữ liệu huấn luyện (x, y)."""
        pass

    @abstractmethod
    def get_val_batch(
        self, batch_size: int, block_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Trích xuất một batch dữ liệu đánh giá (x, y)."""
        pass


class TensorBatchProvider(BaseBatchProvider):
    """Nguồn cung cấp dữ liệu huấn luyện/kiểm tra dựa trên in-memory Tensor."""

    def __init__(self, train_data: torch.Tensor, val_data: torch.Tensor) -> None:
        self.train_data = train_data
        self.val_data = val_data

    @property
    def train_tokens(self) -> int:
        """Tổng số tokens trong tập huấn luyện."""
        return len(self.train_data)

    @property
    def val_tokens(self) -> int:
        """Tổng số tokens trong tập đánh giá."""
        return len(self.val_data)

    def get_train_batch(
        self, batch_size: int, block_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        return extract_tensor_batch(self.train_data, block_size, batch_size, device)

    def get_val_batch(
        self, batch_size: int, block_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        return extract_tensor_batch(self.val_data, block_size, batch_size, device)


class DataLoaderBatchProvider(BaseBatchProvider):
    """Nguồn cung cấp dữ liệu huấn luyện dựa trên PyTorch DataLoader tiêu chuẩn."""

    def __init__(
        self,
        train_dataset: Dataset[Tuple[torch.Tensor, torch.Tensor]],
        val_dataset: Dataset[Tuple[torch.Tensor, torch.Tensor]],
        num_workers: int = 0,
        pin_memory: bool = False,
    ) -> None:
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.num_workers = num_workers
        self.pin_memory = pin_memory

        self._train_loader: Optional[DataLoader[Any]] = None
        self._train_iter: Optional[Iterator[Any]] = None
        self._curr_train_batch_size: Optional[int] = None

        self._val_loader: Optional[DataLoader[Any]] = None
        self._val_iter: Optional[Iterator[Any]] = None
        self._curr_val_batch_size: Optional[int] = None

        self._manual_train_order: Optional[torch.Tensor] = None
        self._manual_train_cursor = 0
        self._manual_val_cursor = 0

    @property
    def supports_exact_resume(self) -> bool:
        return (
            self.num_workers == 0
            and isinstance(self.train_dataset, Sized)
            and isinstance(self.val_dataset, Sized)
        )

    def state_dict(self) -> dict[str, Any]:
        if not self.supports_exact_resume:
            return {"exact_resume": False, "num_workers": self.num_workers}
        return {
            "exact_resume": True,
            "train_order": (
                self._manual_train_order.clone()
                if self._manual_train_order is not None
                else None
            ),
            "train_cursor": self._manual_train_cursor,
            "val_cursor": self._manual_val_cursor,
            "train_batch_size": self._curr_train_batch_size,
            "val_batch_size": self._curr_val_batch_size,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        if not self.supports_exact_resume:
            if state.get("exact_resume"):
                raise ValueError(
                    "Không thể exact-resume DataLoaderBatchProvider khi num_workers > 0 "
                    "hoặc dataset không có kích thước xác định."
                )
            return
        raw_order = state.get("train_order")
        self._manual_train_order = (
            raw_order.detach().cpu().to(dtype=torch.long).clone()
            if isinstance(raw_order, torch.Tensor)
            else None
        )
        self._manual_train_cursor = int(state.get("train_cursor", 0))
        self._manual_val_cursor = int(state.get("val_cursor", 0))
        train_bs = state.get("train_batch_size")
        val_bs = state.get("val_batch_size")
        self._curr_train_batch_size = int(train_bs) if train_bs is not None else None
        self._curr_val_batch_size = int(val_bs) if val_bs is not None else None
        self._train_loader = None
        self._train_iter = None
        self._val_loader = None
        self._val_iter = None

    @staticmethod
    def _stack_dataset_items(
        dataset: Dataset[Tuple[torch.Tensor, torch.Tensor]],
        indices: list[int],
        device: str,
        non_blocking: bool,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        items = [dataset[index] for index in indices]
        if not items:
            raise DatasetEmptyError("Không thể tạo batch rỗng từ DataLoaderBatchProvider.")
        xs, ys = zip(*items)
        x = torch.stack(list(xs))
        y = torch.stack(list(ys))
        return x.to(device, non_blocking=non_blocking), y.to(
            device, non_blocking=non_blocking
        )

    def _get_manual_train_batch(
        self, batch_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        size = len(self.train_dataset)  # type: ignore[arg-type]
        if size == 0:
            raise DatasetEmptyError("Tập dữ liệu huấn luyện rỗng!")
        if self._curr_train_batch_size != batch_size:
            self._curr_train_batch_size = batch_size
            self._manual_train_order = None
            self._manual_train_cursor = 0

        drop_last = size >= batch_size
        needs_new_order = self._manual_train_order is None or self._manual_train_cursor >= size
        if (
            not needs_new_order
            and drop_last
            and self._manual_train_cursor + batch_size > size
        ):
            needs_new_order = True
        if needs_new_order:
            self._manual_train_order = torch.randperm(size)
            self._manual_train_cursor = 0

        assert self._manual_train_order is not None
        end = min(size, self._manual_train_cursor + batch_size)
        indices = self._manual_train_order[self._manual_train_cursor : end].tolist()
        self._manual_train_cursor = end
        return self._stack_dataset_items(
            self.train_dataset, indices, device, self.pin_memory
        )

    def _get_manual_val_batch(
        self, batch_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        size = len(self.val_dataset)  # type: ignore[arg-type]
        if size == 0:
            raise DatasetEmptyError("Tập dữ liệu đánh giá rỗng!")
        if self._curr_val_batch_size != batch_size:
            self._curr_val_batch_size = batch_size
            self._manual_val_cursor = 0

        drop_last = size >= batch_size
        if self._manual_val_cursor >= size or (
            drop_last and self._manual_val_cursor + batch_size > size
        ):
            self._manual_val_cursor = 0
        end = min(size, self._manual_val_cursor + batch_size)
        indices = list(range(self._manual_val_cursor, end))
        self._manual_val_cursor = end
        return self._stack_dataset_items(
            self.val_dataset, indices, device, self.pin_memory
        )

    def get_train_batch(
        self, batch_size: int, block_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.supports_exact_resume:
            return self._get_manual_train_batch(batch_size, device)

        drop_last = False
        if isinstance(self.train_dataset, Sized):
            if len(self.train_dataset) == 0:
                raise DatasetEmptyError("Tập dữ liệu huấn luyện rỗng!")
            drop_last = len(self.train_dataset) >= batch_size

        if self._train_loader is None or self._curr_train_batch_size != batch_size:
            self._curr_train_batch_size = batch_size
            self._train_loader = DataLoader(
                self.train_dataset,
                batch_size=batch_size,
                shuffle=True,
                num_workers=self.num_workers,
                pin_memory=self.pin_memory,
                drop_last=drop_last,
            )
            self._train_iter = iter(self._train_loader)

        assert self._train_iter is not None
        try:
            x, y = next(self._train_iter)
        except StopIteration:
            self._train_iter = iter(self._train_loader)
            x, y = next(self._train_iter)

        return x.to(device, non_blocking=self.pin_memory), y.to(device, non_blocking=self.pin_memory)

    def get_val_batch(
        self, batch_size: int, block_size: int, device: str
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.supports_exact_resume:
            return self._get_manual_val_batch(batch_size, device)

        drop_last = False
        if isinstance(self.val_dataset, Sized):
            if len(self.val_dataset) == 0:
                raise DatasetEmptyError("Tập dữ liệu đánh giá rỗng!")
            drop_last = len(self.val_dataset) >= batch_size

        if self._val_loader is None or self._curr_val_batch_size != batch_size:
            self._curr_val_batch_size = batch_size
            self._val_loader = DataLoader(
                self.val_dataset,
                batch_size=batch_size,
                shuffle=False,
                num_workers=self.num_workers,
                pin_memory=self.pin_memory,
                drop_last=drop_last,
            )
            self._val_iter = iter(self._val_loader)

        assert self._val_iter is not None
        try:
            x, y = next(self._val_iter)
        except StopIteration:
            self._val_iter = iter(self._val_loader)
            x, y = next(self._val_iter)

        return x.to(device, non_blocking=self.pin_memory), y.to(device, non_blocking=self.pin_memory)


def get_batch_provider(
    provider_type: str,
    train_data: torch.Tensor,
    val_data: torch.Tensor,
    block_size: int = 64,
    num_workers: int = 0,
    pin_memory: bool = False,
) -> BaseBatchProvider:
    """Factory khởi tạo Batch Provider từ cấu hình ('tensor' hoặc 'dataloader')."""
    p_type = provider_type.lower().strip()
    if p_type in ("tensor", "memory", "in_memory"):
        return TensorBatchProvider(train_data=train_data, val_data=val_data)
    elif p_type in ("dataloader", "loader", "torch"):
        train_ds = TextDataset(train_data, block_size=block_size)
        val_ds = TextDataset(val_data, block_size=block_size)
        return DataLoaderBatchProvider(
            train_dataset=train_ds,
            val_dataset=val_ds,
            num_workers=num_workers,
            pin_memory=pin_memory,
        )
    else:
        raise DataPipelineError(
            f"Loại BatchProvider không được hỗ trợ: '{provider_type}'",
            details={"provider_type": provider_type},
            suggestion="Hãy chọn 'tensor' (nhanh cho in-memory) hoặc 'dataloader' (chuẩn PyTorch).",
        )


__all__ = [
    "BaseBatchProvider",
    "TensorBatchProvider",
    "DataLoaderBatchProvider",
    "get_batch_provider",
    "extract_tensor_batch",
]

