"""
Model Registry: Quản lý đăng ký kiến trúc mô hình (Factory Pattern).
Cho phép mở rộng kiến trúc mới mà không sửa đổi Trainer hay CLI.
Tự động khám phá (Auto-discovery) các kiến trúc có sẵn trong thư mục architectures/.
"""

import importlib
import pkgutil
from typing import Callable, Dict, List, Type

from src.core.config import ModelConfig
from src.core.exceptions import ModelArchitectureError, ModelNotFoundError
from src.models.base import BaseModel


class ModelRegistry:
    """Registry trung tâm quản lý và khởi tạo các kiến trúc mô hình ngôn ngữ."""

    _registry: Dict[str, Type[BaseModel]] = {}

    @classmethod
    def _ensure_builtins(cls) -> None:
        """Tự động quét và nạp toàn bộ các kiến trúc mô hình trong package architectures."""
        try:
            import src.models.architectures as arch_pkg

            for _, module_name, _ in pkgutil.iter_modules(arch_pkg.__path__):
                if not module_name.startswith("_"):
                    importlib.import_module(f"src.models.architectures.{module_name}")
        except Exception:
            pass

    @classmethod
    def register(cls, *names: str) -> Callable[[Type[BaseModel]], Type[BaseModel]]:
        """Decorator đăng ký kiến trúc mô hình mới vào hệ thống với một hoặc nhiều tên gọi."""

        def decorator(subclass: Type[BaseModel]) -> Type[BaseModel]:
            for name in names:
                name_clean = name.lower().strip()
                if name_clean in cls._registry:
                    raise ModelArchitectureError(
                        f"Mô hình với tên '{name_clean}' đã được đăng ký trước đó!"
                    )
                cls._registry[name_clean] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, name: str, config: ModelConfig) -> BaseModel:
        """Tạo instance của mô hình dựa theo tên và cấu hình."""
        name_lower = name.lower().strip()
        if name_lower not in cls._registry:
            cls._ensure_builtins()

        if name_lower not in cls._registry:
            raise ModelNotFoundError(
                model_name=name,
                available_models=list(cls._registry.keys()),
            )
        model_cls = cls._registry[name_lower]
        return model_cls(config)

    @classmethod
    def list_models(cls) -> List[str]:
        """Danh sách tên tất cả các mô hình đã đăng ký."""
        cls._ensure_builtins()
        return sorted(list(cls._registry.keys()))


__all__ = ["ModelRegistry"]
