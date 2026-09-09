import pytest

from tests.application_support import (
    concrete_inference_runtime,
    make_inference_service,
    make_training_service,
)


def test_accelerator_coordinator_blocks_training_while_generation_is_reserved():
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.exceptions import AcceleratorBusyError

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_generation("cuda")
    try:
        with pytest.raises(AcceleratorBusyError):
            coordinator.reserve_training("cuda")
    finally:
        coordinator.release_generation("cuda")

    coordinator.reserve_training("cuda")
    coordinator.release_training("cuda")


def test_accelerator_coordinator_blocks_generation_while_training_is_reserved():
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.exceptions import AcceleratorBusyError

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_training("mps")
    try:
        with pytest.raises(AcceleratorBusyError):
            coordinator.reserve_generation("mps")
    finally:
        coordinator.release_training("mps")

    coordinator.reserve_generation("mps")
    coordinator.release_generation("mps")


def test_cpu_reservations_do_not_conflict_or_require_release():
    from src.core.accelerator import AcceleratorCoordinator

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_training("cpu")
    coordinator.reserve_generation("cpu")
    coordinator.release_training("cpu")
    coordinator.release_generation("cpu")


def test_inference_service_uses_shared_coordinator_for_generation(tmp_path):
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.config import GenerationConfig
    from src.core.exceptions import AcceleratorBusyError

    class DummyTokenizer:
        def encode(self, text):
            return [1]

    class DummyGenerator:
        pass

    coordinator = AcceleratorCoordinator()
    service = make_inference_service(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        accelerator_coordinator=coordinator,
    )
    concrete_inference_runtime(service).device = "cuda"
    concrete_inference_runtime(service).tokenizer = DummyTokenizer()  # type: ignore[assignment]
    concrete_inference_runtime(service).generator = DummyGenerator()  # type: ignore[assignment]

    coordinator.reserve_training("cuda")
    try:
        with pytest.raises(AcceleratorBusyError):
            service.begin_generation("hello", GenerationConfig(max_new_tokens=1))
    finally:
        coordinator.release_training("cuda")


def test_generation_session_holds_shared_reservation_until_close(tmp_path):
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.config import GenerationConfig
    from src.core.exceptions import AcceleratorBusyError

    class DummyTokenizer:
        def encode(self, text):
            return [1]

    class DummyGenerator:
        pass

    coordinator = AcceleratorCoordinator()
    service = make_inference_service(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        accelerator_coordinator=coordinator,
    )
    concrete_inference_runtime(service).device = "cuda"
    concrete_inference_runtime(service).tokenizer = DummyTokenizer()  # type: ignore[assignment]
    concrete_inference_runtime(service).generator = DummyGenerator()  # type: ignore[assignment]

    session = service.begin_generation("hello", GenerationConfig(max_new_tokens=1))
    with pytest.raises(AcceleratorBusyError):
        coordinator.reserve_training("cuda")
    session.close()
    coordinator.reserve_training("cuda")
    coordinator.release_training("cuda")


def test_training_start_reserves_shared_accelerator_before_entering_starting_state():
    from src.application.training.contracts import TrainingFeasibility, TrainingPlan
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.config import EngineConfig
    from src.core.exceptions import AcceleratorBusyError
    from src.core.runtime import ResolvedTrainingPlan

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_generation("cuda")
    runtime_plan = ResolvedTrainingPlan(
        requested_device="cuda",
        device="cuda",
        device_type="cuda",
        requested_precision="float32",
        precision="float32",
        use_amp=False,
        requested_optimizer="adamw",
        optimizer_type="adamw",
        micro_batch_size=1,
        gradient_accumulation_steps=1,
        effective_batch_size=1,
        gradient_checkpointing=False,
    )
    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cuda"))
    plan = TrainingPlan(
        requested_config=config,
        config=config,
        runtime_plan=runtime_plan,
        feasibility=TrainingFeasibility(True, "ok", 0.0, 0.0),
    )
    service = make_training_service(accelerator_coordinator=coordinator)
    try:
        with pytest.raises(AcceleratorBusyError):
            service.start_training(plan=plan)
        assert service.status == "IDLE"
    finally:
        coordinator.release_generation("cuda")


def test_idle_inference_residency_blocks_training_until_released():
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.exceptions import AcceleratorBusyError

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_inference_residency("cuda:0")
    try:
        with pytest.raises(AcceleratorBusyError):
            coordinator.reserve_training("cuda:1")
    finally:
        coordinator.release_inference_residency("cuda:0")

    coordinator.reserve_training("cuda")
    coordinator.release_training("cuda")


def test_training_blocks_new_inference_residency():
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.exceptions import AcceleratorBusyError

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_training("mps")
    try:
        with pytest.raises(AcceleratorBusyError):
            coordinator.reserve_inference_residency("mps")
    finally:
        coordinator.release_training("mps")


def test_accelerator_coordinator_atomically_transfers_inference_residency_to_training():
    from src.core.accelerator import AcceleratorCoordinator

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_inference_residency("cuda:0")

    coordinator.transfer_inference_to_training("cuda")

    assert coordinator.snapshot()["cuda"] == {
        "training": True,
        "generation": 0,
        "inference_residency": 0,
    }

    coordinator.transfer_training_to_inference("cuda:1")
    assert coordinator.snapshot()["cuda"] == {
        "training": False,
        "generation": 0,
        "inference_residency": 1,
    }


def test_training_start_does_not_leak_admission_when_state_changes_before_commit(monkeypatch):
    from src.application.training.contracts import TrainingFeasibility, TrainingPlan
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.config import EngineConfig
    from src.core.runtime import RuntimeCapabilities, resolve_training_plan

    coordinator = AcceleratorCoordinator()
    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cuda"))
    runtime_plan = resolve_training_plan(
        config,
        capabilities=RuntimeCapabilities(
            cuda_available=True,
            mps_available=False,
            bf16_supported=False,
            bitsandbytes_available=False,
        ),
    )
    plan = TrainingPlan(
        requested_config=config,
        config=config,
        runtime_plan=runtime_plan,
        feasibility=TrainingFeasibility(True, "ok", 0.0, 0.0),
    )
    service = make_training_service(accelerator_coordinator=coordinator)

    original_from_dict = EngineConfig.from_dict
    calls = {"count": 0}

    def race_during_freeze(value):
        calls["count"] += 1
        result = original_from_dict(value)
        if calls["count"] == 2:
            service.status = "STARTING"
        return result

    monkeypatch.setattr(EngineConfig, "from_dict", staticmethod(race_during_freeze))

    with pytest.raises(RuntimeError, match="STARTING"):
        service.start_training(plan=plan)

    assert coordinator.snapshot() == {}
