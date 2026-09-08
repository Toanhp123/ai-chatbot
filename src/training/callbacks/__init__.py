"""
Package Callbacks chuẩn hóa cho quá trình huấn luyện mô hình ngôn ngữ.
Cung cấp các công cụ giám sát, lưu trữ checkpoint, dừng sớm và sinh văn bản mẫu
tuân thủ nguyên tắc Single Responsibility và bảo đảm an toàn kiểu dữ liệu (Strict Typing).
"""

from src.training.callbacks.base import BaseCallback, TrainerProtocol
from src.training.callbacks.checkpoint import ModelCheckpointCallback
from src.training.callbacks.early_stopping import EarlyStoppingCallback
from src.training.callbacks.progress import ConsoleProgressCallback
from src.training.callbacks.sample import SampleGenerationCallback

__all__ = [
    "BaseCallback",
    "TrainerProtocol",
    "ConsoleProgressCallback",
    "ModelCheckpointCallback",
    "EarlyStoppingCallback",
    "SampleGenerationCallback",
]
