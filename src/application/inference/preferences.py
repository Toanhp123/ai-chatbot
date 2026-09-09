"""Canonical inference preference ownership.

Keeps mutable user preferences separate from loaded inference runtime state.  A
shared ConfigurationService remains the only active-config authority; standalone
inference owns a private full EngineConfig snapshot.
"""

from __future__ import annotations

from typing import Optional

from src.application.config import ConfigurationService
from src.core.config import EngineConfig, GenerationConfig


class InferencePreferences:
    def __init__(
        self,
        config: EngineConfig,
        *,
        config_service: Optional[ConfigurationService] = None,
    ) -> None:
        config.validate()
        self._config_service = config_service
        self._private_config = ConfigurationService.snapshot(config)
        self._device_override: Optional[str] = None

    def snapshot(self) -> EngineConfig:
        if self._config_service is not None:
            return self._config_service.current()
        return ConfigurationService.snapshot(self._private_config)

    def activate(self, config: EngineConfig) -> EngineConfig:
        config.validate()
        snapshot = ConfigurationService.snapshot(config)
        self._private_config = snapshot
        if self._config_service is not None:
            self._config_service.activate(snapshot)
        return snapshot

    @property
    def checkpoint_dir(self) -> str:
        return self.snapshot().training.checkpoint_dir

    @checkpoint_dir.setter
    def checkpoint_dir(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("checkpoint_dir không được để trống.")
        config = self.snapshot()
        self.activate(config.copy(training=config.training.copy(checkpoint_dir=value)))

    @property
    def checkpoint_name(self) -> str:
        return self.snapshot().training.checkpoint_name

    @checkpoint_name.setter
    def checkpoint_name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("checkpoint_name không được để trống.")
        config = self.snapshot()
        self.activate(config.copy(training=config.training.copy(checkpoint_name=value)))

    @property
    def vocab_path(self) -> str:
        return self.snapshot().data.vocab_file

    @vocab_path.setter
    def vocab_path(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("vocab_path không được để trống.")
        config = self.snapshot()
        self.activate(config.copy(data=config.data.copy(vocab_file=value)))

    @property
    def configured_device(self) -> str:
        return self._device_override or self.snapshot().system.device

    @configured_device.setter
    def configured_device(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("configured_device không được để trống.")
        self._device_override = value

    @property
    def default_generation_config(self) -> GenerationConfig:
        return GenerationConfig.from_kwargs_safe(self.snapshot().generation.to_dict())

    @default_generation_config.setter
    def default_generation_config(self, value: GenerationConfig) -> None:
        config = self.snapshot()
        generation = GenerationConfig.from_kwargs_safe(value.to_dict())
        self.activate(config.copy(generation=generation))

    def apply_engine_config(self, config: EngineConfig) -> None:
        self._device_override = None
        self.activate(config)


__all__ = ["InferencePreferences"]
