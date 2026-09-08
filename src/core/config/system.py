"""
Cấu hình hệ thống phần cứng, môi trường và nhật ký (System Configuration).
"""

from dataclasses import dataclass

from src.core.config.base import BaseConfig
from src.core.exceptions import ConfigurationError


@dataclass
class SystemConfig(BaseConfig):
    seed: int = 1337
    device: str = "auto"  # "auto", "cuda", "mps", "cpu"
    log_level: str = "INFO"
    log_file: str = "logs/engine.log"

    def validate(self) -> None:
        if self.device not in ["auto", "cuda", "mps", "cpu"]:
            raise ConfigurationError(
                f"Thiết bị '{self.device}' không hợp lệ. Phải là 'auto', 'cuda', 'mps', hoặc 'cpu'",
                {"device": self.device},
            )
        if self.log_level.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ConfigurationError(
                f"Mức log '{self.log_level}' không hợp lệ.", {"log_level": self.log_level}
            )
