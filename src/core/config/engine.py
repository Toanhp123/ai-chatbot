"""
Cấu hình tổng hợp cấp cao cho toàn bộ AI Engine (Engine Configuration Aggregator).
Kết hợp tất cả các domain configs (System, Data, Model, Training, Generation).
Hỗ trợ giải mã biến môi trường (${ENV_VAR:-default}) và ghi đè động CLI (dot-notation).
"""

import copy
import difflib
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence

import yaml

from src.core.config.base import BaseConfig
from src.core.config.data import DataConfig
from src.core.config.generation import GenerationConfig
from src.core.config.model import ModelConfig
from src.core.config.system import SystemConfig
from src.core.config.training import TrainingConfig
from src.core.exceptions import ConfigurationError


def interpolate_env_vars(text: str) -> str:
    """Thay thế các biến môi trường dạng ${VAR} hoặc ${VAR:-default} trong chuỗi."""

    def _replace_env(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default_val = match.group(2)
        if var_name in os.environ:
            return os.environ[var_name]
        if default_val is not None:
            return default_val
        raise ConfigurationError(
            f"Biến môi trường '${{{var_name}}}' chưa được định nghĩa và không có giá trị mặc định."
        )

    pattern = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-([^}]*))?\}")
    return pattern.sub(_replace_env, text)


def parse_cli_value(val_str: str) -> Any:
    """Tự động suy luận kiểu dữ liệu (bool, int, float, str) cho giá trị ghi đè."""
    s = val_str.strip()
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("none", "null"):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def apply_overrides(data: Dict[str, Any], overrides: Sequence[str]) -> Dict[str, Any]:
    """Áp dụng danh sách các quy tắc ghi đè dạng 'section.key=value' vào dictionary cấu hình."""
    result = copy.deepcopy(data)
    for override in overrides:
        if "=" not in override:
            raise ConfigurationError(
                f"Cú pháp ghi đè không hợp lệ: '{override}'. Định dạng yêu cầu: 'section.key=value'"
            )
        key_path, raw_val = override.split("=", 1)
        keys = [k.strip() for k in key_path.strip().split(".") if k.strip()]
        if not keys:
            raise ConfigurationError(f"Khóa ghi đè không hợp lệ trong: '{override}'")

        val = parse_cli_value(raw_val)
        curr = result
        for k in keys[:-1]:
            if k not in curr or not isinstance(curr[k], dict):
                curr[k] = {}
            curr = curr[k]
        curr[keys[-1]] = val

    return result


@dataclass
class EngineConfig(BaseConfig):
    system: SystemConfig = field(default_factory=SystemConfig)
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)

    def validate(self) -> None:
        self.system.validate()
        self.data.validate()
        self.model.validate()
        self.training.validate()
        self.generation.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EngineConfig":
        valid_domains = {"system", "data", "model", "training", "generation"}
        unknown_domains = [k for k in data if k not in valid_domains]
        if unknown_domains:
            suggestions = []
            for u in unknown_domains:
                matches = difflib.get_close_matches(u, list(valid_domains), n=1, cutoff=0.6)
                if matches:
                    suggestions.append(f"'{u}' (có phải ý bạn là '{matches[0]}'?)")
                else:
                    suggestions.append(f"'{u}'")
            sugg_str = ", ".join(suggestions)
            valid_str = ", ".join(sorted(valid_domains))
            raise ConfigurationError(
                f"Phát hiện domain cấu hình không xác định trong EngineConfig: [{sugg_str}]. "
                f"Các domain hợp lệ: [{valid_str}].",
                {"unknown_domains": unknown_domains},
            )

        system_data = dict(data.get("system", {}) or {})
        training_data = dict(data.get("training", {}) or {})
        legacy_mixed_precision = system_data.pop("mixed_precision", None)
        if legacy_mixed_precision is not None and not isinstance(legacy_mixed_precision, bool):
            raise ConfigurationError("system.mixed_precision legacy phải là boolean.")
        if legacy_mixed_precision is True and "precision" not in training_data:
            training_data["precision"] = "amp_fp16"

        system_cfg = SystemConfig.from_kwargs_safe(system_data)
        data_cfg = DataConfig.from_kwargs_safe(data.get("data", {}) or {})
        model_cfg = ModelConfig.from_kwargs_safe(data.get("model", {}) or {})
        train_cfg = TrainingConfig.from_kwargs_safe(training_data)
        gen_cfg = GenerationConfig.from_kwargs_safe(data.get("generation", {}) or {})

        cfg = cls(
            system=system_cfg,
            data=data_cfg,
            model=model_cfg,
            training=train_cfg,
            generation=gen_cfg,
        )
        cfg.validate()
        return cfg

    @classmethod
    def from_yaml(cls, filepath: str, overrides: Optional[Sequence[str]] = None) -> "EngineConfig":
        if not os.path.exists(filepath):
            raise ConfigurationError(f"Không tìm thấy file cấu hình tại: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            interpolated = interpolate_env_vars(content)
            parsed_dict = yaml.safe_load(interpolated)
            if parsed_dict is None:
                parsed_dict = {}
            if not isinstance(parsed_dict, dict):
                raise ConfigurationError(
                    f"Nội dung file cấu hình {filepath} phải là một dictionary/mapping YAML."
                )
            if overrides:
                parsed_dict = apply_overrides(parsed_dict, overrides)
            return cls.from_dict(parsed_dict)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Lỗi phân tích cú pháp YAML trong file {filepath}: {e}")
