"""Capability-owned training graph assembly and execution mechanics."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from src.core.config import EngineConfig
from src.core.exceptions import TrainingPreparationCancelled
from src.core.runtime import ResolvedTrainingPlan, validate_training_plan
from src.data.api import create_batch_provider
from src.generation.api import create_generator
from src.models.api import create_model
from src.training.callbacks import (
    BaseCallback,
    EarlyStoppingCallback,
    ModelCheckpointCallback,
    SampleGenerationCallback,
    TrainerProtocol,
)
from src.training.contracts import (
    NullTrainingObserver,
    PreparedTrainingRun,
    TrainingObserver,
)
from src.training.trainer import Trainer, TrainOutput
from src.utils.seed import set_seed


class ObserverCallback(BaseCallback):
    """Translate trainer callback mechanics into the stable observer contract."""

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
    """Build one trainer graph from already-prepared data and an immutable config."""

    @staticmethod
    def _check_abort(abort_check: Optional[Callable[[], bool]]) -> None:
        if abort_check is not None and abort_check():
            raise TrainingPreparationCancelled()

    def prepare(
        self,
        *,
        config: EngineConfig,
        runtime_plan: ResolvedTrainingPlan,
        train_data: Any,
        val_data: Any,
        tokenizer: Any,
        observer: Optional[TrainingObserver] = None,
        abort_check: Optional[Callable[[], bool]] = None,
        log_interval: int = 10,
    ) -> PreparedTrainingRun:
        effective = EngineConfig.from_dict(config.to_dict())
        set_seed(effective.system.seed)
        self._check_abort(abort_check)

        batch_provider = create_batch_provider(
            provider_type=effective.data.batch_provider_type,
            train_data=train_data,
            val_data=val_data,
            block_size=effective.model.block_size,
            num_workers=effective.data.num_workers,
            pin_memory=effective.data.pin_memory,
        )
        effective = effective.copy(model=effective.model.copy(vocab_size=tokenizer.vocab_size))
        self._check_abort(abort_check)

        model = create_model(effective.model.name, effective.model)
        self._check_abort(abort_check)
        validate_training_plan(effective, runtime_plan)

        sample_generator = create_generator(
            "local",
            model=model,
            tokenizer=tokenizer,
            device=runtime_plan.device,
        )
        sample_config = effective.generation.copy()
        sink = observer or NullTrainingObserver()

        def sample_fn(step: int) -> str:
            output = sample_generator.generate(
                "Trăm năm",
                config=sample_config,
                return_output=True,
            )
            text = output.text
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

    @staticmethod
    def execute(
        prepared: PreparedTrainingRun,
        *,
        resume_checkpoint: Optional[str] = None,
        resume_checkpoint_identity: Optional[tuple[int, int, int, int]] = None,
    ) -> TrainOutput:
        if resume_checkpoint_identity is None:
            return prepared.trainer.train(resume_checkpoint=resume_checkpoint)
        return prepared.trainer.train(
            resume_checkpoint=resume_checkpoint,
            resume_checkpoint_identity=resume_checkpoint_identity,
        )


__all__ = ["ObserverCallback", "TrainingRunFactory"]
