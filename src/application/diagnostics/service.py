"""Diagnostics application use cases over canonical configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from src.application.config import ConfigRequest
from src.application.config.service import ConfigurationService
from src.core.diagnostics import (
    DiagnosticsRunner,
    analyze_vram_scenarios,
    check_attention_backends,
    estimate_vram_budget,
    get_cpu_info,
    get_disk_info,
    get_gpu_info,
    get_memory_info,
    get_system_info,
    verify_directory_permissions,
)
from src.core.runtime import resolve_training_plan
from src.models.api import inspect_model


@dataclass(frozen=True)
class VramEstimateInput:
    device: str = "auto"
    model_name: Optional[str] = None
    batch_size: Optional[int] = None
    block_size: Optional[int] = None
    n_embd: Optional[int] = None
    n_layer: Optional[int] = None
    n_head: Optional[int] = None
    vocab_size: Optional[int] = None
    precision: Optional[str] = None
    optimizer_type: Optional[str] = None
    gradient_checkpointing: Optional[bool] = None
    gradient_accumulation_steps: Optional[int] = None
    intermediate_size: Optional[int] = None
    multiple_of: Optional[int] = None
    tie_word_embeddings: Optional[bool] = None
    bias: Optional[bool] = None


class DiagnosticsRuntimePort(Protocol):
    def run_quality_gates(self) -> Dict[str, Any]: ...
    def logs(self, lines: int = 80) -> Dict[str, Any]: ...


class DiagnosticsApplicationService:
    def __init__(
        self,
        config_service: ConfigurationService,
        runtime_adapter: Optional[DiagnosticsRuntimePort] = None,
    ) -> None:
        self.config_service = config_service
        self._runtime_adapter = runtime_adapter

    def run_quality_gates(self) -> Dict[str, Any]:
        if self._runtime_adapter is None:
            raise RuntimeError("Diagnostics runtime port chưa được cấu hình.")
        return self._runtime_adapter.run_quality_gates()

    def logs(self, lines: int = 80) -> Dict[str, Any]:
        if self._runtime_adapter is None:
            raise RuntimeError("Diagnostics runtime port chưa được cấu hình.")
        return self._runtime_adapter.logs(lines)

    def system(self) -> Dict[str, Any]:
        return {
            "cpu": get_cpu_info(),
            "memory": get_memory_info(),
            "gpu": get_gpu_info(),
            "system": get_system_info(),
        }

    def _effective_config(self, request: VramEstimateInput):
        base = self.config_service.current()
        model_kwargs = dict(base.model.model_kwargs)
        if request.multiple_of is not None:
            model_kwargs["multiple_of"] = request.multiple_of
        if request.intermediate_size is not None:
            model_kwargs["intermediate_size"] = request.intermediate_size

        model_updates: Dict[str, Any] = {"model_kwargs": model_kwargs}
        for field, value in (
            ("name", request.model_name.strip().lower() if request.model_name else None),
            ("vocab_size", request.vocab_size),
            ("block_size", request.block_size),
            ("n_embd", request.n_embd),
            ("n_layer", request.n_layer),
            ("n_head", request.n_head),
            ("tie_word_embeddings", request.tie_word_embeddings),
            ("bias", request.bias),
        ):
            if value is not None:
                model_updates[field] = value

        training_updates: Dict[str, Any] = {}
        for field, value in (
            ("batch_size", request.batch_size),
            ("precision", request.precision),
            ("optimizer_type", request.optimizer_type),
            ("gradient_checkpointing", request.gradient_checkpointing),
            ("gradient_accumulation_steps", request.gradient_accumulation_steps),
        ):
            if value is not None:
                training_updates[field] = value

        system = base.system.copy(device=(request.device or base.system.device).strip().lower())
        model = base.model.copy(**model_updates)
        training = base.training.copy(**training_updates)
        effective = base.copy(system=system, model=model, training=training)
        return effective

    def estimate(self, request: VramEstimateInput) -> Dict[str, Any]:
        config = self._effective_config(request)
        runtime_plan = resolve_training_plan(config)
        budget = estimate_vram_budget(
            model_config=config.model,
            training_config=config.training,
            runtime_plan=runtime_plan,
        )
        comps = budget.get("components_mb", {})
        budget["peak_vram_mb"] = budget.get("total_estimated_mb", 0.0)
        budget["peak_vram_gb"] = budget.get("total_estimated_gb", 0.0)
        budget["model_weights_mb"] = comps.get("parameters", 0.0)
        budget["gradients_mb"] = comps.get("gradients", 0.0)
        budget["optimizer_states_mb"] = comps.get("optimizer_states", 0.0)
        budget["activations_mb"] = comps.get("activations", 0.0)
        budget["cuda_overhead_mb"] = comps.get("cuda_context_overhead", 0.0)
        return budget

    def scenarios(self, request: VramEstimateInput):
        config = self._effective_config(request)
        return analyze_vram_scenarios(
            model_config=config.model,
            training_config=config.training,
            system_config=config.system,
        )

    def scenarios_from_config(self, source: Optional[str], overrides=()):
        config = self.config_service.resolve(
            ConfigRequest(source=source, overrides=tuple(overrides))
        )
        return analyze_vram_scenarios(
            model_config=config.model,
            training_config=config.training,
            system_config=config.system,
        )

    def advisor(self) -> Dict[str, Any]:
        runner = DiagnosticsRunner()
        report = runner.run(test_tensor_allocation=True)
        gpu = get_gpu_info()
        return {
            "gpu": gpu,
            "backends": check_attention_backends(),
            "disk": get_disk_info("."),
            "permissions": verify_directory_permissions(["logs", "checkpoints", "data", "configs"]),
            "recommendations": gpu.get("recommendations", {}),
            "health_status": report.status.value,
            "warnings": report.warnings,
            "suggestions": report.suggestions,
        }

    def inspect(
        self,
        *,
        source: Optional[str] = None,
        model_name: Optional[str] = None,
        n_embd: Optional[int] = None,
        n_head: Optional[int] = None,
        n_layer: Optional[int] = None,
        block_size: Optional[int] = None,
        overrides=(),
    ) -> Dict[str, Any]:
        config = self.config_service.resolve(
            ConfigRequest(source=source, overrides=tuple(overrides))
        )
        actual_model_name = (
            model_name.strip().lower() if model_name and model_name.strip() else config.model.name
        )
        model_updates: Dict[str, Any] = {"name": actual_model_name}
        for key, value in (
            ("n_embd", n_embd),
            ("n_head", n_head),
            ("n_layer", n_layer),
            ("block_size", block_size),
        ):
            if value is not None and value > 0:
                model_updates[key] = value
        model_config = config.model.copy(**model_updates)
        return inspect_model(actual_model_name, model_config)

    def report(self, *, test_tensor_allocation: bool = True) -> Dict[str, Any]:
        """Return a transport-neutral diagnostics report for outer renderers."""
        return DiagnosticsRunner().run(test_tensor_allocation=test_tensor_allocation).to_dict()
