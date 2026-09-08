"""
Package Generation: Dịch vụ và công cụ suy luận văn bản tự hồi quy.
Hỗ trợ Kiến trúc Cắm rút Đa Backend (GeneratorRegistry), KV-Cache, Streaming,
Samplers nâng cao (Greedy, Top-K, Top-P, Min-P) và Chống lặp từ.
"""

from src.generation.base import BaseGenerator, GenerationCancellation, GenerationOutput
from src.generation.generator import LocalTextGenerator, TextGenerator
from src.generation.registry import GeneratorRegistry, get_generator
from src.generation.samplers import (
    TopKTopPSampler,
    apply_repetition_penalty,
    sample_next_token,
)
from src.generation.streamers import (
    BaseStreamer,
    ConsoleStreamer,
    TextIteratorStreamer,
)

__all__ = [
    "BaseGenerator",
    "GeneratorRegistry",
    "get_generator",
    "LocalTextGenerator",
    "TextGenerator",
    "GenerationOutput",
    "GenerationCancellation",
    "TopKTopPSampler",
    "sample_next_token",
    "apply_repetition_penalty",
    "BaseStreamer",
    "ConsoleStreamer",
    "TextIteratorStreamer",
]
