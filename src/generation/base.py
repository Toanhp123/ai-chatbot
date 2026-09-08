"""
Base contracts and abstractions for the Text Generation subsystem.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Literal, Optional, Union, overload

from src.core.config import GenerationConfig
from src.generation.streamers import BaseStreamer


@dataclass
class GenerationOutput:
    """Đối tượng đóng gói toàn diện kết quả và chỉ số suy luận văn bản."""

    text: str
    prompt: str
    generated_text: str
    token_ids: List[int]
    tokens_generated: int
    tokens_per_second: float
    elapsed_time_sec: float
    finish_reason: str  # "length", "eos_token", "stop_sequence"

    def __str__(self) -> str:
        return self.text


class BaseGenerator(ABC):
    """
    Lớp cơ sở trừu tượng cho mọi công cụ sinh văn bản (Inference Engine).
    Hỗ trợ cắm rút đa dạng: Mô hình PyTorch cục bộ, vLLM, TensorRT-LLM, hoặc Cloud APIs (Gemini/OpenAI).
    """

    @overload
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        sampler: Optional[Any] = None,
        streamer: Optional[BaseStreamer] = None,
        *,
        return_output: Literal[True],
        **kwargs: Any,
    ) -> GenerationOutput: ...

    @overload
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        sampler: Optional[Any] = None,
        streamer: Optional[BaseStreamer] = None,
        return_output: Literal[False] = False,
        **kwargs: Any,
    ) -> str: ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        sampler: Optional[Any] = None,
        streamer: Optional[BaseStreamer] = None,
        return_output: bool = False,
        **kwargs: Any,
    ) -> Union[str, GenerationOutput]:
        """Thực hiện suy luận sinh văn bản từ prompt đầu vào."""
        pass


__all__ = ["GenerationOutput", "BaseGenerator"]
