"""
Bộ sinh văn bản tự hồi quy cục bộ sử dụng PyTorch (Local PyTorch Text Generator).
Hỗ trợ:
- Tối ưu hóa Key-Value Cache tăng tốc độ suy luận O(T).
- Chống lặp từ (Repetition Penalty).
- Điều kiện dừng tự nhiên (EOS Token & Stop Sequences).
- Lấy mẫu linh hoạt: Greedy Search, Top-K, Top-P, Min-P.
- Hỗ trợ đa dạng Streamer (ConsoleStreamer, TextIteratorStreamer).
- Đo đạc tốc độ suy luận (Tokens Per Second - TPS) và xuất metadata qua GenerationOutput.
- Đăng ký vào GeneratorRegistry với các bí danh: 'local', 'pytorch', 'default'.
"""

import inspect
import time
from typing import Any, List, Literal, Optional, Protocol, Union, cast, overload

import torch
import torch.nn as nn

from src.core.config import GenerationConfig
from src.generation.base import BaseGenerator, GenerationOutput
from src.generation.registry import GeneratorRegistry
from src.generation.samplers import (
    TopKTopPSampler,
    apply_repetition_penalty,
)
from src.generation.streamers import BaseStreamer
from src.utils.device import resolve_device


class _IncrementalDecoder(Protocol):
    def push(self, tokens: List[int]) -> str: ...

    def finish(self) -> str: ...


@GeneratorRegistry.register("local", "pytorch", "default")
class TextGenerator(BaseGenerator):
    """Bộ sinh văn bản tự hồi quy cục bộ sử dụng mô hình PyTorch."""

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        device: str = "auto",
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.device = resolve_device(device)
        if isinstance(self.model, nn.Module):
            self.model.to(self.device)
            self.model.eval()
        try:
            signature = inspect.signature(self.model.forward)
            self._supports_use_cache = "use_cache" in signature.parameters or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in signature.parameters.values()
            )
        except (TypeError, ValueError):
            self._supports_use_cache = True

    def _call_model(self, x: torch.Tensor, use_cache: bool) -> Any:
        """Call the model once; never hide an internal TypeError by retrying forward."""
        forward = self.model if callable(self.model) else getattr(self.model, "forward")
        if self._supports_use_cache:
            return forward(x, use_cache=use_cache)
        return forward(x)

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

    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        sampler: Optional[Any] = None,
        streamer: Optional[BaseStreamer] = None,
        return_output: bool = False,
        **kwargs: Any,
    ) -> Union[str, GenerationOutput]:
        """
        Thực hiện sinh văn bản tự hồi quy:
        - prompt: Chuỗi gợi ý đầu vào.
        - config: Cấu hình siêu tham số sinh văn bản (GenerationConfig).
        - sampler: Bộ lấy mẫu tùy biến (nếu None sẽ dùng TopKTopPSampler từ config).
        - streamer: Bộ truyền luồng thời gian thực (BaseStreamer).
        - return_output: Nếu False trả về chuỗi str thuần túy; nếu True trả về GenerationOutput.
        """
        if config is None:
            config = GenerationConfig()

        if sampler is None:
            sampler = TopKTopPSampler(
                temperature=config.temperature,
                top_k=config.top_k,
                top_p=config.top_p,
                min_p=config.min_p,
                do_sample=config.do_sample,
            )

        tokens = self.tokenizer.encode(prompt)
        if not tokens:
            tokens = [0]

        idx = torch.tensor([tokens], dtype=torch.long, device=self.device)
        if streamer:
            streamer.on_prompt(prompt)

        reset_fn = getattr(self.model, "reset_kv_cache", None)
        if callable(reset_fn):
            reset_fn()

        stop_sequences: List[List[int]] = []
        if config.stop_sequences:
            stop_sequences.extend(
                [list(sequence) for sequence in config.stop_sequences if sequence]
            )
        if config.stop_tokens:
            stop_sequences.extend([[token] for token in config.stop_tokens])
        max_stop_len = max((len(sequence) for sequence in stop_sequences), default=1)

        generated_token_ids: List[int] = []
        generated_chars: List[str] = []
        streamed_token_count = 0
        decoder_factory = getattr(self.tokenizer, "create_incremental_decoder", None)
        decoder: Optional[_IncrementalDecoder] = (
            cast(_IncrementalDecoder, decoder_factory()) if callable(decoder_factory) else None
        )
        block_size: int = int(getattr(self.model, "block_size", 1024))
        use_cache = config.use_cache and callable(getattr(self.model, "reset_kv_cache", None))
        finish_reason = "length"
        was_training = bool(getattr(self.model, "training", False))
        if isinstance(self.model, nn.Module):
            self.model.eval()

        def emit_tokens(token_chunk: List[int]) -> None:
            if not token_chunk:
                return
            text = (
                decoder.push(token_chunk)
                if decoder is not None
                else self.tokenizer.decode(token_chunk)
            )
            if text:
                generated_chars.append(text)
                if streamer:
                    streamer.on_token(text)

        start_time = time.time()
        try:
            for step in range(config.max_new_tokens):
                if use_cache and idx.size(1) <= block_size:
                    idx_cond = idx if step == 0 else idx[:, [-1]]
                    model_out = self._call_model(idx_cond, use_cache=True)
                else:
                    idx_cond = idx if idx.size(1) <= block_size else idx[:, -block_size:]
                    model_out = self._call_model(idx_cond, use_cache=False)

                logits = cast(
                    torch.Tensor,
                    model_out[0] if isinstance(model_out, tuple) else model_out,
                )

                if config.repetition_penalty > 1.0:
                    context_tokens = idx[0].tolist()
                    logits = apply_repetition_penalty(
                        logits, context_tokens, penalty=config.repetition_penalty
                    )

                next_token = sampler.sample(logits[:, -1, :])
                next_token_id = int(next_token.item())

                if config.eos_token_id is not None and next_token_id == config.eos_token_id:
                    finish_reason = "eos_token"
                    break

                next_token_tensor = torch.tensor(
                    [[next_token_id]], dtype=torch.long, device=self.device
                )
                idx = torch.cat((idx, next_token_tensor), dim=1)
                generated_token_ids.append(next_token_id)

                matched_stop: Optional[List[int]] = None
                for sequence in stop_sequences:
                    if (
                        len(generated_token_ids) >= len(sequence)
                        and generated_token_ids[-len(sequence) :] == sequence
                    ):
                        matched_stop = sequence
                        break
                if matched_stop is not None:
                    del generated_token_ids[-len(matched_stop) :]
                    finish_reason = "stop_sequence"
                    break

                safe_end = max(0, len(generated_token_ids) - (max_stop_len - 1))
                if safe_end > streamed_token_count:
                    emit_tokens(generated_token_ids[streamed_token_count:safe_end])
                    streamed_token_count = safe_end

            if len(generated_token_ids) > streamed_token_count:
                emit_tokens(generated_token_ids[streamed_token_count:])
                streamed_token_count = len(generated_token_ids)
            if decoder is not None:
                tail = decoder.finish()
                if tail:
                    generated_chars.append(tail)
                    if streamer:
                        streamer.on_token(tail)

        finally:
            cleanup_fn = getattr(self.model, "reset_kv_cache", None)
            if callable(cleanup_fn):
                cleanup_fn()
            if isinstance(self.model, nn.Module) and was_training:
                self.model.train()

        if streamer:
            streamer.on_finish()

        elapsed_time = time.time() - start_time
        tokens_count = len(generated_token_ids)
        tps = float(tokens_count) / max(elapsed_time, 1e-6)
        generated_text = "".join(generated_chars)
        full_text = prompt + generated_text

        if return_output:
            return GenerationOutput(
                text=full_text,
                prompt=prompt,
                generated_text=generated_text,
                token_ids=generated_token_ids,
                tokens_generated=tokens_count,
                tokens_per_second=tps,
                elapsed_time_sec=elapsed_time,
                finish_reason=finish_reason,
            )

        return full_text


# Bí danh mở rộng
LocalTextGenerator = TextGenerator

__all__ = ["TextGenerator", "LocalTextGenerator", "GenerationOutput"]
