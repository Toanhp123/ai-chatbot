"""Canonical training run assembly.

This is the one place that converts an effective EngineConfig into concrete data,
model, generator, callbacks and Trainer objects. CLI and Web lifecycle services
must call this factory instead of re-creating the graph.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from src.core.config import EngineConfig
from src.core.runtime import ResolvedTrainingPlan, resolve_training_plan, validate_training_plan
from src.data.batch_provider import get_batch_provider
from src.data.cleaners import get_cleaner
from src.data.pipeline import DataPipeline
from src.generation import get_generator
from src.models.registry import ModelRegistry
from src.training.callbacks import (
    BaseCallback,
    EarlyStoppingCallback,
    ModelCheckpointCallback,
    SampleGenerationCallback,
    TrainerProtocol,
)
from src.training.trainer import Trainer
from src.utils.seed import set_seed

from .contracts import (
    NullTrainingObserver,
    PreparedTrainingRun,
    TrainingObserver,
    TrainingPreparationAborted,
)


class ObserverCallback(BaseCallback):
    def __init__(self, observer: TrainingObserver, log_interval: int = 10) -> None:
        self.observer = observer
        self.log_interval = log_interval
        self.start_time = time.time()

    def on_train_begin(self, trainer: TrainerProtocol) -> None:
        del trainer
        self.start_time = time.time()

    def on_step_end(self, trainer: TrainerProtocol, step: int, loss: float) -> None:
        self.observer.on_step(
            step=step,
            loss=float(loss),
            lr=float(trainer.current_lr),
            elapsed=time.time() - self.start_time,
            emit=step % self.log_interval == 0 or step == trainer.max_iters,
        )

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: dict[str, float]) -> None:
        self.observer.on_eval(
            step=step,
            train_loss=float(metrics.get("train_loss", 0.0)),
            val_loss=float(metrics.get("val_loss", 0.0)),
            lr=float(trainer.current_lr),
        )


class TrainingRunFactory:
    """Build exactly one Trainer graph from an immutable effective config snapshot."""

    @staticmethod
    def _check_abort(abort_check: Optional[Callable[[], bool]]) -> None:
        if abort_check is not None and abort_check():
            raise TrainingPreparationAborted()

    def prepare(
        self,
        *,
        config: EngineConfig,
        runtime_plan: Optional[ResolvedTrainingPlan] = None,
        observer: Optional[TrainingObserver] = None,
        abort_check: Optional[Callable[[], bool]] = None,
        log_interval: int = 10,
    ) -> PreparedTrainingRun:
        effective = EngineConfig.from_dict(config.to_dict())
        set_seed(effective.system.seed)
        self._check_abort(abort_check)

        cleaner_kwargs = dict(effective.data.cleaner_kwargs)
        cleaner_kwargs.setdefault("clean_line_numbers", effective.data.clean_line_numbers)
        cleaner = get_cleaner(cleaner_type=effective.data.cleaner_type, **cleaner_kwargs)
        self._check_abort(abort_check)

        train_data, val_data, tokenizer = DataPipeline.setup_data(
            config=effective.data,
            cleaner=cleaner,
            block_size=effective.model.block_size,
        )
        self._check_abort(abort_check)

        batch_provider = get_batch_provider(
            provider_type=effective.data.batch_provider_type,
            train_data=train_data,
            val_data=val_data,
            block_size=effective.model.block_size,
            num_workers=effective.data.num_workers,
            pin_memory=effective.data.pin_memory,
        )
        effective = effective.copy(model=effective.model.copy(vocab_size=tokenizer.vocab_size))
        self._check_abort(abort_check)

        model = ModelRegistry.create(effective.model.name, effective.model)
        self._check_abort(abort_check)

        if runtime_plan is None:
            runtime_plan = resolve_training_plan(effective)
        else:
            validate_training_plan(effective, runtime_plan)

        sample_generator = get_generator(
            "local",
            model=model,
            tokenizer=tokenizer,
            device=runtime_plan.device,
        )
        sample_config = effective.generation.copy()
        sink = observer or NullTrainingObserver()

        def sample_fn(step: int) -> str:
            text = sample_generator.generate("Trăm năm", config=sample_config)
            sink.on_sample(step=step, text=text)
            return text

        callbacks: list[BaseCallback] = [
            ObserverCallback(sink, log_interval=log_interval),
            SampleGenerationCallback(sample_fn=sample_fn),
            EarlyStoppingCallback(
                monitor="val_loss",
                mode="min",
                patience=effective.training.early_stopping_patience,
            ),
            ModelCheckpointCallback(
                save_dir=effective.training.checkpoint_dir,
                filename=effective.training.checkpoint_name,
                monitor="val_loss",
                mode="min",
                save_top_k=effective.training.save_top_k,
                save_last=effective.training.save_last,
                run_name=effective.training.run_name,
            ),
        ]
        trainer = Trainer(
            model=model,
            batch_provider=batch_provider,
            config=effective,
            callbacks=callbacks,
            tokenizer=tokenizer,
            runtime_plan=runtime_plan,
        )
        return PreparedTrainingRun(config=effective, runtime_plan=runtime_plan, trainer=trainer)
