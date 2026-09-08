"""
Cấu hình đường ống dữ liệu (Data Pipeline Configuration).
Hỗ trợ cấu hình hóa toàn bộ Cleaner, Tokenizer, và BatchProvider theo nguyên lý Open-Closed.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.core.config.base import BaseConfig
from src.core.exceptions import ConfigurationError


@dataclass
class DataConfig(BaseConfig):
    data_dir: str = "data"
    input_file: str = "data/input.txt"
    vocab_file: str = "data/vocab.json"
    source_url: Optional[str] = None
    split_ratio: float = 0.9
    clean_line_numbers: bool = True
    cleaner_type: str = "default"
    cleaner_kwargs: Dict[str, Any] = field(default_factory=dict)
    tokenizer_type: str = "char"
    tokenizer_kwargs: Dict[str, Any] = field(default_factory=dict)
    batch_provider_type: str = "tensor"
    num_workers: int = 0
    pin_memory: bool = True

    def validate(self) -> None:
        if not (0.0 < self.split_ratio < 1.0):
            raise ConfigurationError(
                f"split_ratio phải nằm trong khoảng (0.0, 1.0), nhận được {self.split_ratio}",
                {"split_ratio": self.split_ratio},
            )
        if not self.data_dir:
            raise ConfigurationError("data_dir không được để trống!")
        if not self.input_file:
            raise ConfigurationError("input_file không được để trống!")
        if not self.vocab_file:
            raise ConfigurationError("vocab_file không được để trống!")
        if not self.cleaner_type or not isinstance(self.cleaner_type, str):
            raise ConfigurationError("cleaner_type phải là chuỗi ký tự không rỗng!")
        if not self.tokenizer_type or not isinstance(self.tokenizer_type, str):
            raise ConfigurationError("tokenizer_type phải là chuỗi ký tự không rỗng!")
        if self.batch_provider_type not in ("tensor", "memory", "dataloader", "torch"):
            raise ConfigurationError(
                f"batch_provider_type không hợp lệ: '{self.batch_provider_type}'",
                {"batch_provider_type": self.batch_provider_type},
            )
        if self.num_workers < 0:
            raise ConfigurationError(f"num_workers phải >= 0, nhận được {self.num_workers}")
        if not isinstance(self.pin_memory, bool):
            raise ConfigurationError(
                f"pin_memory phải là boolean, nhận được {type(self.pin_memory).__name__}"
            )
