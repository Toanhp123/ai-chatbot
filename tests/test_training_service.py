from unittest.mock import Mock, patch

import torch

from src.core.config import EngineConfig
from src.core.runtime import RuntimeCapabilities, resolve_training_plan
from src.training.trainer import TrainOutput
from src.ui.services.training_service import TrainingService


def test_abort_before_trainer_creation_does_not_deadlock():
    service = TrainingService()
    config = EngineConfig()
    tokenizer = Mock(vocab_size=32)
    batch_provider = Mock()
    model = Mock()
    sample_generator = Mock()

    def create_model_and_request_abort(*args, **kwargs):
        service._abort_requested.set()
        return model

    with (
        patch(
            "src.ui.services.training_service.EngineConfig.from_yaml",
            return_value=config,
        ),
        patch(
            "src.ui.services.training_service.DataPipeline.setup_data",
            return_value=(torch.arange(64), torch.arange(32), tokenizer),
        ),
        patch(
            "src.ui.services.training_service.get_batch_provider",
            return_value=batch_provider,
        ),
        patch(
            "src.ui.services.training_service.ModelRegistry.create",
            side_effect=create_model_and_request_abort,
        ),
        patch(
            "src.ui.services.training_service.get_generator",
            return_value=sample_generator,
        ),
    ):
        service.start_training(config_path="unused.yaml")
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert not service._thread.is_alive()
    assert service.status == "STOPPED"
    assert service.trainer is None


def test_clear_state_waits_for_stopping_worker_before_committing_idle():
    import threading
    import time

    service = TrainingService()
    service.status = "STOPPING"

    def finish_old_worker():
        time.sleep(0.03)
        with service._lock:
            service.status = "STOPPED"

    worker = threading.Thread(target=finish_old_worker)
    service._thread = worker
    worker.start()

    service.clear_state()
    worker.join(timeout=1)

    assert service.status == "IDLE"


def test_training_worker_shares_one_runtime_plan_with_generator_and_trainer():
    service = TrainingService()
    config = EngineConfig()
    config = config.copy(system=config.system.copy(device="cpu"))
    runtime_plan = resolve_training_plan(
        config,
        capabilities=RuntimeCapabilities(
            cuda_available=False,
            mps_available=False,
            bf16_supported=False,
            bitsandbytes_available=False,
        ),
    )
    tokenizer = Mock(vocab_size=32)
    batch_provider = Mock()
    model = Mock()
    sample_generator = Mock()
    trainer_init = {}

    class FakeTrainer:
        def __init__(self, **kwargs):
            trainer_init.update(kwargs)

        def train(self, resume_checkpoint=None):
            return TrainOutput(
                global_step=1,
                total_steps=1,
                final_train_loss=0.0,
                interrupted=False,
            )

    with (
        patch(
            "src.ui.services.training_service.EngineConfig.from_yaml",
            return_value=config,
        ),
        patch(
            "src.ui.services.training_service.DataPipeline.setup_data",
            return_value=(torch.arange(64), torch.arange(32), tokenizer),
        ),
        patch(
            "src.ui.services.training_service.get_batch_provider",
            return_value=batch_provider,
        ),
        patch(
            "src.ui.services.training_service.ModelRegistry.create",
            return_value=model,
        ),
        patch(
            "src.ui.services.training_service.get_generator",
            return_value=sample_generator,
        ) as get_generator_mock,
        patch(
            "src.ui.services.training_service.resolve_training_plan",
            return_value=runtime_plan,
            create=True,
        ) as resolve_plan_mock,
        patch(
            "src.ui.services.training_service.resolve_device",
            return_value="legacy-device",
            create=True,
        ),
        patch("src.ui.services.training_service.Trainer", FakeTrainer),
    ):
        service.start_training(config_path="unused.yaml")
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert not service._thread.is_alive()
    resolve_plan_mock.assert_called_once()
    assert trainer_init["runtime_plan"] is runtime_plan
    assert get_generator_mock.call_args.kwargs["device"] == runtime_plan.device
