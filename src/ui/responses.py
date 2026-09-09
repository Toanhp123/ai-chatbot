"""HTTP response adapters for UI streaming lifecycles."""

import json
from typing import Any, Iterable, Iterator, Mapping

from fastapi.responses import StreamingResponse

from src.application.inference import GenerationStream


def iter_sse_events(events: Iterable[Mapping[str, object]]) -> Iterator[str]:
    """Render transport-neutral application events as SSE frames."""
    for event in events:
        if event.get("type") == "heartbeat":
            yield f": heartbeat {event.get('timestamp', '')}\n\n"
        else:
            yield f"data: {json.dumps(dict(event))}\n\n"


class GenerationStreamingResponse(StreamingResponse):
    """Close the generation session on every ASGI transport exit, including disconnects."""

    def __init__(self, *, session: GenerationStream, **kwargs: Any) -> None:
        self.generation_session = session
        super().__init__(iter_sse_events(session.iter_events()), **kwargs)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.generation_session.close()


class TrainingStreamingResponse(StreamingResponse):
    """Render training application events without leaking SSE into Application."""

    def __init__(self, *, events: Iterable[Mapping[str, object]], **kwargs: Any) -> None:
        super().__init__(iter_sse_events(events), **kwargs)


__all__ = ["GenerationStreamingResponse", "TrainingStreamingResponse", "iter_sse_events"]
