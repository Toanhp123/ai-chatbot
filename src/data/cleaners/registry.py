"""
Cơ chế điều phối và đăng ký bộ tiền xử lý/làm sạch văn bản (Cleaner Registry).
Trang bị:
- CleanerRegistry: Quản lý đăng ký động và khởi tạo linh kiện theo Open-Closed Principle (OCP).
- get_cleaner: Hàm factory tiện ích tra cứu từ Registry.
"""

from typing import Any, Callable, Dict, List, Type

from src.core.exceptions import DataPipelineError
from src.core.logging import get_logger
from src.data.cleaners.base import BaseTextPreprocessor

logger = get_logger("CleanerRegistry")


class CleanerRegistry:
    """Registry trung tâm đăng ký & khởi tạo các bộ tiền xử lý/làm sạch văn bản."""

    _registry: Dict[str, Type[BaseTextPreprocessor]] = {}

    @classmethod
    def register(cls, *names: str) -> Callable[[Any], Any]:
        """Decorator đăng ký một Preprocessor class với một hoặc nhiều tên định danh."""

        def decorator(subclass: Any) -> Any:
            for name in names:
                cls._registry[name.lower().strip()] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> BaseTextPreprocessor:
        """Khởi tạo một instance cleaner từ tên đăng ký."""
        name_clean = name.lower().strip()
        if name_clean in cls._registry:
            target_cls = cls._registry[name_clean]
            return target_cls(**kwargs)

        available = list(cls._registry.keys())
        raise DataPipelineError(
            f"Loại Cleaner không được hỗ trợ: '{name}' (Khả dụng: {available})",
            details={"requested_type": name, "available_types": available},
            suggestion=f"Hãy chọn một trong các loại: {available} hoặc đăng ký bằng @CleanerRegistry.register('{name}')",
        )

    @classmethod
    def list_available(cls) -> List[str]:
        """Danh sách tất cả các loại cleaner đã đăng ký."""
        return sorted(list(cls._registry.keys()))


def get_cleaner(cleaner_type: str = "default", **kwargs: Any) -> BaseTextPreprocessor:
    """Factory tiện ích tra cứu và khởi tạo Cleaner từ Registry."""
    return CleanerRegistry.create(cleaner_type, **kwargs)


__all__ = [
    "BaseTextPreprocessor",
    "CleanerRegistry",
    "get_cleaner",
]
