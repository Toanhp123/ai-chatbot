"""Stable public API for the model capability."""

from __future__ import annotations

from src.core.config import ModelConfig
from src.models.base import BaseModel
from src.models.registry import ModelRegistry


def create_model(name: str, config: ModelConfig) -> BaseModel:
    return ModelRegistry.create(name, config)


def inspect_model(name: str, config: ModelConfig, *, layer_limit: int = 35) -> dict[str, object]:
    """Materialize and summarize a model behind the stable model capability boundary."""
    model = ModelRegistry.create(name, config)
    layers: list[dict[str, object]] = []
    total_params = 0
    for parameter_name, parameter in model.named_parameters():
        count = parameter.numel()
        total_params += count
        layers.append(
            {
                "name": parameter_name,
                "shape": list(parameter.shape),
                "params": count,
                "trainable": parameter.requires_grad,
                "memory_kb": round((count * parameter.element_size()) / 1024, 2),
            }
        )
    return {
        "model_name": name,
        "total_parameters": total_params,
        "total_parameters_formatted": f"{total_params:,}",
        "vocab_size": config.vocab_size,
        "block_size": config.block_size,
        "n_embd": config.n_embd,
        "n_head": config.n_head,
        "n_layer": config.n_layer,
        "layers": layers[:layer_limit],
    }


def list_models() -> list[str]:
    return ModelRegistry.list_models()


__all__ = ["BaseModel", "create_model", "inspect_model", "list_models"]
