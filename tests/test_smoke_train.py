import os
import tempfile

import pytest
import torch
from torch.utils.checkpoint import checkpoint as torch_checkpoint

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


def test_trainer_stop_request_does_not_report_phantom_step() -> None:
    from src.training.callbacks import BaseCallback

    class StopAfterTwo(BaseCallback):
        def on_step_end(self, trainer, step, loss):
            if step == 2:
                trainer.request_stop()

    config = EngineConfig()
    config.model.vocab_size = 20
    config.model.block_size = 8
    config.model.n_embd = 16
    config.model.n_head = 2
    config.model.n_layer = 1
    config.training.batch_size = 2
    config.training.max_iters = 5
    config.training.eval_interval = 5
    config.training.eval_iters = 1
    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)
    trainer = Trainer(
        model=model,
        batch_provider=provider,
        config=config,
        callbacks=[StopAfterTwo()],
        device="cpu",
    )

    output = trainer.train()

    assert output.global_step == 2
    assert output.total_steps == 2
    assert output.interrupted is True


def test_trainer_uses_first_warmup_lr_on_first_training_step() -> None:
    from src.training.callbacks import BaseCallback

    seen = []

    class CaptureLr(BaseCallback):
        def on_step_end(self, trainer, step, loss):
            seen.append((step, trainer.current_lr))

    config = EngineConfig()
    config.model.vocab_size = 20
    config.model.block_size = 8
    config.model.n_embd = 16
    config.model.n_head = 2
    config.model.n_layer = 1
    config.training.batch_size = 2
    config.training.max_iters = 3
    config.training.eval_interval = 3
    config.training.eval_iters = 1
    config.training.learning_rate = 0.003
    config.training.warmup_iters = 3
    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)
    trainer = Trainer(
        model=model, batch_provider=provider, config=config, callbacks=[CaptureLr()], device="cpu"
    )

    trainer.train()

    assert seen[0][1] == pytest.approx(0.001)


def test_train_output_reports_historical_best_validation_loss(monkeypatch) -> None:
    config = EngineConfig()
    config.model.vocab_size = 20
    config.model.block_size = 8
    config.model.n_embd = 16
    config.model.n_head = 2
    config.model.n_layer = 1
    config.training.batch_size = 2
    config.training.max_iters = 3
    config.training.eval_interval = 1
    config.training.eval_iters = 1
    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)
    trainer = Trainer(model=model, batch_provider=provider, config=config, device="cpu")
    metrics = iter(
        [
            {"train_loss": 3.0, "val_loss": 3.0},
            {"train_loss": 1.0, "val_loss": 1.0},
            {"train_loss": 2.0, "val_loss": 2.0},
        ]
    )
    monkeypatch.setattr(trainer, "evaluate", lambda: next(metrics))

    output = trainer.train()

    assert output.metrics["val_loss"] == pytest.approx(2.0)
    assert output.best_val_loss == pytest.approx(1.0)


def test_gradient_checkpointing_executes_checkpoint_path(monkeypatch) -> None:
    import src.models.architectures.minigpt as minigpt_module

    config = EngineConfig()
    config.model.vocab_size = 20
    config.model.block_size = 8
    config.model.n_embd = 16
    config.model.n_head = 2
    config.model.n_layer = 1
    config.training.batch_size = 2
    config.training.max_iters = 1
    config.training.eval_interval = 1
    config.training.eval_iters = 1
    config.training.gradient_checkpointing = True
    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)
    calls = []
    real_checkpoint = torch_checkpoint

    def recording_checkpoint(function, *args, **kwargs):
        calls.append(True)
        return real_checkpoint(function, *args, **kwargs)

    monkeypatch.setattr(minigpt_module, "checkpoint", recording_checkpoint, raising=False)
    trainer = Trainer(model=model, batch_provider=provider, config=config, device="cpu")

    trainer.train()

    assert calls


def test_resume_restores_exact_training_trajectory(tmp_path) -> None:
    import random

    import numpy as np

    from src.training.callbacks import BaseCallback

    class StopAtTwo(BaseCallback):
        def on_step_end(self, trainer, step, loss):
            if step == 2:
                trainer.request_stop()

    def make_config() -> EngineConfig:
        cfg = EngineConfig()
        cfg.system.seed = 1234
        cfg.model.vocab_size = 23
        cfg.model.block_size = 8
        cfg.model.n_embd = 16
        cfg.model.n_head = 2
        cfg.model.n_layer = 1
        cfg.model.dropout = 0.1
        cfg.training.batch_size = 2
        cfg.training.max_iters = 4
        cfg.training.eval_interval = 2
        cfg.training.eval_iters = 1
        cfg.training.warmup_iters = 10
        return cfg

    # Uninterrupted reference.
    random.seed(1234)
    np.random.seed(1234)
    torch.manual_seed(1234)
    full_cfg = make_config()
    full_model = ModelRegistry.create("minigpt", full_cfg.model)
    full_provider = MockBatchProvider(full_cfg.model.vocab_size)
    full_trainer = Trainer(
        model=full_model, batch_provider=full_provider, config=full_cfg, device="cpu"
    )
    full_trainer.train()
    expected = {key: value.detach().clone() for key, value in full_model.state_dict().items()}

    # Same start, stop after step 2 and persist exact runtime state.
    random.seed(1234)
    np.random.seed(1234)
    torch.manual_seed(1234)
    split_cfg = make_config()
    split_model = ModelRegistry.create("minigpt", split_cfg.model)
    split_provider = MockBatchProvider(split_cfg.model.vocab_size)
    checkpoint_cb = ModelCheckpointCallback(save_dir=str(tmp_path), save_top_k=0)
    split_trainer = Trainer(
        model=split_model,
        batch_provider=split_provider,
        config=split_cfg,
        callbacks=[StopAtTwo(), checkpoint_cb],
        device="cpu",
    )
    split_trainer.train()
    checkpoint_path = tmp_path / "last_model.pt"
    assert checkpoint_path.exists()

    # Simulate a fresh process whose initialization has already consumed unrelated RNG.
    random.seed(999)
    np.random.seed(999)
    torch.manual_seed(999)
    resumed_cfg = make_config()
    resumed_model = ModelRegistry.create("minigpt", resumed_cfg.model)
    resumed_provider = MockBatchProvider(resumed_cfg.model.vocab_size)
    resumed_trainer = Trainer(
        model=resumed_model,
        batch_provider=resumed_provider,
        config=resumed_cfg,
        device="cpu",
    )
    resumed_trainer.train(resume_checkpoint=str(checkpoint_path))

    actual = resumed_model.state_dict()
    assert actual.keys() == expected.keys()
    for key in expected:
        assert torch.equal(actual[key], expected[key]), key


def test_resume_preserves_historical_best_validation_loss(tmp_path, monkeypatch) -> None:
    from src.training.callbacks import BaseCallback

    class StopAtOne(BaseCallback):
        def on_step_end(self, trainer, step, loss):
            if step == 1:
                trainer.request_stop()

    config = EngineConfig()
    config.model.vocab_size = 20
    config.model.block_size = 8
    config.model.n_embd = 16
    config.model.n_head = 2
    config.model.n_layer = 1
    config.training.batch_size = 2
    config.training.max_iters = 2
    config.training.eval_interval = 1
    config.training.eval_iters = 1
    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)
    checkpoint_cb = ModelCheckpointCallback(save_dir=str(tmp_path), save_top_k=0)
    trainer = Trainer(
        model=model,
        batch_provider=provider,
        config=config,
        callbacks=[StopAtOne(), checkpoint_cb],
        device="cpu",
    )
    monkeypatch.setattr(trainer, "evaluate", lambda: {"train_loss": 1.0, "val_loss": 1.0})
    trainer.train()

    resumed_model = ModelRegistry.create("minigpt", config.model)
    resumed = Trainer(
        model=resumed_model,
        batch_provider=MockBatchProvider(config.model.vocab_size),
        config=config,
        device="cpu",
    )
    monkeypatch.setattr(resumed, "evaluate", lambda: {"train_loss": 2.0, "val_loss": 2.0})
    output = resumed.train(resume_checkpoint=str(tmp_path / "last_model.pt"))

    assert output.best_val_loss == pytest.approx(1.0)


def test_evaluate_restores_previous_model_mode() -> None:
    config = EngineConfig()
    config.model.vocab_size = 20
    config.model.block_size = 8
    config.model.n_embd = 16
    config.model.n_head = 2
    config.model.n_layer = 1
    config.training.batch_size = 2
    config.training.eval_iters = 1
    model = ModelRegistry.create("minigpt", config.model)
    provider = MockBatchProvider(config.model.vocab_size)
    trainer = Trainer(model=model, batch_provider=provider, config=config, device="cpu")
    model.eval()

    trainer.evaluate()

    assert model.training is False
