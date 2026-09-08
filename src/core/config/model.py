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

        model_name = self.name.lower().strip()
        if model_name in {"llama", "llama_nano"}:
            head_dim = self.n_embd // self.n_head
            if head_dim % 2 != 0:
                raise ConfigurationError(
                    "LLaMA yêu cầu head_dim chẵn để áp dụng Rotary Position Embedding.",
                    {"head_dim": head_dim, "n_embd": self.n_embd, "n_head": self.n_head},
                )

            raw_multiple_of = self.model_kwargs.get("multiple_of", 64)
            if isinstance(raw_multiple_of, bool):
                raise ConfigurationError("LLaMA multiple_of phải là số nguyên > 0.")
            try:
                multiple_of = int(raw_multiple_of)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError("LLaMA multiple_of phải là số nguyên > 0.") from exc
            if multiple_of <= 0:
                raise ConfigurationError(f"LLaMA multiple_of phải > 0, nhận được {raw_multiple_of}")

            raw_norm_eps = self.model_kwargs.get("norm_eps", 1e-6)
            if isinstance(raw_norm_eps, bool):
                raise ConfigurationError("LLaMA norm_eps phải là số thực > 0.")
            try:
                norm_eps = float(raw_norm_eps)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError("LLaMA norm_eps phải là số thực > 0.") from exc
            if norm_eps <= 0.0:
                raise ConfigurationError(f"LLaMA norm_eps phải > 0, nhận được {raw_norm_eps}")

            if "intermediate_size" in self.model_kwargs:
                raw_intermediate = self.model_kwargs["intermediate_size"]
                if isinstance(raw_intermediate, bool):
                    raise ConfigurationError("LLaMA intermediate_size phải là số nguyên >= 0.")
                try:
                    intermediate_size = int(raw_intermediate)
                except (TypeError, ValueError) as exc:
                    raise ConfigurationError(
                        "LLaMA intermediate_size phải là số nguyên >= 0."
                    ) from exc
                if intermediate_size < 0:
                    raise ConfigurationError(
                        f"LLaMA intermediate_size phải >= 0, nhận được {raw_intermediate}"
                    )
