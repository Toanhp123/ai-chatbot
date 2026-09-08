from unittest.mock import Mock, patch

import torch

from src.core.config import EngineConfig
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
