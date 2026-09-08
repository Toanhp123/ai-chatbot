"""
Generator Registry: Quản lý và khởi tạo các backend sinh văn bản (Factory Pattern).
Hỗ trợ đa bí danh, tự động khám phá và cắm rút linh hoạt giữa Local PyTorch, API, hoặc vLLM.
"""

import importlib
import inspect
from typing import Any, Callable, Dict, List, Type, TypeVar

from src.core.exceptions import (
    AIEngineError,
    GeneratorBackendNotFoundError,
    SignatureMismatchError,
)
from src.generation.base import BaseGenerator

T = TypeVar("T", bound=BaseGenerator)


class GeneratorRegistry:
    """Registry trung tâm quản lý và khởi tạo các công cụ sinh văn bản (Generators)."""

    _registry: Dict[str, Type[BaseGenerator]] = {}

    @classmethod
    def _ensure_builtins(cls) -> None:
        """Tự động nạp generator mặc định (TextGenerator)."""
        importlib.import_module("src.generation.generator")

    @classmethod
    def register(cls, *names: str) -> Callable[[Type[T]], Type[T]]:
        """Decorator đăng ký Generator mới vào hệ thống với một hoặc nhiều tên gọi."""

        def decorator(subclass: Type[T]) -> Type[T]:
            signature = inspect.signature(subclass.generate)
            accepts_cancellation = "cancellation" in signature.parameters or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in signature.parameters.values()
            )
            if not accepts_cancellation:
                raise SignatureMismatchError(
                    method_name=f"{subclass.__name__}.generate",
                    reason="generator backend phải nhận tham số cancellation hoặc **kwargs",
                )
            for name in names:
                name_clean = name.lower().strip()
                if name_clean in cls._registry:
                    raise AIEngineError(
                        f"Generator với tên '{name_clean}' đã được đăng ký trước đó!"
                    )
                cls._registry[name_clean] = subclass
            return subclass

        return decorator

    @classmethod
    def get(cls, name: str) -> Type[BaseGenerator]:
        """Lấy lớp Generator class theo tên định danh."""
        name_clean = name.lower().strip()
        if name_clean not in cls._registry:
            cls._ensure_builtins()

        if name_clean not in cls._registry:
            available = list(cls._registry.keys())
            raise GeneratorBackendNotFoundError(name, available)
        return cls._registry[name_clean]

    @classmethod
    def create(cls, name: str, *args: Any, **kwargs: Any) -> BaseGenerator:
        """Khởi tạo một Generator instance theo tên định danh và các tham số khởi tạo."""
        generator_cls = cls.get(name)
        return generator_cls(*args, **kwargs)

    @classmethod
    def create_for_inference(
        cls,
        name: str,
        *,
        model: Any,
        tokenizer: Any,
        device: str,
    ) -> BaseGenerator:
        """Create a backend through its inference-context factory hook."""
        generator_cls = cls.get(name)
        return generator_cls.from_inference_context(
            model=model,
            tokenizer=tokenizer,
            device=device,
        )

    @classmethod
    def list_generators(cls) -> List[str]:
        """Danh sách tên các Generator đang được đăng ký."""
        cls._ensure_builtins()
        return sorted(list(cls._registry.keys()))


def get_generator(backend: str = "local", *args: Any, **kwargs: Any) -> BaseGenerator:
    """Hàm tiện ích nhanh để khởi tạo Generator theo tên backend."""
    return GeneratorRegistry.create(backend, *args, **kwargs)


__all__ = ["GeneratorRegistry", "get_generator"]
