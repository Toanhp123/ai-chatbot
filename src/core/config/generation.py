"""
Cấu hình suy luận và sinh văn bản (Generation Configuration).
"""

from dataclasses import dataclass
from typing import List, Optional

from src.core.config.base import BaseConfig
from src.core.exceptions import ConfigurationError


@dataclass
class GenerationConfig(BaseConfig):
    max_new_tokens: int = 250
    temperature: float = 0.75
    top_k: Optional[int] = 40
    top_p: Optional[float] = 0.9
    min_p: Optional[float] = None
    repetition_penalty: float = 1.0
    do_sample: bool = True
    eos_token_id: Optional[int] = None
    stop_tokens: Optional[List[int]] = None
    use_cache: bool = True

    def validate(self) -> None:
        if self.max_new_tokens <= 0:
            raise ConfigurationError(f"max_new_tokens phải > 0, nhận được {self.max_new_tokens}")
        if self.temperature < 0.0:
            raise ConfigurationError(f"temperature phải >= 0.0, nhận được {self.temperature}")
        if self.top_p is not None and (self.top_p <= 0.0 or self.top_p > 1.0):
            raise ConfigurationError(
                f"top_p phải nằm trong khoảng (0.0, 1.0], nhận được {self.top_p}",
                {"top_p": self.top_p},
            )
        if self.min_p is not None and (self.min_p < 0.0 or self.min_p > 1.0):
            raise ConfigurationError(
                f"min_p phải nằm trong khoảng [0.0, 1.0], nhận được {self.min_p}"
            )
        if self.top_k is not None and self.top_k < 0:
            raise ConfigurationError(f"top_k phải >= 0 hoặc None, nhận được {self.top_k}")
        if self.repetition_penalty < 1.0:
            raise ConfigurationError(
                f"repetition_penalty phải >= 1.0, nhận được {self.repetition_penalty}"
            )
        if not isinstance(self.use_cache, bool):
            raise ConfigurationError(
                f"use_cache phải là kiểu boolean, nhận được {type(self.use_cache).__name__}"
            )
