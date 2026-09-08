"""
Training Service: Quản lý tiến trình huấn luyện chạy nền (Background Thread),
hệ thống phát sóng sự kiện Pub/Sub đa thuê bao (Multi-subscriber Broadcast) và theo dõi metrics thời gian thực.
"""

import json
import queue
import threading
import time
from typing import Any, Dict, Generator, List, Optional

import torch

from src.core.config import EngineConfig, GenerationConfig
from src.core.logging import configure_logging_from_system, get_logger
from src.core.runtime import ResolvedTrainingPlan, resolve_training_plan, validate_training_plan
from src.data.batch_provider import get_batch_provider
from src.data.cleaners import get_cleaner
from src.data.pipeline import DataPipeline
from src.generation import BaseGenerator, get_generator
from src.models.registry import ModelRegistry
from src.training.callbacks import (
    BaseCallback,
    EarlyStoppingCallback,
    ModelCheckpointCallback,
    SampleGenerationCallback,
    TrainerProtocol,
)
from src.training.trainer import Trainer, TrainingTerminationReason, TrainOutput
from src.utils.seed import set_seed

logger = get_logger("TrainingService")


class WebMetricsCallback(BaseCallback):
    """Collect training metrics while TrainingService owns lifecycle transitions."""

    def __init__(
        self,
        service: "TrainingService",
        log_interval: int = 10,
    ) -> None:
        self.service = service
        self.log_interval = log_interval
        self.start_time = time.time()

    def on_train_begin(self, trainer: TrainerProtocol) -> None:
        # The worker owns STARTING -> RUNNING exactly once.  The callback only
        # measures elapsed time and records trainer metrics.
        self.start_time = time.time()

    def on_step_end(self, trainer: TrainerProtocol, step: int, loss: float) -> None:
        elapsed = time.time() - self.start_time
        self.service.record_step(
            step=step,
            loss=float(loss),
            lr=float(trainer.current_lr),
            elapsed=elapsed,
            emit=step % self.log_interval == 0 or step == trainer.max_iters,
        )

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: Dict[str, float]) -> None:
        self.service.record_eval(
            step=step,
            train_loss=float(metrics.get("train_loss", 0.0)),
            val_loss=float(metrics.get("val_loss", 0.0)),
            lr=float(trainer.current_lr),
        )

    def on_train_end(self, trainer: TrainerProtocol) -> None:
        # Trainer callbacks run before TrainingService knows the final semantic
        # termination reason, so emitting a status here would be stale/duplicate.
        return None


class TrainingService:
    """Service singleton điều phối huấn luyện mô hình nền cho Web UI với Pub/Sub Broadcast."""

    MAX_STEP_HISTORY = 3000
    MAX_EVAL_HISTORY = 1000
    MAX_SAMPLE_HISTORY = 200

    def __init__(self) -> None:
        self.status: str = "IDLE"  # IDLE, STARTING, RUNNING, STOPPING, STOPPED, COMPLETED, ERROR
        self.current_step: int = 0
        self.max_iters: int = 0
        self.current_loss: Optional[float] = None
        self.current_val_loss: Optional[float] = None
        self.current_lr: Optional[float] = None
        self.last_sample_text: str = ""
        self.error_message: Optional[str] = None
        self.termination_reason: Optional[str] = None
        self.run_id: int = 0
        self.sequence: int = 0
        self.trainer: Optional[Trainer] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._abort_requested = threading.Event()

        # Hệ thống Pub/Sub phát sóng đa thuê bao
        self._subscribers: List["queue.Queue[Dict[str, Any]]"] = []
        self._sub_lock = threading.Lock()

        self.history_steps: List[Dict[str, Any]] = []
        self.history_evals: List[Dict[str, Any]] = []
        self.sample_history: List[Dict[str, Any]] = []

    def register_subscriber(self) -> "queue.Queue[Dict[str, Any]]":
        """Đăng ký một subscriber mới cho kết nối SSE độc lập."""
        q: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=500)
        with self._sub_lock:
            self._subscribers.append(q)
        return q

    def unregister_subscriber(self, q: "queue.Queue[Dict[str, Any]]") -> None:
        """Hủy đăng ký subscriber khi client ngắt kết nối."""
        with self._sub_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def broadcast(self, evt: Dict[str, Any]) -> None:
        """Phát sóng sự kiện tới 100% tất cả các client đang kết nối."""
        with self._sub_lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(evt)
                except queue.Full:
                    # Bỏ qua nếu buffer client bị đầy để tránh nghẽn
                    pass

    def _snapshot_locked(self) -> Dict[str, Any]:
        """Return one coherent UI snapshot. Caller must hold ``_lock``."""
        return {
            "run_id": self.run_id,
            "sequence": self.sequence,
            "status": self.status,
            "termination_reason": self.termination_reason,
            "current_step": self.current_step,
            "max_iters": self.max_iters,
            "current_loss": self.current_loss,
            "current_val_loss": self.current_val_loss,
            "current_lr": self.current_lr,
            "last_sample_text": self.last_sample_text,
            "error_message": self.error_message,
            # REST/SSE init is authoritative for the server's bounded history.
            # Do not truncate it further here or clients cannot reconcile gaps.
            "history_steps": [dict(item) for item in self.history_steps],
            "history_evals": [dict(item) for item in self.history_evals],
            "sample_history": [dict(item) for item in self.sample_history],
        }

    def _next_sequence_locked(self) -> int:
        self.sequence += 1
        return self.sequence

    def _status_event_locked(self, message: str) -> Dict[str, Any]:
        self._next_sequence_locked()
        return {"type": "status", **self._snapshot_locked(), "message": message}

    def get_state(self) -> Dict[str, Any]:
        """Return an atomic, authoritative snapshot for REST polling/reconnect."""
        with self._lock:
            return self._snapshot_locked()

    def record_step(
        self,
        *,
        step: int,
        loss: float,
        lr: float,
        elapsed: float,
        emit: bool,
    ) -> None:
        event: Optional[Dict[str, Any]] = None
        with self._lock:
            self.current_step = step
            self.current_loss = round(float(loss), 4)
            self.current_lr = round(float(lr), 7)
            sequence = self._next_sequence_locked()
            if emit:
                event = {
                    "type": "step",
                    "run_id": self.run_id,
                    "sequence": sequence,
                    "step": step,
                    "loss": self.current_loss,
                    "lr": self.current_lr,
                    "elapsed": round(elapsed, 1),
                }
                self.history_steps.append(dict(event))
                if len(self.history_steps) > self.MAX_STEP_HISTORY:
                    del self.history_steps[: -self.MAX_STEP_HISTORY]
        if event is not None:
            self.broadcast(event)

    def record_eval(self, *, step: int, train_loss: float, val_loss: float, lr: float) -> None:
        with self._lock:
            self.current_val_loss = round(float(val_loss), 4)
            sequence = self._next_sequence_locked()
            event = {
                "type": "eval",
                "run_id": self.run_id,
                "sequence": sequence,
                "step": step,
                "train_loss": round(float(train_loss), 4),
                "val_loss": self.current_val_loss,
                "lr": round(float(lr), 7),
            }
            self.history_evals.append(dict(event))
            if len(self.history_evals) > self.MAX_EVAL_HISTORY:
                del self.history_evals[: -self.MAX_EVAL_HISTORY]
        self.broadcast(event)

    def record_sample(self, *, step: int, text: str) -> None:
        with self._lock:
            self.last_sample_text = text
            sequence = self._next_sequence_locked()
            event = {
                "type": "sample",
                "run_id": self.run_id,
                "sequence": sequence,
                "step": step,
                "text": text,
                "timestamp": time.strftime("%H:%M:%S"),
            }
            self.sample_history.append(dict(event))
            if len(self.sample_history) > self.MAX_SAMPLE_HISTORY:
                del self.sample_history[: -self.MAX_SAMPLE_HISTORY]
        self.broadcast(event)

    def clear_state(self) -> None:
        """Erase the terminal run only after the worker has fully cleaned up."""
        cleanup_thread: Optional[threading.Thread] = None
        with self._lock:
            if self.status in ("RUNNING", "STARTING"):
                raise RuntimeError("Không thể làm mới khi tiến trình huấn luyện đang chạy.")
            if self._thread and self._thread.is_alive():
                cleanup_thread = self._thread

        if cleanup_thread is threading.current_thread():
            raise RuntimeError("Không thể clear trạng thái từ chính worker huấn luyện đang chạy.")
        if cleanup_thread is not None:
            cleanup_thread.join(timeout=3.5)
            if cleanup_thread.is_alive():
                raise RuntimeError("Worker huấn luyện cũ chưa hoàn tất dọn dẹp; vui lòng thử lại.")

        with self._lock:
            if self.status in ("RUNNING", "STARTING", "STOPPING"):
                raise RuntimeError("Không thể làm mới khi tiến trình huấn luyện đang chạy.")
            self.status = "IDLE"
            self.termination_reason = None
            self.current_step = 0
            self.max_iters = 0
            self.current_loss = None
            self.current_val_loss = None
            self.current_lr = None
            self.last_sample_text = ""
            self.error_message = None
            self.history_steps.clear()
            self.history_evals.clear()
            self.sample_history.clear()
            event = self._status_event_locked("Đã làm mới thông tin huấn luyện.")

        self.broadcast(event)
        logger.info("Đã làm mới toàn bộ thông tin trạng thái huấn luyện (cleared state).")

    def _finish_abort(self) -> None:
        """Finish a user-requested abort during STARTING without inventing metrics."""
        with self._lock:
            self.status = "STOPPED"
            self.termination_reason = TrainingTerminationReason.ABORTED_STARTUP.value
            self.trainer = None
            event = self._status_event_locked(
                "Đã hủy bỏ khởi tạo huấn luyện an toàn theo yêu cầu người dùng."
            )
        self.broadcast(event)
        logger.info("Đã hủy bỏ khởi tạo huấn luyện an toàn (startup aborted).")

    def start_training(
        self,
        config_path: str = "configs/truyen_kieu.yaml",
        overrides: Optional[List[str]] = None,
        quick_check: bool = False,
        resume_checkpoint: Optional[str] = None,
        runtime_plan: Optional[ResolvedTrainingPlan] = None,
    ) -> None:
        """Start one exclusive background training run with versioned UI state."""
        old_thread: Optional[threading.Thread] = None
        with self._lock:
            if self.status in ("RUNNING", "STARTING"):
                raise RuntimeError(
                    f"Không thể khởi chạy: Tiến trình đang ở trạng thái '{self.status}'. "
                    "Vui lòng đợi tiến trình hoàn tất hoặc dừng hẳn trước khi bắt đầu lại."
                )
            if self.status == "STOPPING" or (self._thread and self._thread.is_alive()):
                old_thread = self._thread

        # Never join while holding _lock: the old worker acquires it in finally.
        if old_thread and old_thread.is_alive():
            logger.info("Đang đợi luồng huấn luyện trước đó giải phóng tài nguyên...")
            old_thread.join(timeout=3.5)
            if old_thread.is_alive():
                raise RuntimeError(
                    "Tiến trình huấn luyện trước đó vẫn chưa kết thúc hoặc đang giải phóng bộ nhớ GPU. "
                    "Vui lòng đợi 1-2 giây rồi thử lại."
                )

        with self._lock:
            if self.status in ("RUNNING", "STARTING", "STOPPING"):
                raise RuntimeError(
                    f"Không thể khởi chạy: Tiến trình đang ở trạng thái '{self.status}'. "
                    "Vui lòng đợi tiến trình hoàn tất hoặc dừng hẳn trước khi bắt đầu lại."
                )
            if self._thread and self._thread.is_alive():
                raise RuntimeError(
                    "Tiến trình huấn luyện trước đó vẫn đang trong quá trình giải phóng tài nguyên. "
                    "Vui lòng đợi 1-2 giây."
                )

            self._abort_requested.clear()
            self.run_id += 1
            self.sequence = 0
            self.status = "STARTING"
            self.termination_reason = None
            self.error_message = None
            self.current_step = 0
            self.max_iters = 0
            self.current_loss = None
            self.current_val_loss = None
            self.current_lr = None
            self.last_sample_text = ""
            self.trainer = None
            # A new UI run gets a new run_id. Reusing process-local history from a
            # previous run (even when resuming a checkpoint) would mislabel it.
            self.history_steps.clear()
            self.history_evals.clear()
            self.sample_history.clear()
            starting_event = self._status_event_locked(
                "Đang chuẩn bị dữ liệu và khởi tạo kiến trúc mạng..."
            )

        self.broadcast(starting_event)

        def train_worker() -> None:
            try:
                config = EngineConfig.from_yaml(config_path, overrides=overrides)
                configure_logging_from_system(
                    config.system, name="TrainingService", force_reconfigure=True
                )
                if quick_check:
                    config = config.copy(
                        training=config.training.copy(
                            max_iters=50,
                            eval_interval=25,
                            eval_iters=10,
                        )
                    )

                with self._lock:
                    self.max_iters = config.training.max_iters
                    config_event = self._status_event_locked("Đã nạp cấu hình huấn luyện.")
                self.broadcast(config_event)
                set_seed(config.system.seed)

                if self._abort_requested.is_set():
                    self._finish_abort()
                    return

                cleaner_kwargs = dict(config.data.cleaner_kwargs)
                cleaner_kwargs.setdefault("clean_line_numbers", config.data.clean_line_numbers)
                cleaner = get_cleaner(
                    cleaner_type=config.data.cleaner_type,
                    **cleaner_kwargs,
                )

                if self._abort_requested.is_set():
                    self._finish_abort()
                    return

                train_data, val_data, tokenizer = DataPipeline.setup_data(
                    config=config.data,
                    cleaner=cleaner,
                    block_size=config.model.block_size,
                )

                if self._abort_requested.is_set():
                    self._finish_abort()
                    return

                batch_provider = get_batch_provider(
                    provider_type=config.data.batch_provider_type,
                    train_data=train_data,
                    val_data=val_data,
                    block_size=config.model.block_size,
                    num_workers=config.data.num_workers,
                    pin_memory=config.data.pin_memory,
                )

                # Runtime model shape must use the tokenizer actually selected by
                # the data pipeline, not a stale YAML vocab_size.
                config = config.copy(model=config.model.copy(vocab_size=tokenizer.vocab_size))

                if self._abort_requested.is_set():
                    self._finish_abort()
                    return

                model = ModelRegistry.create(config.model.name, config.model)
                if self._abort_requested.is_set():
                    self._finish_abort()
                    return

                effective_runtime_plan = runtime_plan
                if effective_runtime_plan is None:
                    effective_runtime_plan = resolve_training_plan(config)
                else:
                    validate_training_plan(config, effective_runtime_plan)

                sample_gen: BaseGenerator = get_generator(
                    "local",
                    model=model,
                    tokenizer=tokenizer,
                    device=effective_runtime_plan.device,
                )
                sample_cfg = GenerationConfig(
                    max_new_tokens=60,
                    temperature=0.8,
                    top_k=40,
                    use_cache=True,
                )

                def sample_fn(step: int) -> str:
                    text = sample_gen.generate("Trăm năm", config=sample_cfg)
                    self.record_sample(step=step, text=text)
                    return text

                callbacks: List[BaseCallback] = [
                    WebMetricsCallback(service=self, log_interval=10),
                    SampleGenerationCallback(sample_fn=sample_fn),
                    EarlyStoppingCallback(
                        monitor="val_loss",
                        mode="min",
                        patience=config.training.early_stopping_patience,
                    ),
                    # Persist after stateful callbacks so resume snapshot is coherent.
                    ModelCheckpointCallback(
                        save_dir=config.training.checkpoint_dir,
                        filename=config.training.checkpoint_name,
                        monitor="val_loss",
                        mode="min",
                        save_top_k=config.training.save_top_k,
                        save_last=config.training.save_last,
                        run_name=config.training.run_name,
                    ),
                ]

                trainer = Trainer(
                    model=model,
                    batch_provider=batch_provider,
                    config=config,
                    callbacks=callbacks,
                    tokenizer=tokenizer,
                    runtime_plan=effective_runtime_plan,
                )

                with self._lock:
                    if self._abort_requested.is_set() or self.status == "STOPPING":
                        abort_before_trainer = True
                        running_event = None
                    else:
                        abort_before_trainer = False
                        self.trainer = trainer
                        self.status = "RUNNING"
                        running_event = self._status_event_locked("Bắt đầu huấn luyện mô hình.")

                if abort_before_trainer:
                    self._finish_abort()
                    return
                if running_event is not None:
                    self.broadcast(running_event)

                train_out: TrainOutput = trainer.train(resume_checkpoint=resume_checkpoint)

                with self._lock:
                    reason = train_out.termination_reason
                    user_stopped = (
                        train_out.interrupted or reason is TrainingTerminationReason.USER_STOPPED
                    )
                    if user_stopped:
                        self.status = "STOPPED"
                        self.termination_reason = TrainingTerminationReason.USER_STOPPED.value
                    else:
                        self.status = "COMPLETED"
                        self.termination_reason = reason.value
                    terminal_event = self._status_event_locked(
                        f"Huấn luyện kết thúc với trạng thái: {self.status}"
                    )
                self.broadcast(terminal_event)

            except Exception as e:
                logger.exception(f"Lỗi trong quá trình huấn luyện nền: {e}")
                with self._lock:
                    self.status = "ERROR"
                    self.termination_reason = TrainingTerminationReason.FAILED.value
                    self.error_message = str(e)
                    error_event = self._status_event_locked(str(e))
                self.broadcast(error_event)
            finally:
                cleanup_event: Optional[Dict[str, Any]] = None
                with self._lock:
                    self.trainer = None
                    if self.status in ("STARTING", "STOPPING"):
                        self.status = "STOPPED"
                        if self.termination_reason is None:
                            self.termination_reason = (
                                TrainingTerminationReason.ABORTED_STARTUP.value
                                if self.current_step == 0
                                else TrainingTerminationReason.USER_STOPPED.value
                            )
                        cleanup_event = self._status_event_locked(
                            "Tiến trình huấn luyện đã dừng và hoàn tất dọn dẹp."
                        )
                    final_status = self.status
                if cleanup_event is not None:
                    self.broadcast(cleanup_event)
                if torch.cuda.is_available():
                    try:
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
                logger.info(
                    f"Luồng huấn luyện nền đã hoàn tất dọn dẹp. Trạng thái cuối: {final_status}"
                )

        with self._lock:
            self._thread = threading.Thread(target=train_worker, daemon=True)
            thread = self._thread
        thread.start()

    def stop_training(self) -> None:
        """Request a safe stop without erasing terminal run metrics."""
        event: Optional[Dict[str, Any]] = None
        trainer: Optional[Trainer] = None
        with self._lock:
            if self.status == "STOPPING":
                logger.info("Yêu cầu dừng khi đang ở trạng thái STOPPING (đã nhận lệnh trước đó).")
                return

            if self.status == "STARTING":
                self.status = "STOPPING"
                self._abort_requested.set()
                event = self._status_event_locked("Đang hủy tiến trình khởi tạo...")
            elif self.status == "RUNNING":
                self.status = "STOPPING"
                self._abort_requested.set()
                trainer = self.trainer
                event = self._status_event_locked("Đang dừng huấn luyện an toàn...")
            else:
                logger.info(
                    f"Yêu cầu dừng được gửi nhưng trạng thái hiện tại là '{self.status}' (bỏ qua)."
                )
                return

        if trainer is not None:
            trainer.request_stop()
        if event is not None:
            self.broadcast(event)
        logger.info("Đã gửi tín hiệu dừng huấn luyện an toàn.")

    def stream_events(self) -> Generator[str, None, None]:
        """SSE stream with an authoritative versioned snapshot followed by deltas."""
        client_q = self.register_subscriber()

        try:
            initial_payload = json.dumps({"type": "init", **self.get_state()})
            yield f"data: {initial_payload}\n\n"

            while True:
                try:
                    evt = client_q.get(timeout=1.0)
                    yield f"data: {json.dumps(evt)}\n\n"
                except queue.Empty:
                    yield f": heartbeat {time.time()}\n\n"
        finally:
            self.unregister_subscriber(client_q)
