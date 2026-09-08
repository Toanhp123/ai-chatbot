import os
import tempfile

import torch

from src.core.config import EngineConfig
from src.data.batch_provider import BaseBatchProvider
from src.models.registry import ModelRegistry
from src.training.callbacks import ModelCheckpointCallback
from src.training.trainer import Trainer, TrainOutput


class MockBatchProvider(BaseBatchProvider):
    def __init__(self, vocab_size: int) -> None:
        self.vocab_size = vocab_size

    def get_train_batch(self, batch_size: int, block_size: int, device: str):
        x = torch.randint(0, self.vocab_size, (batch_size, block_size), device=device)
        y = torch.randint(0, self.vocab_size, (batch_size, block_size), device=device)
        return x, y

    def get_val_batch(self, batch_size: int, block_size: int, device: str):
        x = torch.randint(0, self.vocab_size, (batch_size, block_size), device=device)
        y = torch.randint(0, self.vocab_size, (batch_size, block_size), device=device)
        return x, y


def test_trainer_smoke_steps_with_batch_provider():
    """Kiểm thử Trainer hoạt động độc lập qua BaseBatchProvider."""
    config = EngineConfig()
    config.model.vocab_size = 30
    config.model.block_size = 16
    config.model.n_embd = 32
    config.model.n_head = 2
    config.model.n_layer = 1

    config.training.batch_size = 4
    config.training.max_iters = 5
    config.training.eval_interval = 5
    config.training.eval_iters = 2
    config.training.warmup_iters = 2

    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)

    trainer = Trainer(model=model, batch_provider=provider, config=config, device="cpu")

    trainer.train()
    assert True


def test_trainer_smoke_steps_with_tensor_data():
    """Kiểm thử Trainer hoạt động với cặp tensor truyền vào (backward compatibility)."""
    config = EngineConfig()
    config.model.vocab_size = 30
    config.model.block_size = 16
    config.model.n_embd = 32
    config.model.n_head = 2
    config.model.n_layer = 1

    config.training.batch_size = 4
    config.training.max_iters = 5
    config.training.eval_interval = 5
    config.training.eval_iters = 2
    config.training.warmup_iters = 2

    model = ModelRegistry.create("minigpt", config.model)

    dummy_data = torch.randint(0, config.model.vocab_size, (200,))
    train_data = dummy_data[:150]
    val_data = dummy_data[150:]

    trainer = Trainer(
        model=model, train_data=train_data, val_data=val_data, config=config, device="cpu"
    )

    trainer.train()
    assert True


def test_trainer_gradient_accumulation_and_optimizer():
    """Kiểm thử Trainer với Gradient Accumulation > 1 và optimizer SGD."""
    config = EngineConfig()
    config.model.vocab_size = 30
    config.model.block_size = 16
    config.model.n_embd = 32
    config.model.n_head = 2
    config.model.n_layer = 1

    config.training.batch_size = 2
    config.training.gradient_accumulation_steps = 2
    config.training.optimizer_type = "sgd"
    config.training.max_iters = 4
    config.training.eval_interval = 2
    config.training.eval_iters = 1

    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)

    trainer = Trainer(model=model, batch_provider=provider, config=config, device="cpu")
    assert isinstance(trainer.optimizer, torch.optim.SGD)

    trainer.train()
    assert True


def test_trainer_checkpoint_and_resume():
    """Kiểm thử lưu trạng thái optimizer và khôi phục huấn luyện từ checkpoint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = EngineConfig()
        config.model.vocab_size = 30
        config.model.block_size = 16
        config.model.n_embd = 32
        config.model.n_head = 2
        config.model.n_layer = 1

        config.training.batch_size = 2
        config.training.max_iters = 3
        config.training.eval_interval = 3
        config.training.eval_iters = 1

        ckpt_cb = ModelCheckpointCallback(save_dir=tmpdir, filename="test_ckpt.pt")
        model = ModelRegistry.create("minigpt", config.model)
        provider = MockBatchProvider(config.model.vocab_size)

        trainer = Trainer(
            model=model,
            batch_provider=provider,
            config=config,
            callbacks=[ckpt_cb],
            device="cpu",
        )
        trainer.train()

        ckpt_path = os.path.join(tmpdir, "test_ckpt.pt")
        assert os.path.exists(ckpt_path)

        state = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        assert "optimizer_state_dict" in state
        assert state["optimizer_state_dict"] is not None
        assert state["step"] == 3

        # Phục hồi vào một Trainer mới
        config.training.max_iters = 5
        new_model = ModelRegistry.create("minigpt", config.model)
        resume_trainer = Trainer(
            model=new_model,
            batch_provider=provider,
            config=config,
            device="cpu",
        )
        resume_trainer.train(resume_checkpoint=ckpt_path)
        assert resume_trainer.start_step == 4


def test_trainer_custom_optimizer_injection():
    """Kiểm thử Trainer chấp nhận custom optimizer được inject từ bên ngoài và trả về TrainOutput."""
    config = EngineConfig()
    config.model.vocab_size = 20
    config.model.block_size = 8
    config.model.n_embd = 16
    config.model.n_head = 2
    config.model.n_layer = 1
    config.training.max_iters = 2
    config.training.eval_interval = 2

    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)
    custom_optim = torch.optim.Adagrad(model.parameters(), lr=0.05)

    trainer = Trainer(
        model=model,
        batch_provider=provider,
        config=config,
        optimizer=custom_optim,
        device="cpu",
    )
    assert trainer.optimizer is custom_optim
    output = trainer.train()
    assert isinstance(output, TrainOutput)
    assert output.global_step == 2
    assert output.total_steps == 2
    assert not output.interrupted
    assert output.elapsed_time_sec >= 0.0
