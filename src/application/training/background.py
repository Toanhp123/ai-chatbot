"""Background training lifecycle application service.

HTTP/SSE adapters call this service; concrete training assembly is delegated to
TrainingApplicationService so Web and CLI share one canonical run graph.
"""

import time
from typing import Any, Dict, Generator, List, Optional

from src.application.runtime.accelerator import AcceleratorCoordinator
from src.application.training.contracts import (
    TrainingPlan,
    TrainingPreparationAborted,
)
from src.application.training.service import TrainingApplicationService
from src.core.config import EngineConfig
from src.core.logging import get_logger
from src.training.api import (
    BackgroundExecution,
    BackgroundTask,
    TrainingControl,
    TrainingEventHub,
    TrainingTerminationReason,
)

logger = get_logger("TrainingService")


class _WebTrainingObserver:
    def __init__(self, service: "TrainingService") -> None:
        self.service = service

    def on_step(self, *, step: int, loss: float, lr: float, elapsed: float, emit: bool) -> None:
        self.service.record_step(step=step, loss=loss, lr=lr, elapsed=elapsed, emit=emit)

    def on_eval(self, *, step: int, train_loss: float, val_loss: float, lr: float) -> None:
        self.service.record_eval(step=step, train_loss=train_loss, val_loss=val_loss, lr=lr)

    def on_sample(self, *, step: int, text: str) -> None:
        self.service.record_sample(step=step, text=text)


class TrainingService:
    """Service singleton điều phối huấn luyện mô hình nền cho Web UI với Pub/Sub Broadcast."""

    MAX_STEP_HISTORY = 3000
    MAX_EVAL_HISTORY = 1000
    MAX_SAMPLE_HISTORY = 200

    def __init__(
        self,
        accelerator_coordinator: Optional[AcceleratorCoordinator] = None,
        training_application: Optional[TrainingApplicationService] = None,
        execution: Optional[BackgroundExecution] = None,
    ) -> None:
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
        self.trainer: Optional[TrainingControl] = None
        self._execution = execution or BackgroundExecution()
        self._thread: Optional[BackgroundTask] = None
        self._lock = self._execution.create_lock()
        self._abort_requested = self._execution.create_cancellation_signal()
        self._accelerator_coordinator = accelerator_coordinator
        self._training_application = training_application or TrainingApplicationService()

        self._events = TrainingEventHub(queue_size=500)

        self.history_steps: List[Dict[str, Any]] = []
        self.history_evals: List[Dict[str, Any]] = []
        self.sample_history: List[Dict[str, Any]] = []

    def broadcast(self, evt: Dict[str, Any]) -> None:
        """Publish one transport-neutral event to all current subscribers."""
        self._events.publish(evt)

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
        cleanup_thread: Optional[BackgroundTask] = None
        with self._lock:
            if self.status in ("RUNNING", "STARTING"):
                raise RuntimeError("Không thể làm mới khi tiến trình huấn luyện đang chạy.")
            if self._thread and self._thread.is_alive():
                cleanup_thread = self._thread

        if cleanup_thread is not None and self._execution.is_current_task(cleanup_thread):
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
        *,
        plan: TrainingPlan,
        admission_reserved: bool = False,
    ) -> None:
        """Start one exclusive background run from an already-resolved application plan."""
        old_thread: Optional[BackgroundTask] = None
        with self._lock:
            if self.status in ("RUNNING", "STARTING"):
                raise RuntimeError(
                    f"Không thể khởi chạy: Tiến trình đang ở trạng thái '{self.status}'. "
                    "Vui lòng đợi tiến trình hoàn tất hoặc dừng hẳn trước khi bắt đầu lại."
                )
            if self.status == "STOPPING" or (self._thread and self._thread.is_alive()):
                old_thread = self._thread

        if old_thread and old_thread.is_alive():
            logger.info("Đang đợi luồng huấn luyện trước đó giải phóng tài nguyên...")
            old_thread.join(timeout=3.5)
            if old_thread.is_alive():
                raise RuntimeError(
                    "Tiến trình huấn luyện trước đó vẫn chưa kết thúc hoặc đang giải phóng bộ nhớ GPU. "
                    "Vui lòng đợi 1-2 giây rồi thử lại."
                )

        frozen_plan = TrainingPlan(
            requested_config=EngineConfig.from_dict(plan.requested_config.to_dict()),
            config=EngineConfig.from_dict(plan.config.to_dict()),
            runtime_plan=plan.runtime_plan,
            feasibility=plan.feasibility,
            resume_checkpoint=plan.resume_checkpoint,
            resume_checkpoint_identity=plan.resume_checkpoint_identity,
        )
        admission_device = frozen_plan.runtime_plan.device
        reserved_accelerator = admission_reserved
        externally_reserved_admission = admission_reserved
        try:
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
                if self._accelerator_coordinator is not None and not reserved_accelerator:
                    self._accelerator_coordinator.reserve_training(admission_device)
                    reserved_accelerator = True

                self._abort_requested.clear()
                self.run_id += 1
                self.sequence = 0
                self.status = "STARTING"
                self.termination_reason = None
                self.error_message = None
                self.current_step = 0
                self.max_iters = frozen_plan.config.training.max_iters
                self.current_loss = None
                self.current_val_loss = None
                self.current_lr = None
                self.last_sample_text = ""
                self.trainer = None
                self.history_steps.clear()
                self.history_evals.clear()
                self.sample_history.clear()
                starting_event = self._status_event_locked(
                    "Đang chuẩn bị dữ liệu và khởi tạo kiến trúc mạng..."
                )
        except Exception:
            if (
                reserved_accelerator
                and not externally_reserved_admission
                and self._accelerator_coordinator is not None
            ):
                self._accelerator_coordinator.release_training(admission_device)
            raise

        self.broadcast(starting_event)

        def train_worker() -> None:
            try:
                prepared = self._training_application.prepare(
                    frozen_plan,
                    observer=_WebTrainingObserver(self),
                    abort_check=self._abort_requested.is_set,
                    log_interval=10,
                )
                with self._lock:
                    if self._abort_requested.is_set() or self.status == "STOPPING":
                        abort_before_trainer = True
                        running_event = None
                    else:
                        abort_before_trainer = False
                        self.trainer = prepared.trainer
                        self.status = "RUNNING"
                        running_event = self._status_event_locked("Bắt đầu huấn luyện mô hình.")
                if abort_before_trainer:
                    self._finish_abort()
                    return
                if running_event is not None:
                    self.broadcast(running_event)

                train_out = self._training_application.execute(prepared, frozen_plan)
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
            except TrainingPreparationAborted:
                self._finish_abort()
            except Exception as exc:
                logger.exception("Lỗi trong quá trình huấn luyện nền: %s", exc)
                with self._lock:
                    self.status = "ERROR"
                    self.termination_reason = TrainingTerminationReason.FAILED.value
                    self.error_message = str(exc)
                    error_event = self._status_event_locked(str(exc))
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
                if reserved_accelerator and self._accelerator_coordinator is not None:
                    self._accelerator_coordinator.release_training(admission_device)
                self._execution.cleanup_accelerator_cache()
                logger.info(
                    "Luồng huấn luyện nền đã hoàn tất dọn dẹp. Trạng thái cuối: %s",
                    final_status,
                )

        with self._lock:
            self._thread = self._execution.create_task(train_worker)
            thread = self._thread
        try:
            thread.start()
        except Exception as exc:
            with self._lock:
                if self._thread is thread:
                    self._thread = None
                self.status = "IDLE"
                self.termination_reason = TrainingTerminationReason.FAILED.value
                self.error_message = str(exc)
                rollback_event = self._status_event_locked(
                    "Không thể khởi chạy luồng huấn luyện; trạng thái đã được hoàn nguyên."
                )
            if (
                reserved_accelerator
                and not externally_reserved_admission
                and self._accelerator_coordinator is not None
            ):
                self._accelerator_coordinator.release_training(admission_device)
            self.broadcast(rollback_event)
            raise

    def stop_training(self) -> None:
        """Request a safe stop without erasing terminal run metrics."""
        event: Optional[Dict[str, Any]] = None
        trainer: Optional[TrainingControl] = None
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

    def iter_events(self) -> Generator[Dict[str, Any], None, None]:
        """Yield an authoritative snapshot followed by transport-neutral lifecycle events."""
        yield from self._events.iter_events(self.get_state)
