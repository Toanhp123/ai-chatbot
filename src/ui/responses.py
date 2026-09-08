"""HTTP response adapters for UI streaming lifecycles."""

from typing import Any

from fastapi.responses import StreamingResponse

from src.ui.services.generation_session import GenerationSession


class GenerationStreamingResponse(StreamingResponse):
    """Close the generation session on every ASGI transport exit, including disconnects."""

    def __init__(self, *, session: GenerationSession, **kwargs: Any) -> None:
        self.generation_session = session
        super().__init__(session.iter_sse(), **kwargs)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.generation_session.close()


__all__ = ["GenerationStreamingResponse"]
