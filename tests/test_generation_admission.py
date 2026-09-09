from typing import Any, Literal, Optional, Union, overload

import pytest

from src.core.config import GenerationConfig
from src.core.exceptions import GenerationBusyError
from src.data.tokenizers import BaseTokenizer
from src.generation import (
    BaseGenerator,
    BaseStreamer,
    GenerationCancellation,
    GenerationOutput,
)


class _Tokenizer(BaseTokenizer):
    @property
    def vocab_size(self) -> int:
        return 256

    def encode(self, text: str) -> list[int]:
        return [ord(ch) for ch in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(token) for token in tokens)

    def save_vocab(self, filepath: str) -> None:
        return None


class _Generator(BaseGenerator):
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
        if not return_output:
            return prompt
        return GenerationOutput(
            text=prompt,
            prompt=prompt,
            generated_text="",
            token_ids=[],
            tokens_generated=0,
            tokens_per_second=0.0,
            elapsed_time_sec=0.0,
            finish_reason="length",
        )


def test_generation_admission_manager_owns_session_limit_and_release():
    from src.application.inference.generation_admission import GenerationAdmissionManager

    manager = GenerationAdmissionManager(max_sessions=1)
    release = manager.acquire(
        prompt="hello",
        config=GenerationConfig(max_new_tokens=1),
        device="cpu",
    )

    assert manager.active_sessions == 1
    with pytest.raises(GenerationBusyError):
        manager.acquire(
            prompt="second",
            config=GenerationConfig(max_new_tokens=1),
            device="cpu",
        )

    release()
    release()
    assert manager.active_sessions == 0
