"""
Training Service: Quản lý tiến trình huấn luyện chạy nền (Background Thread),
hệ thống phát sóng sự kiện Pub/Sub đa thuê bao (Multi-subscriber Broadcast) và theo dõi metrics thời gian thực.
"""

import json
import queue
import threading
import time
from typing import Any, Dict, Iterator, List, Optional

import torch

from src.core.config import EngineConfig, GenerationConfig
from src.core.logging import get_logger
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
from src.training.trainer import Trainer, TrainOutput
from src.utils.seed import set_seed

logger = get_logger("TrainingService")


class WebMetricsCallback(BaseCallback):
    """Callback chuyên biệt thu thập chỉ số huấn luyện và phát sóng tới tất cả UI subscribers."""

    def __init__(
        self,
        service: "TrainingService",
        log_interval: int = 10,
    ) -> None:
        self.service = service
        self.log_interval = log_interval
        self.start_time = time.time()

    def on_train_begin(self, trainer: TrainerProtocol) -> None:
        self.start_time = time.time()
        self.service.status = "RUNNING"
        self.service.max_iters = trainer.max_iters
        evt = {
            "type": "status",
            "status": "RUNNING",
            "max_iters": trainer.max_iters,
            "message": "Bắt đầu phiên huấn luyện.",
        }
        self.service.broadcast(evt)

    def on_step_end(self, trainer: TrainerProtocol, step: int, loss: float) -> None:
        self.service.current_step = step
        self.service.current_loss = round(float(loss), 4)
        self.service.current_lr = round(float(trainer.current_lr), 7)

        if step % self.log_interval == 0 or step == trainer.max_iters:
            elapsed = time.time() - self.start_time
            data = {
                "type": "step",
                "step": step,
                "loss": self.service.current_loss,
                "lr": self.service.current_lr,
                "elapsed": round(elapsed, 1),
            }
            if len(self.service.history_steps) > 3000:
                self.service.history_steps.pop(0)
            self.service.history_steps.append(data)
            self.service.broadcast(data)

    def on_eval_end(self, trainer: TrainerProtocol, step: int, metrics: Dict[str, float]) -> None:
        train_loss = round(float(metrics.get("train_loss", 0.0)), 4)
        val_loss = round(float(metrics.get("val_loss", 0.0)), 4)
        self.service.current_val_loss = val_loss

        data = {
            "type": "eval",
            "step": step,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "lr": round(float(trainer.current_lr), 7),
        }
        self.service.history_evals.append(data)
        self.service.broadcast(data)

    def on_train_end(self, trainer: TrainerProtocol) -> None:
        elapsed = time.time() - self.start_time
        evt = {
            "type": "status",
            "status": self.service.status,
            "elapsed_total": round(elapsed, 1),
            "message": "Quá trình huấn luyện đã kết thúc.",
        }
        self.service.broadcast(evt)


class TrainingService:
    """Service singleton điều phối huấn luyện mô hình nền cho Web UI với Pub/Sub Broadcast."""

    def __init__(self) -> None:
        self.status: str = "IDLE"  # IDLE, STARTING, RUNNING, STOPPING, STOPPED, COMPLETED, ERROR
        self.current_step: int = 0
        self.max_iters: int = 0
        self.current_loss: Optional[float] = None
        self.current_val_loss: Optional[float] = None
        self.current_lr: Optional[float] = None
        self.last_sample_text: str = ""
        self.error_message: Optional[str] = None
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

    def get_state(self) -> Dict[str, Any]:
        """Trả về trạng thái hiện tại phục vụ REST API Polling Sync."""
        return {
            "status": self.status,
            "current_step": self.current_step,
            "max_iters": self.max_iters,
            "current_loss": self.current_loss,
            "current_val_loss": self.current_val_loss,
            "current_lr": self.current_lr,
            "last_sample_text": self.last_sample_text,
            "error_message": self.error_message,
            "history_steps": self.history_steps[-300:],  # 300 điểm gần nhất cho sync mượt mà
            "history_evals": self.history_evals,
            "sample_history": self.sample_history[-5:],
        }

    def clear_state(self) -> None:
        """Làm mới toàn bộ trạng thái số liệu huấn luyện về IDLE ban đầu."""
        with self._lock:
            if self.status in ("RUNNING", "STARTING"):
                raise RuntimeError("Không thể làm mới khi tiến trình huấn luyện đang chạy.")
            self.status = "IDLE"
            self.current_step = 0
            self.current_loss = None
            self.current_val_loss = None
            self.current_lr = None
            self.last_sample_text = ""
            self.error_message = None
            self.history_steps.clear()
            self.history_evals.clear()
            self.sample_history.clear()

        self.broadcast(
            {
                "type": "status",
                "status": "IDLE",
                "current_step": 0,
                "current_loss": None,
                "current_val_loss": None,
                "current_lr": None,
                "last_sample_text": "",
                "history_steps": [],
                "history_evals": [],
                "sample_history": [],
                "message": "Đã làm mới thông tin huấn luyện.",
            }
        )
        logger.info("Đã làm mới toàn bộ thông tin trạng thái huấn luyện (cleared state).")

    def _finish_abort(self) -> None:
        """Kết thúc và dọn dẹp an toàn khi người dùng hủy bỏ huấn luyện ở giai đoạn STARTING."""
        with self._lock:
            self.status = "STOPPED"
            self.trainer = None
            self.current_step = 0
            self.current_loss = None
            self.current_val_loss = None
            self.current_lr = None
            self.last_sample_text = ""
            self.history_steps.clear()
            self.history_evals.clear()
            self.sample_history.clear()
        self.broadcast(
            {
                "type": "status",
                "status": "STOPPED",
                "current_step": 0,
                "current_loss": None,
                "current_val_loss": None,
                "current_lr": None,
                "last_sample_text": "",
                "history_steps": [],
                "history_evals": [],
                "sample_history": [],
                "message": "Đã hủy bỏ khởi tạo huấn luyện an toàn theo yêu cầu người dùng.",
            }
        )
        logger.info("Đã hủy bỏ khởi tạo huấn luyện an toàn (startup aborted).")

    def start_training(
        self,
        config_path: str = "configs/truyen_kieu.yaml",
        overrides: Optional[List[str]] = None,
        quick_check: bool = False,
        resume_checkpoint: Optional[str] = None,
    ) -> None:
        """Khởi chạy huấn luyện trên luồng riêng biệt (Background Thread) với khóa chống spam và đảm bảo độc quyền luồng."""
        # 1. Kiểm tra trạng thái sơ bộ và đợi luồng cũ ngoài lock (nếu luồng cũ đang kết thúc)
        old_thread = None
        with self._lock:
            if self.status in ("RUNNING", "STARTING"):
                raise RuntimeError(
                    f"Không thể khởi chạy: Tiến trình đang ở trạng thái '{self.status}'. "
                    "Vui lòng đợi tiến trình hoàn tất hoặc dừng hẳn trước khi bắt đầu lại."
                )
            if self.status == "STOPPING" or (self._thread and self._thread.is_alive()):
                old_thread = self._thread

        # Đợi luồng cũ kết thúc ngoài lock để tránh deadlock khi luồng cũ acquire lock trong finally
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
            self.status = "STARTING"
            self.error_message = None
            self.current_step = 0
            self.current_loss = None
            self.current_val_loss = None
            self.trainer = None

            # Nếu không resume từ checkpoint cũ, làm mới lịch sử
            if not resume_checkpoint:
                self.history_steps.clear()
                self.history_evals.clear()
                self.sample_history.clear()

            self.broadcast(
                {
                    "type": "status",
                    "status": "STARTING",
                    "message": "Đang chuẩn bị dữ liệu và khởi tạo kiến trúc mạng...",
                }
            )

            def train_worker() -> None:
                try:
                    config = EngineConfig.from_yaml(config_path, overrides=overrides)
                    if quick_check:
                        config.training.max_iters = 50
                        config.training.eval_interval = 25
                        config.training.eval_iters = 10

                    self.max_iters = config.training.max_iters
                    set_seed(config.system.seed)

                    if self._abort_requested.is_set():
                        self._finish_abort()
                        return

                    # 1. Cleaner
                    cleaner_kwargs = dict(config.data.cleaner_kwargs)
                    cleaner_kwargs.setdefault("clean_line_numbers", config.data.clean_line_numbers)
                    cleaner = get_cleaner(
                        cleaner_type=config.data.cleaner_type,
                        **cleaner_kwargs,
                    )

                    if self._abort_requested.is_set():
                        self._finish_abort()
                        return

                    # 2. DataPipeline
                    train_data, val_data, tokenizer = DataPipeline.setup_data(
                        config=config.data,
                        cleaner=cleaner,
                    )

                    if self._abort_requested.is_set():
                        self._finish_abort()
                        return

                    # 3. Batch Provider
                    batch_provider = get_batch_provider(
                        provider_type=config.data.batch_provider_type,
                        train_data=train_data,
                        val_data=val_data,
                        block_size=config.model.block_size,
                        num_workers=config.data.num_workers,
                        pin_memory=config.data.pin_memory,
                    )

                    config.model.vocab_size = tokenizer.vocab_size

                    if self._abort_requested.is_set():
                        self._finish_abort()
                        return

                    # 4. Model
                    model = ModelRegistry.create(config.model.name, config.model)

                    # 5. Callbacks
                    device_str = (
                        "cuda"
                        if (
                            config.system.device == "cuda"
                            or (config.system.device == "auto" and torch.cuda.is_available())
                        )
                        else "cpu"
                    )
                    sample_gen: BaseGenerator = get_generator(
                        "local", model=model, tokenizer=tokenizer, device=device_str
                    )
                    sample_cfg = GenerationConfig(
                        max_new_tokens=60,
                        temperature=0.8,
                        top_k=40,
                        use_cache=True,
                    )

                    def sample_fn(step: int) -> str:
                        text = sample_gen.generate("Trăm năm", config=sample_cfg)
                        self.last_sample_text = text
                        sample_record = {
                            "type": "sample",
                            "step": step,
                            "text": text,
                            "timestamp": time.strftime("%H:%M:%S"),
                        }
                        self.sample_history.append(sample_record)
                        self.broadcast(sample_record)
                        return text

                    web_cb = WebMetricsCallback(
                        service=self,
                        log_interval=10,
                    )

                    callbacks: List[BaseCallback] = [
                        web_cb,
                        ModelCheckpointCallback(
                            save_dir=config.training.checkpoint_dir,
                            filename=config.training.checkpoint_name,
                            monitor="val_loss",
                            mode="min",
                            save_top_k=config.training.save_top_k,
                            save_last=config.training.save_last,
                            run_name=config.training.run_name,
                        ),
                        SampleGenerationCallback(sample_fn=sample_fn),
                        EarlyStoppingCallback(
                            monitor="val_loss",
                            mode="min",
                            patience=config.training.early_stopping_patience,
                        ),
                    ]

                    # 6. Trainer
                    abort_before_trainer = False
                    with self._lock:
                        if self._abort_requested.is_set():
                            abort_before_trainer = True
                        else:
                            self.trainer = Trainer(
                                model=model,
                                batch_provider=batch_provider,
                                config=config,
                                callbacks=callbacks,
                            )
                            self.status = "RUNNING"

                    if abort_before_trainer:
                        self._finish_abort()
                        return

                    self.broadcast(
                        {
                            "type": "status",
                            "status": "RUNNING",
                            "max_iters": self.max_iters,
                            "message": "Bắt đầu huấn luyện mô hình.",
                        }
                    )

                    train_out: TrainOutput = self.trainer.train(resume_checkpoint=resume_checkpoint)

                    with self._lock:
                        if (
                            train_out.interrupted
                            or self._abort_requested.is_set()
                            or self.status == "STOPPING"
                        ):
                            self.status = "STOPPED"
                            self.current_step = 0
                            self.current_loss = None
                            self.current_val_loss = None
                            self.current_lr = None
                            self.last_sample_text = ""
                            self.history_steps.clear()
                            self.history_evals.clear()
                            self.sample_history.clear()
                        else:
                            self.status = "COMPLETED"

                    self.broadcast(
                        {
                            "type": "status",
                            "status": self.status,
                            "current_step": self.current_step,
                            "current_loss": self.current_loss,
                            "current_val_loss": self.current_val_loss,
                            "current_lr": self.current_lr,
                            "last_sample_text": self.last_sample_text,
                            "history_steps": list(self.history_steps),
                            "history_evals": list(self.history_evals),
                            "sample_history": list(self.sample_history),
                            "message": f"Huấn luyện kết thúc với trạng thái: {self.status}",
                        }
                    )

                except Exception as e:
                    logger.exception(f"Lỗi trong quá trình huấn luyện nền: {e}")
                    with self._lock:
                        self.status = "ERROR"
                        self.error_message = str(e)
                    self.broadcast(
                        {
                            "type": "status",
                            "status": "ERROR",
                            "message": str(e),
                        }
                    )
                finally:
                    with self._lock:
                        self.trainer = None
                        if self.status in ("STARTING", "STOPPING"):
                            self.status = "STOPPED"
                        if self.status == "STOPPED":
                            self.current_step = 0
                            self.current_loss = None
                            self.current_val_loss = None
                            self.current_lr = None
                            self.last_sample_text = ""
                            self.history_steps.clear()
                            self.history_evals.clear()
                            self.sample_history.clear()
                    if torch.cuda.is_available():
                        try:
                            torch.cuda.empty_cache()
                        except Exception:
                            pass
                    logger.info(
                        f"Luồng huấn luyện nền đã hoàn tất dọn dẹp. Trạng thái cuối: {self.status}"
                    )

            self._thread = threading.Thread(target=train_worker, daemon=True)
            self._thread.start()

    def stop_training(self) -> None:
        """Yêu cầu dừng huấn luyện an toàn ở bất kỳ giai đoạn nào."""
        with self._lock:
            if self.status == "STOPPING":
                logger.info("Yêu cầu dừng khi đang ở trạng thái STOPPING (đã nhận lệnh trước đó).")
                return

            if self.status == "STARTING":
                self.status = "STOPPING"
                self._abort_requested.set()
                self.broadcast(
                    {
                        "type": "status",
                        "status": "STOPPING",
                        "message": "Đang hủy tiến trình khởi tạo...",
                    }
                )
                logger.info("Yêu cầu dừng khi đang ở trạng thái STARTING.")
                return

            if self.status == "RUNNING":
                self.status = "STOPPING"
                self._abort_requested.set()
                if self.trainer:
                    self.trainer.request_stop()
                self.broadcast(
                    {
                        "type": "status",
                        "status": "STOPPING",
                        "message": "Đang dừng huấn luyện an toàn...",
                    }
                )
                logger.info("Đã gửi tín hiệu dừng huấn luyện an toàn (request_stop).")
                return

            logger.info(
                f"Yêu cầu dừng được gửi nhưng trạng thái hiện tại là '{self.status}' (bỏ qua)."
            )

    def stream_events(self) -> Iterator[str]:
        """SSE stream phát sự kiện huấn luyện độc lập cho từng client bằng Pub/Sub."""
        client_q = self.register_subscriber()

        try:
            # Gửi dữ liệu lịch sử đầu tiên cho client mới kết nối
            initial_payload = json.dumps(
                {
                    "type": "init",
                    "status": self.status,
                    "history_steps": self.history_steps[-300:],
                    "history_evals": self.history_evals,
                    "sample_history": self.sample_history[-5:],
                    "current_step": self.current_step,
                    "current_loss": self.current_loss,
                    "current_val_loss": self.current_val_loss,
                    "max_iters": self.max_iters,
                }
            )
            yield f"data: {initial_payload}\n\n"

            while True:
                try:
                    # Đợi sự kiện mới trong tối đa 1.0 giây
                    evt = client_q.get(timeout=1.0)
                    yield f"data: {json.dumps(evt)}\n\n"
                except queue.Empty:
                    # Gửi heartbeat giữ kết nối SSE
                    yield f": heartbeat {time.time()}\n\n"
        finally:
            self.unregister_subscriber(client_q)
