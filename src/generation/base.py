"""
Base contracts and abstractions for the Text Generation subsystem.
"""

import threading
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
    finish_reason: str  # "length", "eos_token", "stop_sequence", "cancelled"
    prompt_tokens_input: int = 0
    prompt_tokens_used: int = 0
    prompt_truncated: bool = False

    def __str__(self) -> str:
        return self.text


class GenerationCancellation:
    """Small thread-safe cancellation primitive shared across API and generators."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


class BaseGenerator(ABC):
    """
    Lớp cơ sở trừu tượng cho mọi công cụ sinh văn bản (Inference Engine).
    Hỗ trợ cắm rút đa dạng: Mô hình PyTorch cục bộ, vLLM, TensorRT-LLM, hoặc Cloud APIs (Gemini/OpenAI).
    """

    @classmethod
    def from_inference_context(
        cls,
        *,
        model: Any,
        tokenizer: Any,
        device: str,
    ) -> "BaseGenerator":
        """Build a backend from the local inference context; remote backends may override."""
        return cls(model=model, tokenizer=tokenizer, device=device)  # type: ignore[call-arg]

    @overload
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        sampler: Optional[Any] = None,
        streamer: Optional[BaseStreamer] = None,
        *,
        cancellation: Optional[GenerationCancellation] = None,
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
        cancellation: Optional[GenerationCancellation] = None,
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
        cancellation: Optional[GenerationCancellation] = None,
        return_output: bool = False,
        **kwargs: Any,
    ) -> Union[str, GenerationOutput]:
        """Thực hiện suy luận sinh văn bản từ prompt đầu vào."""
        pass


__all__ = ["GenerationOutput", "GenerationCancellation", "BaseGenerator"]
