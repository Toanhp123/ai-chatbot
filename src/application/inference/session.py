"""Lifecycle object for one bounded, cancellable inference stream."""

from __future__ import annotations

import inspect
import json
import threading
import time
from typing import Any, Callable, Iterator, List, Optional

from src.core.config import GenerationConfig
from src.core.exceptions import AIEngineError, GenerationError
from src.core.logging import get_logger
from src.generation import (
    BaseGenerator,
    GenerationCancellation,
    GenerationOutput,
    TextIteratorStreamer,
)

logger = get_logger("GenerationSession")


class GenerationSession:
    """Own one request's snapshot, worker, cancellation and SSE lifecycle."""

    def __init__(
        self,
        *,
        generator_provider: Callable[[], BaseGenerator],
        prompt: str,
        config: GenerationConfig,
        execution_lock: threading.Lock,
        release_admission: Callable[[], None],
        streamer_timeout: float = 0.25,
    ) -> None:
        self.generator: Optional[BaseGenerator] = None
        self._generator_provider = generator_provider
        self.prompt = prompt
        self.config = config
        self.cancellation = GenerationCancellation()
        self.streamer = TextIteratorStreamer(timeout=streamer_timeout)
        self._execution_lock = execution_lock
        self._release_admission = release_admission
        self._thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()
        self._release_lock = threading.Lock()
        self._released = False
        self._generation_error: List[Exception] = []
        self._generation_output: List[GenerationOutput] = []
        self._tokens_emitted: List[str] = []
        self._started_at: Optional[float] = None

    def _release_once(self) -> None:
        with self._release_lock:
            if self._released:
                return
            self._released = True
        self._release_admission()

    @staticmethod
    def _generator_accepts_cancellation(generator: BaseGenerator) -> bool:
        try:
            signature = inspect.signature(generator.generate)
        except (TypeError, ValueError):
            return True
        parameters = signature.parameters.values()
        return "cancellation" in signature.parameters or any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters
        )

    def _run_worker(self) -> None:
        acquired = False
        try:
            while not self.cancellation.is_cancelled():
                if self._execution_lock.acquire(timeout=0.05):
                    acquired = True
                    break
            if not acquired or self.cancellation.is_cancelled():
                return

            generator = self._generator_provider()
            self.generator = generator
            kwargs: dict[str, Any] = {
                "prompt": self.prompt,
                "config": self.config,
                "streamer": self.streamer,
                "return_output": True,
            }
            if self._generator_accepts_cancellation(generator):
                kwargs["cancellation"] = self.cancellation
            result = generator.generate(**kwargs)
            if isinstance(result, GenerationOutput):
                self._generation_output.append(result)
        except Exception as exc:
            logger.exception("Lỗi worker suy luận: %s", exc)
            self._generation_error.append(exc)
        finally:
            self.streamer.on_finish()
            if acquired:
                self._execution_lock.release()
            self._release_once()

    def start(self) -> None:
        with self._start_lock:
            if self._thread is not None or self._released:
                return
            self._started_at = time.time()
            self._thread = threading.Thread(target=self._run_worker, daemon=True)
            self._thread.start()

    def close(self) -> None:
        """Cancel this request. Admission remains held until a started worker actually stops."""
        self.cancellation.cancel()
        self.streamer.cancel()
        with self._start_lock:
            thread = self._thread
        if thread is None:
            self._release_once()
            return
        if thread is not threading.current_thread():
            thread.join(timeout=1.0)

    @staticmethod
    def _error_payload(exc: Exception) -> dict[str, object]:
        if isinstance(exc, AIEngineError):
            payload = exc.to_dict()
        else:
            wrapped = GenerationError("Lỗi không mong đợi trong worker sinh văn bản.", cause=exc)
            payload = wrapped.to_dict()
        payload.pop("cause", None)
        payload["type"] = "error"
        return payload

    def iter_events(self) -> Iterator[dict[str, object]]:
        """Yield transport-neutral generation lifecycle events."""
        self.start()
        yield {"type": "start", "prompt": self.prompt}
        try:
            for token in self.streamer:
                self._tokens_emitted.append(token)
                yield {"type": "token", "token": token}

            thread = self._thread
            if thread is not None:
                thread.join(timeout=1.0)
                if thread.is_alive():
                    self.cancellation.cancel()
                    thread.join(timeout=1.0)
                    if thread.is_alive() and not self._generation_error:
                        self._generation_error.append(
                            GenerationError(
                                "Worker suy luận không dừng sau khi stream kết thúc.",
                                is_recoverable=True,
                            )
                        )

            if self._generation_error:
                yield self._error_payload(self._generation_error[0])
                return

            elapsed_wall = max(
                time.time() - (self._started_at if self._started_at is not None else time.time()),
                0.0,
            )
            if self._generation_output:
                output = self._generation_output[0]
                payload: dict[str, object] = {
                    "type": "done",
                    "full_text": output.text,
                    "generated_text": output.generated_text,
                    "token_count": output.tokens_generated,
                    "elapsed_sec": round(output.elapsed_time_sec, 3),
                    "tps": round(output.tokens_per_second, 2),
                    "finish_reason": output.finish_reason,
                    "prompt_tokens_input": output.prompt_tokens_input,
                    "prompt_tokens_used": output.prompt_tokens_used,
                    "prompt_truncated": output.prompt_truncated,
                }
            else:
                generated_text = "".join(self._tokens_emitted)
                token_count = len(self._tokens_emitted)
                payload = {
                    "type": "done",
                    "full_text": self.prompt + generated_text,
                    "generated_text": generated_text,
                    "token_count": token_count,
                    "elapsed_sec": round(elapsed_wall, 3),
                    "tps": round(token_count / elapsed_wall, 2) if elapsed_wall > 0 else 0.0,
                    "finish_reason": "length",
                    "prompt_tokens_input": 0,
                    "prompt_tokens_used": 0,
                    "prompt_truncated": False,
                }
            yield payload
        finally:
            self.close()

    def iter_sse(self) -> Iterator[str]:
        """Serialize transport-neutral events for the legacy SSE adapter."""
        for event in self.iter_events():
            yield f"data: {json.dumps(event)}\n\n"


__all__ = ["GenerationSession"]
