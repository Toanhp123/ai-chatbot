"""
Cấu hình kiến trúc mô hình nơ-ron ngôn ngữ (Model Architecture Configuration).
"""

from dataclasses import dataclass, field
from typing import Any, Dict

from src.core.config.base import BaseConfig
from src.core.exceptions import ConfigurationError


@dataclass
class ModelConfig(BaseConfig):
    name: str = "minigpt"
    vocab_size: int = 129
    block_size: int = 128
    n_embd: int = 192
    n_head: int = 6
    n_layer: int = 4
    dropout: float = 0.1
    tie_word_embeddings: bool = True
    bias: bool = False
    model_kwargs: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.vocab_size <= 0:
            raise ConfigurationError(f"vocab_size phải > 0, nhận được {self.vocab_size}")
        if self.block_size <= 0:
            raise ConfigurationError(f"block_size phải > 0, nhận được {self.block_size}")
        if self.n_embd <= 0:
            raise ConfigurationError(f"n_embd phải > 0, nhận được {self.n_embd}")
        if self.n_head <= 0:
            raise ConfigurationError(f"n_head phải > 0, nhận được {self.n_head}")
        if self.n_embd % self.n_head != 0:
            raise ConfigurationError(
                f"n_embd ({self.n_embd}) phải chia hết cho n_head ({self.n_head})",
                {"n_embd": self.n_embd, "n_head": self.n_head},
            )
        if self.n_layer <= 0:
            raise ConfigurationError(f"n_layer phải > 0, nhận được {self.n_layer}")
        if not (0.0 <= self.dropout < 1.0):
            raise ConfigurationError(
                f"dropout phải nằm trong khoảng [0.0, 1.0), nhận được {self.dropout}"
            )
        if not isinstance(self.tie_word_embeddings, bool):
            raise ConfigurationError(
                f"tie_word_embeddings phải là kiểu boolean, nhận được {type(self.tie_word_embeddings).__name__}"
            )
        if not isinstance(self.bias, bool):
            raise ConfigurationError(
                f"bias phải là kiểu boolean, nhận được {type(self.bias).__name__}"
            )
        if not isinstance(self.model_kwargs, dict):
            raise ConfigurationError(
                f"model_kwargs phải là một dictionary, nhận được {type(self.model_kwargs).__name__}"
            )
