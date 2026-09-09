"""HTTP boundary for structured core-domain errors."""

import logging
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.application.errors import AIEngineError, ErrorCode

logger = logging.getLogger("UIErrors")

_NOT_FOUND_CODES = {
    ErrorCode.CONFIG_NOT_FOUND,
    ErrorCode.DATA_FILE_NOT_FOUND,
    ErrorCode.MODEL_NOT_FOUND,
    ErrorCode.CHECKPOINT_NOT_FOUND,
}
_BAD_REQUEST_CODES = {
    ErrorCode.CONFIG_INVALID,
    ErrorCode.DATA_VOCAB_EMPTY,
    ErrorCode.DATA_CORPUS_EMPTY,
    ErrorCode.MODEL_SHAPE_MISMATCH,
    ErrorCode.MODEL_CONTEXT_EXCEEDED,
    ErrorCode.GEN_SAMPLING_FAILED,
    ErrorCode.GEN_BACKEND_NOT_FOUND,
    ErrorCode.GEN_EMPTY_PROMPT,
    ErrorCode.GEN_CONTEXT_EXCEEDED,
    ErrorCode.PROTO_VIOLATION,
    ErrorCode.PROTO_SIGNATURE_MISMATCH,
    ErrorCode.DIAG_VRAM_OVERFLOW,
}
_TOO_MANY_REQUESTS_CODES = {ErrorCode.GEN_BUSY}
_SERVICE_UNAVAILABLE_CODES = {ErrorCode.GEN_NOT_READY}
_CONFLICT_CODES = {ErrorCode.HARDWARE_BUSY}
_HARDWARE_CODES = {
    ErrorCode.HARDWARE_CUDA_UNAVAILABLE,
    ErrorCode.HARDWARE_OOM,
    ErrorCode.HARDWARE_PERMISSION,
    ErrorCode.HARDWARE_BUSY,
    ErrorCode.DIAG_HEALTH_FAILED,
}


def status_code_for_ai_error(error: AIEngineError) -> int:
    """Map stable domain error codes to HTTP without parsing localized messages."""
    if error.error_code in _NOT_FOUND_CODES:
        return 404
    if error.error_code in _BAD_REQUEST_CODES:
        return 400
    if error.error_code in _TOO_MANY_REQUESTS_CODES:
        return 429
    if error.error_code in _SERVICE_UNAVAILABLE_CODES:
        return 503
    if error.error_code in _CONFLICT_CODES:
        return 409
    if error.error_code in _HARDWARE_CODES:
        return 503
    return 500


def ai_engine_error_payload(error: AIEngineError) -> Dict[str, object]:
    """Return the typed public error payload used by all API consumers."""
    payload = error.to_dict()
    # Preserve the public taxonomy while avoiding nested exception internals in responses.
    payload.pop("cause", None)
    return payload


def register_ai_engine_error_handlers(app: FastAPI) -> None:
    """Install the single FastAPI boundary for all AIEngineError subclasses."""

    @app.exception_handler(AIEngineError)
    async def handle_ai_engine_error(request: Request, exc: AIEngineError) -> JSONResponse:
        status = status_code_for_ai_error(exc)
        logger.warning(
            "AIEngineError %s on %s %s: %s",
            exc.error_code,
            request.method,
            request.url.path,
            exc.message,
        )
        return JSONResponse(status_code=status, content=ai_engine_error_payload(exc))


__all__ = [
    "ai_engine_error_payload",
    "register_ai_engine_error_handlers",
    "status_code_for_ai_error",
]
