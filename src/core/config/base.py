import difflib
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, fields, is_dataclass, replace
from typing import Any, Dict, Type, TypeVar

import yaml

from src.core.exceptions import ConfigurationError

T = TypeVar("T", bound="BaseConfig")


@dataclass
class BaseConfig(ABC):
    """Lớp trừu tượng cơ sở cho mọi cấu hình domain trong hệ thống."""

    @abstractmethod
    def validate(self) -> None:
        """Xác thực tính hợp lệ của các giá trị cấu hình."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi dataclass thành Dictionary chuẩn."""
        if is_dataclass(self):
            return asdict(self)
        return {}

    def to_yaml(self, filepath: str) -> None:
        """Xuất cấu hình ra file định dạng YAML."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, sort_keys=False)

    def copy(self: T, **overrides: Any) -> T:
        """Tạo bản sao cấu hình với các trường ghi đè tùy chọn (immutable update)."""
        return replace(self, **overrides)

    @classmethod
    def from_kwargs_safe(cls: Type[T], data: Dict[str, Any], ignore_unknown: bool = False) -> T:
        """Khởi tạo instance an toàn từ dictionary, lọc trường hợp lệ và phát hiện lỗi gõ nhầm (typo)."""
        try:
            cls_fields = fields(cls)
        except TypeError:
            raise ConfigurationError(f"Lớp {cls.__name__} không phải là dataclass hợp lệ.")

        known_fields = {f.name for f in cls_fields}

        safe_kwargs: Dict[str, Any] = {}
        unknown_fields = []

        for key, val in data.items():
            if key in known_fields:
                safe_kwargs[key] = val
            else:
                unknown_fields.append(key)

        if unknown_fields and not ignore_unknown:
            suggestions = []
            for u in unknown_fields:
                matches = difflib.get_close_matches(u, list(known_fields), n=1, cutoff=0.6)
                if matches:
                    suggestions.append(f"'{u}' (có phải ý bạn là '{matches[0]}'?)")
                else:
                    suggestions.append(f"'{u}'")

            sugg_str = ", ".join(suggestions)
            valid_str = ", ".join(sorted(list(known_fields)))
            raise ConfigurationError(
                f"Phát hiện trường cấu hình không xác định trong {cls.__name__}: [{sugg_str}]. "
                f"Các trường hợp lệ: [{valid_str}].",
                {"class": cls.__name__, "unknown_fields": unknown_fields},
            )

        instance = cls(**safe_kwargs)
        instance.validate()
        return instance
