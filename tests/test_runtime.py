import pytest

from src.core.config import EngineConfig
from src.core.exceptions import ConfigurationError, CudaUnavailableError, HardwareError
from src.core.runtime import RuntimeCapabilities, resolve_training_plan, validate_training_plan


def _capabilities(
    *,
    cuda: bool = False,
    mps: bool = False,
    bf16: bool = False,
    bitsandbytes: bool = False,
) -> RuntimeCapabilities:
    return RuntimeCapabilities(
        cuda_available=cuda,
        mps_available=mps,
        bf16_supported=bf16,
        bitsandbytes_available=bitsandbytes,
    )


def test_runtime_plan_resolves_auto_device_once() -> None:
    config = EngineConfig()
    config.system.device = "auto"

    plan = resolve_training_plan(config, capabilities=_capabilities(cuda=True, bf16=True))

    assert plan.requested_device == "auto"
    assert plan.device == "cuda"
    assert plan.device_type == "cuda"


def test_runtime_plan_rejects_explicit_unavailable_cuda() -> None:
    config = EngineConfig()
    config.system.device = "cuda"

    with pytest.raises(CudaUnavailableError):
        resolve_training_plan(config, capabilities=_capabilities(cuda=False))


def test_runtime_plan_rejects_explicit_unavailable_mps() -> None:
    config = EngineConfig()
    config.system.device = "mps"

    with pytest.raises(HardwareError, match="MPS"):
        resolve_training_plan(config, capabilities=_capabilities(mps=False))


def test_runtime_plan_falls_back_precision_to_float32_on_cpu() -> None:
    config = EngineConfig()
    config.system.device = "cpu"
    config.training.precision = "amp_fp16"

    plan = resolve_training_plan(config, capabilities=_capabilities())

    assert plan.requested_precision == "amp_fp16"
    assert plan.precision == "float32"
    assert plan.use_amp is False
    assert any("precision" in reason.lower() for reason in plan.fallback_reasons)


def test_runtime_plan_falls_back_8bit_optimizer_when_dependency_missing() -> None:
    config = EngineConfig()
    config.training.optimizer_type = "8bit_adamw"

    plan = resolve_training_plan(config, capabilities=_capabilities(cuda=True, bitsandbytes=False))

    assert plan.requested_optimizer == "8bit_adamw"
    assert plan.optimizer_type == "adamw"
    assert any("bitsandbytes" in reason.lower() for reason in plan.fallback_reasons)


def test_runtime_plan_uses_configured_batch_as_micro_batch() -> None:
    config = EngineConfig()
    config.training.batch_size = 16
    config.training.gradient_accumulation_steps = 4

    plan = resolve_training_plan(config, capabilities=_capabilities())

    assert plan.micro_batch_size == 16
    assert plan.gradient_accumulation_steps == 4
    assert plan.effective_batch_size == 64


def test_runtime_plan_rejects_stale_training_config() -> None:
    config = EngineConfig()
    plan = resolve_training_plan(config, capabilities=_capabilities())
    changed = config.copy(training=config.training.copy(batch_size=8))

    with pytest.raises(ConfigurationError, match="runtime plan"):
        validate_training_plan(changed, plan)
