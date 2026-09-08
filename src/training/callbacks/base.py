"""
Base contracts and protocols for the training callback system.
Provides strict typing via TrainerProtocol to eliminate coupling with Trainer implementation.
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class TrainerProtocol(Protocol):
    """
    Hợp đồng giao tiếp an toàn (PEP 544 Protocol) cho các Callbacks.
    Giúp Callbacks truy cập các thông tin cần thiết mà không phụ thuộc
    trực tiếp vào lớp Trainer cụ thể (phá vỡ coupling, đảm bảo Type Safety).
    """

    @property
    def current_lr(self) -> float:
        """Learning rate hiện tại."""
        ...

    @property
    def max_iters(self) -> int:
        """Tổng số bước huấn luyện tối đa."""
        ...

    @property
    def should_stop(self) -> bool:
        """Cờ báo hiệu dừng sớm."""
        ...

    def request_stop(self) -> None:
        """Yêu cầu dừng huấn luyện sớm một cách an toàn."""
        ...

    def get_model_state_dict(self) -> Dict[str, Any]:
        """Lấy state dict của mô hình."""
        ...

    def get_optimizer_state_dict(self) -> Optional[Dict[str, Any]]:
        """Lấy state dict của optimizer nếu có."""
        ...

    def get_config_dict(self) -> Dict[str, Any]:
        """Lấy cấu hình huấn luyện dưới dạng dict thuần túy."""
        ...


class BaseCallback:
    """Lớp cơ sở (Abstract Base Class) cho tất cả các Callbacks trong hệ thống."""

    def on_train_begin(self, trainer: TrainerProtocol) -> None:
        """Được gọi khi bắt đầu phiên huấn luyện."""
        pass

    def on_step_end(self, trainer: TrainerProtocol, step: int, loss: float) -> None:
        """Được gọi sau mỗi bước huấn luyện (sau optimizer.step)."""
        pass

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: Dict[str, float]) -> None:
        """Được gọi sau khi hoàn thành chu kỳ đánh giá (evaluate)."""
        pass

    def on_train_end(self, trainer: TrainerProtocol) -> None:
        """Được gọi khi kết thúc toàn bộ quá trình huấn luyện."""
        pass


__all__ = ["TrainerProtocol", "BaseCallback"]
