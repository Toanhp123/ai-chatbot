"""
Unit tests for enterprise training callbacks system:
- ConsoleProgressCallback
- ModelCheckpointCallback (min/max modes)
- EarlyStoppingCallback (min/max modes)
- SampleGenerationCallback (IoC / Dependency Injection)
- Protocol verification
"""

import os
import random
import tempfile
from typing import Any, Dict, Optional, cast

import numpy as np
import pytest
import torch
import torch.nn as nn

from src.training.callbacks import (
    BaseCallback,
    ConsoleProgressCallback,
    EarlyStoppingCallback,
    ModelCheckpointCallback,
    SampleGenerationCallback,
    TrainerProtocol,
)


class DummyTrainer:
    """Mock trainer implementing TrainerProtocol for isolated callback testing."""

    def __init__(self, max_iters: int = 100, lr: float = 1e-3) -> None:
        self._max_iters = max_iters
        self.current_lr = lr
        self.should_stop = False
        self.model = nn.Linear(4, 2)
        self.optimizer = torch.optim.SGD(self.model.parameters(), lr=lr)
        self.config_dict = {"dummy_config": True}

    @property
    def max_iters(self) -> int:
        return self._max_iters

    def request_stop(self) -> None:
        self.should_stop = True

    def get_model_state_dict(self) -> Dict[str, Any]:
        return self.model.state_dict()

    def get_optimizer_state_dict(self) -> Optional[Dict[str, Any]]:
        return self.optimizer.state_dict()

    def get_config_dict(self) -> Dict[str, Any]:
        return self.config_dict

    def get_checkpoint_state(self) -> Dict[str, Any]:
        return {
            "checkpoint_version": 2,
            "model_state_dict": self.get_model_state_dict(),
            "optimizer_state_dict": self.get_optimizer_state_dict(),
            "config": self.get_config_dict(),
            "tokenizer_identity": None,
            "runtime_state": {},
        }


def test_trainer_protocol_conformance() -> None:
    """Kiểm tra DummyTrainer tuân thủ TrainerProtocol."""
    trainer = DummyTrainer()
    assert isinstance(trainer, TrainerProtocol)


def test_console_progress_callback() -> None:
    """Kiểm tra ConsoleProgressCallback không ném lỗi trong suốt vòng đời."""
    cb = ConsoleProgressCallback(log_interval=5)
    trainer = DummyTrainer(max_iters=20)

    cb.on_train_begin(trainer)
    cb.on_step_end(trainer, step=5, loss=0.5)
    cb.on_eval_end(trainer, step=5, metrics={"train_loss": 0.5, "val_loss": 0.45})
    cb.on_train_end(trainer)


def test_model_checkpoint_callback_min_mode() -> None:
    """Kiểm tra ModelCheckpointCallback ở chế độ mode='min' (ví dụ: val_loss)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cb = ModelCheckpointCallback(
            save_dir=tmpdir,
            filename="best.pt",
            monitor="val_loss",
            mode="min",
        )
        trainer = DummyTrainer()
        cb.on_train_begin(trainer)

        # Lần 1: val_loss = 2.0 -> Cải thiện -> Lưu checkpoint
        cb.on_eval_end(trainer, step=10, metrics={"val_loss": 2.0})
        assert os.path.exists(cb.filepath)
        state1 = torch.load(cb.filepath, weights_only=False)
        assert state1["step"] == 10
        assert state1["val_loss"] == 2.0

        # Lần 2: val_loss = 2.5 -> Tệ hơn -> Không lưu đè
        cb.on_eval_end(trainer, step=20, metrics={"val_loss": 2.5})
        state2 = torch.load(cb.filepath, weights_only=False)
        assert state2["step"] == 10

        # Lần 3: val_loss = 1.5 -> Tốt hơn -> Lưu đè
        cb.on_eval_end(trainer, step=30, metrics={"val_loss": 1.5})
        state3 = torch.load(cb.filepath, weights_only=False)
        assert state3["step"] == 30
        assert state3["val_loss"] == 1.5


def test_model_checkpoint_callback_max_mode() -> None:
    """Kiểm tra ModelCheckpointCallback ở chế độ mode='max' (ví dụ: accuracy)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cb = ModelCheckpointCallback(
            save_dir=tmpdir,
            filename="best_acc.pt",
            monitor="accuracy",
            mode="max",
        )
        trainer = DummyTrainer()
        cb.on_train_begin(trainer)

        # Lần 1: acc = 0.6 -> Kỷ lục mới
        cb.on_eval_end(trainer, step=10, metrics={"accuracy": 0.6})
        state = torch.load(cb.filepath, weights_only=False)
        assert state["accuracy"] == 0.6

        # Lần 2: acc = 0.55 -> Kém hơn -> Không lưu
        cb.on_eval_end(trainer, step=20, metrics={"accuracy": 0.55})
        state = torch.load(cb.filepath, weights_only=False)
        assert state["step"] == 10

        # Lần 3: acc = 0.75 -> Tốt hơn -> Lưu đè
        cb.on_eval_end(trainer, step=30, metrics={"accuracy": 0.75})
        state = torch.load(cb.filepath, weights_only=False)
        assert state["step"] == 30


def test_model_checkpoint_invalid_mode() -> None:
    """Kiểm tra ngoại lệ khi truyền mode không hợp lệ."""
    with pytest.raises(ValueError, match="Chế độ mode không hợp lệ"):
        # pyright: ignore[reportArgumentType]
        ModelCheckpointCallback(mode="invalid")  # type: ignore


def test_early_stopping_callback_min_mode() -> None:
    """Kiểm tra EarlyStoppingCallback ở chế độ mode='min'."""
    trainer = DummyTrainer()
    cb = EarlyStoppingCallback(monitor="val_loss", mode="min", patience=2, min_delta=0.01)

    # Lần 1: 1.0 (kỷ lục)
    cb.on_eval_end(trainer, step=10, metrics={"val_loss": 1.0})
    assert not trainer.should_stop

    # Lần 2: 1.05 (không cải thiện lần 1)
    cb.on_eval_end(trainer, step=20, metrics={"val_loss": 1.05})
    assert not trainer.should_stop

    # Lần 3: 1.02 (không cải thiện lần 2 -> hết patience)
    cb.on_eval_end(trainer, step=30, metrics={"val_loss": 1.02})
    assert trainer.should_stop


def test_early_stopping_callback_max_mode() -> None:
    """Kiểm tra EarlyStoppingCallback ở chế độ mode='max'."""
    trainer = DummyTrainer()
    cb = EarlyStoppingCallback(monitor="accuracy", mode="max", patience=2, min_delta=0.01)

    # Lần 1: acc 0.8
    cb.on_eval_end(trainer, step=10, metrics={"accuracy": 0.8})
    assert not trainer.should_stop

    # Lần 2: acc 0.805 (chưa vượt min_delta 0.01 -> không tính là cải thiện)
    cb.on_eval_end(trainer, step=20, metrics={"accuracy": 0.805})
    assert not trainer.should_stop

    # Lần 3: acc 0.79 -> Hết patience -> should_stop = True
    cb.on_eval_end(trainer, step=30, metrics={"accuracy": 0.79})
    assert trainer.should_stop


def test_sample_generation_callback_with_sample_fn() -> None:
    """Kiểm tra SampleGenerationCallback sử dụng IoC sample_fn."""
    invoked_steps = []

    def mock_sample_fn(step: int) -> str:
        invoked_steps.append(step)
        return f"Generated sample at step {step}"

    cb = SampleGenerationCallback(sample_fn=mock_sample_fn)
    trainer = DummyTrainer()

    cb.on_eval_end(trainer, step=50, metrics={"val_loss": 1.5})
    assert 50 in invoked_steps


def test_base_callback_default_methods() -> None:
    """Kiểm tra các phương thức mặc định của BaseCallback an toàn."""
    cb = BaseCallback()
    trainer = DummyTrainer()
    cb.on_train_begin(trainer)
    cb.on_step_end(trainer, 1, 0.5)
    cb.on_eval_end(trainer, 1, {})
    cb.on_train_end(trainer)


def test_model_checkpoint_top_k_and_last() -> None:
    """Kiểm tra ModelCheckpointCallback lưu đúng Top-K và last_model.pt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cb = ModelCheckpointCallback(
            save_dir=tmpdir,
            filename="best.pt",
            monitor="val_loss",
            mode="min",
            save_top_k=2,
            save_last=True,
            run_name="exp_test",
        )
        trainer = DummyTrainer()
        cb.on_train_begin(trainer)

        # Step 10: val_loss 3.0 -> Save best.pt, exp_test_step10_val3.0000.pt, last_model.pt
        cb.on_eval_end(trainer, step=10, metrics={"val_loss": 3.0})
        # Step 20: val_loss 2.0 -> Save best.pt, exp_test_step20_val2.0000.pt, last_model.pt
        cb.on_eval_end(trainer, step=20, metrics={"val_loss": 2.0})
        # Step 30: val_loss 1.0 -> Save best.pt, exp_test_step30_val1.0000.pt, deletes step10 (worst of top 2)
        cb.on_eval_end(trainer, step=30, metrics={"val_loss": 1.0})

        files = os.listdir(tmpdir)
        assert "best.pt" in files
        assert "last_model.pt" in files
        assert "exp_test_last.pt" in files
        assert "exp_test_step30_val1.0000.pt" in files
        assert "exp_test_step20_val2.0000.pt" in files
        # exp_test_step10_val3.0000.pt must have been pruned because save_top_k=2!
        assert "exp_test_step10_val3.0000.pt" not in files


def test_model_checkpoint_rejects_unsafe_filename() -> None:
    """Checkpoint filename must not escape its configured save directory."""
    with pytest.raises(ValueError, match="filename"):
        ModelCheckpointCallback(save_dir="checkpoints", filename="../best.pt")


@pytest.mark.parametrize("run_name", ["../escape", r"..\\escape", ".", ".."])
def test_model_checkpoint_rejects_unsafe_run_name(run_name: str) -> None:
    """Run names are filename components, not arbitrary paths."""
    with pytest.raises(ValueError, match="run_name"):
        ModelCheckpointCallback(save_dir="checkpoints", run_name=run_name)


def test_model_checkpoint_failed_save_preserves_existing_file(tmp_path, monkeypatch) -> None:
    """A failed checkpoint write must not corrupt the last known-good canonical file."""
    cb = ModelCheckpointCallback(save_dir=str(tmp_path), filename="best.pt")
    trainer = DummyTrainer()
    target = tmp_path / "best.pt"
    target.write_bytes(b"known-good")

    def failing_save(_state, path):
        with open(path, "wb") as f:
            f.write(b"partial")
        raise OSError("simulated interrupted write")

    monkeypatch.setattr("src.training.callbacks.checkpoint.torch.save", failing_save)

    with pytest.raises(OSError, match="interrupted"):
        cb._save_state(trainer, step=1, metrics={"val_loss": 1.0}, path=str(target))

    assert target.read_bytes() == b"known-good"
    assert not list(tmp_path.glob("*.tmp"))


def test_model_checkpoint_top_k_handles_non_monotonic_scores() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cb = ModelCheckpointCallback(
            save_dir=tmpdir,
            filename="best.pt",
            monitor="val_loss",
            mode="min",
            save_top_k=2,
            save_last=False,
            run_name="nonmono",
        )
        trainer = DummyTrainer()
        cb.on_train_begin(trainer)
        cb.on_eval_end(trainer, step=10, metrics={"val_loss": 3.0})
        cb.on_eval_end(trainer, step=20, metrics={"val_loss": 1.0})
        cb.on_eval_end(trainer, step=30, metrics={"val_loss": 2.0})

        versioned = sorted(name for name in os.listdir(tmpdir) if name.startswith("nonmono_step"))
        assert versioned == [
            "nonmono_step20_val1.0000.pt",
            "nonmono_step30_val2.0000.pt",
        ]


def test_last_checkpoint_keeps_last_metric_not_historical_best() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cb = ModelCheckpointCallback(
            save_dir=tmpdir,
            filename="best.pt",
            monitor="val_loss",
            mode="min",
            save_top_k=0,
            save_last=True,
        )
        trainer = DummyTrainer()
        cb.on_train_begin(trainer)
        cb.on_eval_end(trainer, step=10, metrics={"val_loss": 1.0})
        cb.on_eval_end(trainer, step=20, metrics={"val_loss": 2.0})
        cb.on_train_end(trainer)

        state = torch.load(os.path.join(tmpdir, "last_model.pt"), weights_only=True)
        assert state["step"] == 20
        assert state["val_loss"] == pytest.approx(2.0)


def test_sample_callback_does_not_advance_training_rng() -> None:
    cb = SampleGenerationCallback(sample_fn=lambda _step: str(torch.rand(3).tolist()))
    trainer = DummyTrainer()
    torch.manual_seed(1234)
    before = torch.random.get_rng_state().clone()

    cb.on_eval_end(trainer, step=1, metrics={"val_loss": 1.0})

    assert torch.equal(torch.random.get_rng_state(), before)


def test_sample_callback_preserves_python_numpy_and_torch_rng() -> None:
    def sample_fn(_step: int) -> str:
        _ = random.random()
        _ = np.random.random()
        _ = torch.rand(3)
        return "sample"

    cb = SampleGenerationCallback(sample_fn=sample_fn)
    trainer = DummyTrainer()
    random.seed(77)
    np.random.seed(77)
    torch.manual_seed(77)
    python_before = random.getstate()
    numpy_before = cast(
        tuple[str, np.ndarray, int, int, float],
        np.random.get_state(legacy=True),
    )
    torch_before = torch.random.get_rng_state().clone()

    cb.on_eval_end(trainer, step=1, metrics={"val_loss": 1.0})

    assert random.getstate() == python_before
    numpy_after = cast(
        tuple[str, np.ndarray, int, int, float],
        np.random.get_state(legacy=True),
    )
    assert numpy_after[0] == numpy_before[0]
    assert np.array_equal(numpy_after[1], numpy_before[1])
    assert numpy_after[2:] == numpy_before[2:]
    assert torch.equal(torch.random.get_rng_state(), torch_before)


def test_model_checkpoint_restores_zero_or_negative_best_metric(tmp_path) -> None:
    zero_path = tmp_path / "best_zero.pt"
    torch.save({"accuracy": 0.0, "val_loss": 1.0}, zero_path)
    zero_cb = ModelCheckpointCallback(
        save_dir=str(tmp_path), filename="best_zero.pt", monitor="accuracy", mode="max"
    )
    zero_cb.on_train_begin(DummyTrainer())
    assert zero_cb.best_score == pytest.approx(0.0)

    negative_path = tmp_path / "best_negative.pt"
    torch.save({"accuracy": -0.25, "val_loss": 1.0}, negative_path)
    negative_cb = ModelCheckpointCallback(
        save_dir=str(tmp_path), filename="best_negative.pt", monitor="accuracy", mode="max"
    )
    negative_cb.on_train_begin(DummyTrainer())
    assert negative_cb.best_score == pytest.approx(-0.25)


def test_checkpoint_callback_drops_missing_top_k_paths_when_restoring(tmp_path) -> None:
    existing = tmp_path / "existing.pt"
    existing.write_bytes(b"placeholder")
    missing = tmp_path / "missing.pt"
    cb = ModelCheckpointCallback(save_dir=str(tmp_path), save_top_k=2)

    cb.load_state_dict(
        {
            "best_score": 0.5,
            "top_k_checkpoints": [[0.5, str(existing)], [0.6, str(missing)]],
        }
    )

    assert cb.top_k_checkpoints == [(0.5, str(existing))]
