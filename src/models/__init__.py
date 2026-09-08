"""Public model API with lazy exports to avoid package-initialization dependency cycles."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.models.architectures.llama import LlamaNano
    from src.models.architectures.minigpt import MiniGPT
    from src.models.base import BaseModel
    from src.models.layers import (
        CausalSelfAttention,
        FeedForward,
        LlamaAttention,
        LlamaBlock,
        RMSNorm,
        RotaryEmbedding,
        SwiGLUFeedForward,
        TransformerBlock,
        apply_rotary_emb,
    )
    from src.models.registry import ModelRegistry

_EXPORTS = {
    "BaseModel": ("src.models.base", "BaseModel"),
    "ModelRegistry": ("src.models.registry", "ModelRegistry"),
    "CausalSelfAttention": ("src.models.layers", "CausalSelfAttention"),
    "LlamaAttention": ("src.models.layers", "LlamaAttention"),
    "FeedForward": ("src.models.layers", "FeedForward"),
    "SwiGLUFeedForward": ("src.models.layers", "SwiGLUFeedForward"),
    "TransformerBlock": ("src.models.layers", "TransformerBlock"),
    "LlamaBlock": ("src.models.layers", "LlamaBlock"),
    "RMSNorm": ("src.models.layers", "RMSNorm"),
    "RotaryEmbedding": ("src.models.layers", "RotaryEmbedding"),
    "apply_rotary_emb": ("src.models.layers", "apply_rotary_emb"),
    "MiniGPT": ("src.models.architectures.minigpt", "MiniGPT"),
    "LlamaNano": ("src.models.architectures.llama", "LlamaNano"),
}

__all__ = [
    "BaseModel",
    "ModelRegistry",
    "CausalSelfAttention",
    "LlamaAttention",
    "FeedForward",
    "SwiGLUFeedForward",
    "TransformerBlock",
    "LlamaBlock",
    "RMSNorm",
    "RotaryEmbedding",
    "apply_rotary_emb",
    "MiniGPT",
    "LlamaNano",
]


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
