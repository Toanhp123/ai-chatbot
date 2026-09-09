"""Checkpoint artifact materialization for inference runtime swaps."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import torch

from src.application.inference.checkpoint_catalog import identity_from_stat
from src.core.config import ModelConfig
from src.data.tokenizers import BaseTokenizer, load_tokenizer, load_tokenizer_state
from src.data.tokenizers.base import get_tokenizer_identity
from src.models.base import BaseModel
from src.models.registry import ModelRegistry


@dataclass(frozen=True)
class LoadedCheckpointArtifacts:
    identity: tuple[int, int, int, int]
    tokenizer: BaseTokenizer
    model: BaseModel


def load_checkpoint_artifacts(
    checkpoint_path: str,
    *,
    vocab_path: str,
    fallback_tokenizer: Optional[BaseTokenizer],
) -> LoadedCheckpointArtifacts:
    """Load and validate checkpoint-bound CPU artifacts without publishing runtime state."""
    with open(checkpoint_path, "rb") as checkpoint_file:
        loaded_identity = identity_from_stat(os.fstat(checkpoint_file.fileno()))
        checkpoint = torch.load(checkpoint_file, map_location="cpu", weights_only=True)

    if not isinstance(checkpoint, dict):
        raise ValueError("Checkpoint không có payload mapping hợp lệ.")
    checkpoint_identity = checkpoint.get("tokenizer_identity")
    if not isinstance(checkpoint_identity, dict):
        raise ValueError(
            "Checkpoint legacy không có tokenizer identity; từ chối nạp để tránh ánh xạ token sai."
        )

    checkpoint_version = int(checkpoint.get("checkpoint_version", 1))
    embedded_state = checkpoint.get("tokenizer_state")
    if checkpoint_version >= 3 and not isinstance(embedded_state, dict):
        raise ValueError("Checkpoint v3 thiếu tokenizer state bắt buộc.")
    if isinstance(embedded_state, dict):
        tokenizer = load_tokenizer_state(embedded_state)
    else:
        tokenizer = load_tokenizer(vocab_path) if os.path.exists(vocab_path) else fallback_tokenizer
    if tokenizer is None:
        raise ValueError("Không thể nạp checkpoint khi chưa có tokenizer/từ vựng tương ứng.")

    current_identity = get_tokenizer_identity(tokenizer)
    if checkpoint_identity.get("fingerprint") != current_identity.get("fingerprint"):
        raise ValueError("Tokenizer/từ vựng hiện tại không khớp tokenizer identity của checkpoint.")

    cfg_dict = checkpoint.get("config", {}).get("model", {})
    model_config = ModelConfig.from_kwargs_safe(cfg_dict, ignore_unknown=True)
    model = ModelRegistry.create(model_config.name, model_config)
    if isinstance(model, torch.nn.Module):
        model.load_state_dict(checkpoint["model_state_dict"])

    return LoadedCheckpointArtifacts(
        identity=loaded_identity,
        tokenizer=tokenizer,
        model=model,
    )


__all__ = ["LoadedCheckpointArtifacts", "load_checkpoint_artifacts"]
