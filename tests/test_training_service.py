from typing import cast
from unittest.mock import Mock, patch

import pytest
import torch

from src.application.training.contracts import TrainingFeasibility, TrainingPlan
from src.core.config import EngineConfig
from src.core.runtime import RuntimeCapabilities, resolve_training_plan
from src.training.trainer import TrainOutput
from tests.application_support import make_training_service


def _training_plan(
    config: EngineConfig,
    runtime_plan=None,
    *,
    resume_checkpoint=None,
    resume_checkpoint_identity=None,
) -> TrainingPlan:
    runtime_plan = runtime_plan or resolve_training_plan(config)
    return TrainingPlan(
        requested_config=config,
        config=config,
        runtime_plan=runtime_plan,
        feasibility=TrainingFeasibility(
            feasible=True,
            message="ok",
            estimated_gb=0.0,
            estimated_mb=0.0,
        ),
        resume_checkpoint=resume_checkpoint,
        resume_checkpoint_identity=resume_checkpoint_identity,
    )


def test_abort_before_trainer_creation_does_not_deadlock():
    service = make_training_service()
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
            "src.application.training.service.prepare_application_dataset",
            return_value=(torch.arange(64), torch.arange(32), tokenizer),
        ),
        patch(
            "src.training.runtime.create_batch_provider",
            return_value=batch_provider,
        ),
        patch(
            "src.training.runtime.create_model",
            side_effect=create_model_and_request_abort,
        ),
        patch(
            "src.training.runtime.create_generator",
            return_value=sample_generator,
        ),
    ):
        service.start_training(plan=_training_plan(config))
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert not service._thread.is_alive()
    assert service.status == "STOPPED"
    assert service.trainer is None


def test_clear_state_waits_for_stopping_worker_before_committing_idle():
    import threading
    import time

    service = make_training_service()
    service.status = "STOPPING"

    def finish_old_worker():
        time.sleep(0.03)
        with service._synchronization.section():
            service.status = "STOPPED"

    worker = threading.Thread(target=finish_old_worker)
    service._thread = worker
    worker.start()

    service.clear_state()
    worker.join(timeout=1)

    assert service.status == "IDLE"


def test_training_worker_shares_one_runtime_plan_with_generator_and_trainer():
    service = make_training_service()
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
            "src.application.training.service.prepare_application_dataset",
            return_value=(torch.arange(64), torch.arange(32), tokenizer),
        ),
        patch(
            "src.training.runtime.create_batch_provider",
            return_value=batch_provider,
        ),
        patch(
            "src.training.runtime.create_model",
            return_value=model,
        ),
        patch(
            "src.training.runtime.create_generator",
            return_value=sample_generator,
        ) as get_generator_mock,
        patch("src.training.runtime.Trainer", FakeTrainer),
    ):
        service.start_training(plan=_training_plan(config, runtime_plan))
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert not service._thread.is_alive()
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
            "src.application.training.service.prepare_application_dataset",
            return_value=(torch.arange(64), torch.arange(32), tokenizer),
        ),
        patch(
            "src.training.runtime.create_batch_provider",
            return_value=batch_provider,
        ),
        patch(
            "src.training.runtime.create_model",
            return_value=model,
        ),
        patch(
            "src.training.runtime.create_generator",
            return_value=sample_generator,
        ),
        patch("src.training.runtime.Trainer", FakeTrainer),
    ):
        service.start_training(plan=_training_plan(config, runtime_plan))
        assert service._thread is not None
        service._thread.join(timeout=1.0)
        assert not service._thread.is_alive()


def test_training_state_is_versioned_and_event_init_is_authoritative():

    service = make_training_service()
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

    stream = service.iter_events()
    payload = next(stream)
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

    service = make_training_service()
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

    service = make_training_service()
    _run_fake_training_service(service, TrainingTerminationReason.EARLY_STOPPED)

    state = service.get_state()
    assert state["status"] == "COMPLETED"
    assert state["termination_reason"] == "EARLY_STOPPED"
    assert state["current_step"] == 10
    assert state["history_steps"]


def test_clear_state_is_the_only_terminal_operation_that_erases_metrics():
    service = make_training_service()
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
    service = make_training_service()
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

    service = make_training_service()
    _run_fake_training_service(
        service,
        TrainingTerminationReason.COMPLETED,
        before_return=service.stop_training,
    )

    state = service.get_state()
    assert state["status"] == "COMPLETED"
    assert state["termination_reason"] == "COMPLETED"


def test_training_worker_uses_resolved_config_snapshot_without_rereading_yaml():
    service = make_training_service()
    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cpu"))
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
    model = Mock()

    class FakeTrainer:
        def __init__(self, **kwargs):
            self.config = kwargs["config"]

        def train(self, resume_checkpoint=None):
            return TrainOutput(
                global_step=0, total_steps=1, final_train_loss=0.0, interrupted=False
            )

    with (
        patch(
            "src.application.training.service.prepare_application_dataset",
            return_value=(torch.arange(64), torch.arange(32), tokenizer),
        ),
        patch("src.training.runtime.create_batch_provider", return_value=Mock()),
        patch("src.training.runtime.create_model", return_value=model),
        patch("src.training.runtime.create_generator", return_value=Mock()),
        patch("src.training.runtime.Trainer", FakeTrainer),
    ):
        service.start_training(plan=_training_plan(config, runtime_plan))
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert service.status == "COMPLETED"


def test_training_service_defensively_copies_config_snapshot_before_worker_runs():
    service = make_training_service()
    config = EngineConfig().copy(
        system=EngineConfig().system.copy(device="cpu"),
        training=EngineConfig().training.copy(max_iters=123, run_name="stable"),
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
    observed = {}

    def setup_data(*args, **kwargs):
        observed["max_iters"] = captured.training.max_iters
        observed["run_name"] = captured.training.run_name
        return torch.arange(64), torch.arange(32), Mock(vocab_size=32)

    captured = config

    class FakeTrainer:
        def __init__(self, **kwargs):
            observed["worker_config"] = kwargs["config"]

        def train(self, resume_checkpoint=None):
            return TrainOutput(
                global_step=0, total_steps=1, final_train_loss=0.0, interrupted=False
            )

    with (
        patch(
            "src.application.training.service.prepare_application_dataset", side_effect=setup_data
        ),
        patch("src.training.runtime.create_batch_provider", return_value=Mock()),
        patch("src.training.runtime.create_model", return_value=Mock()),
        patch("src.training.runtime.create_generator", return_value=Mock()),
        patch("src.training.runtime.Trainer", FakeTrainer),
    ):
        service.start_training(plan=_training_plan(config, runtime_plan))
        # Mutation after submission must not affect the worker snapshot.
        config.training.max_iters = 999
        config.training.run_name = "mutated"
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert observed["worker_config"].training.max_iters == 123
    assert observed["worker_config"].training.run_name == "stable"


def test_training_start_rejected_while_generation_owns_same_accelerator():
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.exceptions import AcceleratorBusyError

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_generation("cuda")
    service = make_training_service(accelerator_coordinator=coordinator)
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

    with pytest.raises(AcceleratorBusyError):
        service.start_training(plan=_training_plan(config, runtime_plan))

    assert service.status == "IDLE"
    coordinator.release_generation("cuda")


def _cuda_plan_for_test():
    from src.core.runtime import ResolvedTrainingPlan

    return ResolvedTrainingPlan(
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


def test_training_start_rejected_before_state_commit_when_generation_owns_accelerator():
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.exceptions import AcceleratorBusyError

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_generation("cuda")
    service = make_training_service(accelerator_coordinator=coordinator)
    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cuda"))
    try:
        with pytest.raises(AcceleratorBusyError):
            service.start_training(plan=_training_plan(config, _cuda_plan_for_test()))
        assert service.status == "IDLE"
        assert service._thread is None
    finally:
        coordinator.release_generation("cuda")


def test_training_releases_accelerator_after_worker_failure():
    from src.core.accelerator import AcceleratorCoordinator

    coordinator = AcceleratorCoordinator()
    service = make_training_service(accelerator_coordinator=coordinator)
    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cuda"))

    with patch(
        "src.application.training.service.prepare_application_dataset",
        side_effect=RuntimeError("synthetic startup failure"),
    ):
        service.start_training(plan=_training_plan(config, _cuda_plan_for_test()))
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert service.status == "ERROR"
    coordinator.reserve_generation("cuda")
    coordinator.release_generation("cuda")


def test_training_thread_start_failure_rolls_back_state_and_accelerator_reservation():
    from src.core.accelerator import AcceleratorCoordinator

    coordinator = AcceleratorCoordinator()
    service = make_training_service(accelerator_coordinator=coordinator)
    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cuda"))

    with patch(
        "src.training.execution.threading.Thread.start",
        side_effect=RuntimeError("thread start failed"),
    ):
        with pytest.raises(RuntimeError, match="thread start failed"):
            service.start_training(plan=_training_plan(config, _cuda_plan_for_test()))

    assert service.status == "IDLE"
    assert service._thread is None
    coordinator.reserve_generation("cuda")
    coordinator.release_generation("cuda")


def test_training_sample_generation_uses_canonical_generation_config():
    from src.generation import GenerationOutput
    from src.training.callbacks import SampleGenerationCallback, TrainerProtocol

    service = make_training_service()
    base = EngineConfig()
    config = base.copy(
        system=base.system.copy(device="cpu"),
        generation=base.generation.copy(
            max_new_tokens=37,
            temperature=0.31,
            top_k=13,
            top_p=0.72,
            min_p=0.08,
            repetition_penalty=1.19,
            do_sample=False,
            use_cache=False,
        ),
    )
    tokenizer = Mock(vocab_size=32)
    batch_provider = Mock()
    model = Mock()
    sample_generator = Mock()
    sample_generator.generate.return_value = GenerationOutput(
        text="sample",
        prompt="Trăm năm",
        generated_text="sample",
        token_ids=[1],
        tokens_generated=1,
        tokens_per_second=1.0,
        elapsed_time_sec=1.0,
        finish_reason="length",
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

    class FakeTrainer:
        def __init__(self, **kwargs):
            self.callbacks = kwargs["callbacks"]

        def train(self, resume_checkpoint=None):
            sample_callback = next(
                callback
                for callback in self.callbacks
                if isinstance(callback, SampleGenerationCallback)
            )
            sample_callback.on_eval_end(cast(TrainerProtocol, self), 1, {})
            return TrainOutput(
                global_step=1,
                total_steps=1,
                final_train_loss=0.0,
            )

    with (
        patch(
            "src.application.training.service.prepare_application_dataset",
            return_value=(torch.arange(64), torch.arange(32), tokenizer),
        ),
        patch(
            "src.training.runtime.create_batch_provider",
            return_value=batch_provider,
        ),
        patch(
            "src.training.runtime.create_model",
            return_value=model,
        ),
        patch(
            "src.training.runtime.create_generator",
            return_value=sample_generator,
        ),
        patch("src.training.runtime.Trainer", FakeTrainer),
    ):
        service.start_training(plan=_training_plan(config, runtime_plan))
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert not service._thread.is_alive()
    sample_config = sample_generator.generate.call_args.kwargs["config"]
    assert sample_generator.generate.call_args.kwargs["return_output"] is True
    assert sample_config == config.generation
    assert sample_config is not config.generation


def test_training_service_forwards_pinned_resume_identity_to_trainer():
    service = make_training_service()
    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cpu"))
    runtime_plan = resolve_training_plan(
        config,
        capabilities=RuntimeCapabilities(
            cuda_available=False,
            mps_available=False,
            bf16_supported=False,
            bitsandbytes_available=False,
        ),
    )
    identity = (1, 2, 3, 4)
    observed = {}

    class FakeTrainer:
        def __init__(self, **kwargs):
            pass

        def train(self, **kwargs):
            observed.update(kwargs)
            return TrainOutput(
                global_step=0, total_steps=1, final_train_loss=0.0, interrupted=False
            )

    with (
        patch(
            "src.application.training.service.prepare_application_dataset",
            return_value=(torch.arange(64), torch.arange(32), Mock(vocab_size=32)),
        ),
        patch("src.training.runtime.create_batch_provider", return_value=Mock()),
        patch("src.training.runtime.create_model", return_value=Mock()),
        patch("src.training.runtime.create_generator", return_value=Mock()),
        patch("src.training.runtime.Trainer", FakeTrainer),
    ):
        service.start_training(
            plan=_training_plan(
                config,
                runtime_plan,
                resume_checkpoint="checkpoints/resume.pt",
                resume_checkpoint_identity=identity,
            )
        )
        assert service._thread is not None
        service._thread.join(timeout=1.0)

    assert observed["resume_checkpoint"] == "checkpoints/resume.pt"
    assert observed["resume_checkpoint_identity"] == identity


def test_training_application_event_stream_is_transport_neutral():
    service = make_training_service()
    stream = service.iter_events()
    first = next(stream)
    stream.close()

    assert isinstance(first, dict)
    assert first["type"] == "init"
    assert not hasattr(service, "stream_events")
