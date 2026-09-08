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


def _run_fake_training_service(service, termination_reason, before_return=None):
    from src.training.trainer import TrainingTerminationReason

    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cpu"))
    tokenizer = Mock(vocab_size=32)
    batch_provider = Mock()
    model = Mock()
    sample_generator = Mock()

    class FakeTrainer:
        def __init__(self, **kwargs):
            self.callbacks = kwargs["callbacks"]
            self.max_iters = kwargs["config"].training.max_iters
            self.current_lr = kwargs["config"].training.learning_rate
            self.should_stop = False

        def request_stop(self):
            self.should_stop = True

        def train(self, resume_checkpoint=None):
            for callback in self.callbacks:
                callback.on_train_begin(self)
            for callback in self.callbacks:
                callback.on_step_end(self, 10, 0.5)
            if before_return is not None:
                before_return()
            return TrainOutput(
                global_step=10,
                total_steps=self.max_iters,
                final_train_loss=0.5,
                interrupted=termination_reason is TrainingTerminationReason.USER_STOPPED,
                termination_reason=termination_reason,
            )

    runtime_plan = resolve_training_plan(
        config,
        capabilities=RuntimeCapabilities(
            cuda_available=False,
            mps_available=False,
            bf16_supported=False,
            bitsandbytes_available=False,
        ),
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
        ),
        patch(
            "src.ui.services.training_service.resolve_training_plan",
            return_value=runtime_plan,
        ),
        patch("src.ui.services.training_service.Trainer", FakeTrainer),
    ):
        service.start_training(config_path="unused.yaml")
        assert service._thread is not None
        service._thread.join(timeout=1.0)
        assert not service._thread.is_alive()


def test_training_state_is_versioned_and_sse_init_is_authoritative():
    import json

    service = TrainingService()
    service.history_steps.extend(
        {"type": "step", "step": i, "loss": 1.0, "lr": 0.001, "elapsed": 0.0} for i in range(350)
    )
    service.sample_history.extend(
        {"type": "sample", "step": i, "text": str(i), "timestamp": "00:00:00"} for i in range(8)
    )
    service.error_message = "boom"
    service.current_lr = 0.001

    state = service.get_state()

    assert state["run_id"] == 0
    assert state["sequence"] == 0
    assert state["error_message"] == "boom"
    assert state["current_lr"] == 0.001
    assert len(state["history_steps"]) == 350
    assert len(state["sample_history"]) == 8

    stream = service.stream_events()
    first = next(stream)
    payload = json.loads(first.removeprefix("data: ").strip())
    stream.close()

    assert payload["type"] == "init"
    assert payload["run_id"] == state["run_id"]
    assert payload["sequence"] == state["sequence"]
    assert payload["error_message"] == "boom"
    assert payload["current_lr"] == 0.001
    assert payload["history_steps"] == state["history_steps"]
    assert payload["sample_history"] == state["sample_history"]


def test_user_stop_preserves_metrics_and_exposes_termination_reason():
    from src.training.trainer import TrainingTerminationReason

    service = TrainingService()
    events = []
    original_broadcast = service.broadcast

    def capture(evt):
        events.append(dict(evt))
        original_broadcast(evt)

    service.broadcast = capture
    _run_fake_training_service(service, TrainingTerminationReason.USER_STOPPED)

    state = service.get_state()
    assert state["status"] == "STOPPED"
    assert state["termination_reason"] == "USER_STOPPED"
    assert state["current_step"] == 10
    assert state["current_loss"] == 0.5
    assert state["history_steps"]
    running_events = [
        e for e in events if e.get("type") == "status" and e.get("status") == "RUNNING"
    ]
    assert len(running_events) == 1
    assert all("run_id" in e and "sequence" in e for e in events)


def test_early_stop_maps_to_completed_without_erasing_metrics():
    from src.training.trainer import TrainingTerminationReason

    service = TrainingService()
    _run_fake_training_service(service, TrainingTerminationReason.EARLY_STOPPED)

    state = service.get_state()
    assert state["status"] == "COMPLETED"
    assert state["termination_reason"] == "EARLY_STOPPED"
    assert state["current_step"] == 10
    assert state["history_steps"]


def test_clear_state_is_the_only_terminal_operation_that_erases_metrics():
    service = TrainingService()
    service.status = "STOPPED"
    service.current_step = 12
    service.current_loss = 0.4
    service.history_steps.append({"type": "step", "step": 12, "loss": 0.4})

    service.clear_state()

    state = service.get_state()
    assert state["status"] == "IDLE"
    assert state["current_step"] == 0
    assert state["current_loss"] is None
    assert state["history_steps"] == []
    assert state["sequence"] > 0


def test_training_histories_are_bounded_without_breaking_authoritative_snapshot(monkeypatch):
    service = TrainingService()
    monkeypatch.setattr(service, "MAX_STEP_HISTORY", 2, raising=False)
    monkeypatch.setattr(service, "MAX_EVAL_HISTORY", 2, raising=False)
    monkeypatch.setattr(service, "MAX_SAMPLE_HISTORY", 2, raising=False)

    for step in range(1, 4):
        service.record_step(step=step, loss=float(step), lr=0.1, elapsed=0.0, emit=True)
        service.record_eval(step=step, train_loss=1.0, val_loss=float(step), lr=0.1)
        service.record_sample(step=step, text=str(step))

    state = service.get_state()
    assert [item["step"] for item in state["history_steps"]] == [2, 3]
    assert [item["step"] for item in state["history_evals"]] == [2, 3]
    assert [item["step"] for item in state["sample_history"]] == [2, 3]


def test_late_stop_request_does_not_overwrite_already_completed_trainer_result():
    from src.training.trainer import TrainingTerminationReason

    service = TrainingService()
    _run_fake_training_service(
        service,
        TrainingTerminationReason.COMPLETED,
        before_return=service.stop_training,
    )

    state = service.get_state()
    assert state["status"] == "COMPLETED"
    assert state["termination_reason"] == "COMPLETED"
