import pytest


def test_accelerator_coordinator_blocks_training_while_generation_is_reserved():
    from src.core.exceptions import AcceleratorBusyError
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator

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
    from src.core.exceptions import AcceleratorBusyError
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator

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
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_training("cpu")
    coordinator.reserve_generation("cpu")
    coordinator.release_training("cpu")
    coordinator.release_generation("cpu")


def test_inference_service_uses_shared_coordinator_for_generation(tmp_path):
    from src.core.config import GenerationConfig
    from src.core.exceptions import AcceleratorBusyError
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator
    from src.ui.services.inference_service import InferenceService

    class DummyTokenizer:
        def encode(self, text):
            return [1]

    class DummyGenerator:
        pass

    coordinator = AcceleratorCoordinator()
    service = InferenceService(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        accelerator_coordinator=coordinator,
    )
    service.device_str = "cuda"
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = DummyGenerator()  # type: ignore[assignment]

    coordinator.reserve_training("cuda")
    try:
        with pytest.raises(AcceleratorBusyError):
            service.begin_generation("hello", GenerationConfig(max_new_tokens=1))
    finally:
        coordinator.release_training("cuda")


def test_generation_session_holds_shared_reservation_until_close(tmp_path):
    from src.core.config import GenerationConfig
    from src.core.exceptions import AcceleratorBusyError
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator
    from src.ui.services.inference_service import InferenceService

    class DummyTokenizer:
        def encode(self, text):
            return [1]

    class DummyGenerator:
        pass

    coordinator = AcceleratorCoordinator()
    service = InferenceService(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        accelerator_coordinator=coordinator,
    )
    service.device_str = "cuda"
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = DummyGenerator()  # type: ignore[assignment]

    session = service.begin_generation("hello", GenerationConfig(max_new_tokens=1))
    with pytest.raises(AcceleratorBusyError):
        coordinator.reserve_training("cuda")
    session.close()
    coordinator.reserve_training("cuda")
    coordinator.release_training("cuda")


def test_training_start_reserves_shared_accelerator_before_entering_starting_state():
    from src.core.exceptions import AcceleratorBusyError
    from src.core.runtime import ResolvedTrainingPlan
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator
    from src.ui.services.training_service import TrainingService

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_generation("cuda")
    plan = ResolvedTrainingPlan(
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
    service = TrainingService(accelerator_coordinator=coordinator)
    try:
        with pytest.raises(AcceleratorBusyError):
            service.start_training(runtime_plan=plan)
        assert service.status == "IDLE"
    finally:
        coordinator.release_generation("cuda")


def test_idle_inference_residency_blocks_training_until_released():
    from src.core.exceptions import AcceleratorBusyError
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator

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
    from src.core.exceptions import AcceleratorBusyError
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_training("mps")
    try:
        with pytest.raises(AcceleratorBusyError):
            coordinator.reserve_inference_residency("mps")
    finally:
        coordinator.release_training("mps")
