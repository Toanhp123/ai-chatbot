"""
Hệ thống Logging & Metrics tập trung cho AI Engine.
Bao gồm:
- Formatters: Console, File xoay vòng, JSON Lines
- Handlers: Rich console, Rotating file, JSON metric
- MetricLogger: Theo dõi và kết xuất chỉ số huấn luyện (Loss, VRAM, Throughput)
- LogManager / setup_logger / get_logger: Quản lý cấu hình logger tập trung, idempotent
"""

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Any, Dict, List, Optional, TextIO, Union

from src.core.exceptions import AIEngineError

# ==============================================================================
# 1. Formatters
# ==============================================================================


class StandardConsoleFormatter(logging.Formatter):
    """Định dạng cơ bản cho Console khi không sử dụng Rich."""

    def __init__(self) -> None:
        super().__init__(
            fmt="[%(asctime)s] [%(levelname)-7s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class FileLogFormatter(logging.Formatter):
    """Định dạng chuẩn cho file log xoay vòng (.log)."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class JSONLogFormatter(logging.Formatter):
    """Định dạng JSON Lines cho các công cụ giám sát (Grafana, ELK, Datadog)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Trích xuất ngữ cảnh nếu có từ LogContextFilter
        for ctx_key in ("run_id", "experiment", "rank"):
            if hasattr(record, ctx_key):
                log_entry[ctx_key] = getattr(record, ctx_key)

        # Trích xuất ngoại lệ chi tiết
        if record.exc_info:
            _, exc_val, _ = record.exc_info
            log_entry["exception"] = self.formatException(record.exc_info)
            if isinstance(exc_val, AIEngineError):
                log_entry["ai_error"] = {
                    "code": str(exc_val.error_code),
                    "severity": str(exc_val.severity),
                    "is_recoverable": exc_val.is_recoverable,
                    "details": exc_val.details,
                    "suggestion": exc_val.suggestion,
                }

        return json.dumps(log_entry, ensure_ascii=False)


# ==============================================================================
# 2. Handlers & Context
# ==============================================================================


class LogContext:
    """Quản lý biến ngữ cảnh log toàn cục/phiên chạy (Run Tracker)."""

    _context: Dict[str, Any] = {}

    @classmethod
    def set(cls, **kwargs: Any) -> None:
        """Thiết lập các biến ngữ cảnh (ví dụ run_id, rank, experiment)."""
        cls._context.update(kwargs)

    @classmethod
    def get(cls) -> Dict[str, Any]:
        """Lấy bản sao ngữ cảnh hiện tại."""
        return dict(cls._context)

    @classmethod
    def clear(cls) -> None:
        """Xóa sạch ngữ cảnh."""
        cls._context.clear()


class LogContextFilter(logging.Filter):
    """Gắn các biến ngữ cảnh từ LogContext vào từng LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        for k, v in LogContext.get().items():
            if not hasattr(record, k):
                setattr(record, k, v)
        return True


def create_console_handler(
    level: Union[str, int] = logging.INFO,
    use_rich: bool = True,
) -> logging.Handler:
    """Tạo Console Handler với hỗ trợ Rich màu sắc hoặc fallback chuẩn."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    if use_rich:
        try:
            from rich.logging import RichHandler

            handler = RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_path=False,
                markup=True,
            )
            handler.setLevel(level)
            return handler
        except ImportError:
            pass

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(StandardConsoleFormatter())
    return handler


def create_rotating_file_handler(
    filepath: str,
    level: Union[str, int] = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    formatter: Optional[logging.Formatter] = None,
) -> logging.Handler:
    """Tạo Rotating File Handler tự động xoay vòng file khi vượt dung lượng."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.DEBUG)

    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    handler = RotatingFileHandler(
        abs_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter or FileLogFormatter())
    return handler


def create_json_metric_handler(
    filepath: str,
    level: Union[str, int] = logging.INFO,
    max_bytes: int = 20 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Handler:
    """Tạo JSONL Handler chuyên dụng cho metric huấn luyện hoặc giám sát."""
    return create_rotating_file_handler(
        filepath=filepath,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
        formatter=JSONLogFormatter(),
    )


def create_timed_rotating_file_handler(
    filepath: str,
    level: Union[str, int] = logging.INFO,
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 7,
    formatter: Optional[logging.Formatter] = None,
) -> logging.Handler:
    """Tạo TimedRotatingFileHandler tự động xoay file log theo chu kỳ thời gian (ngày/giờ)."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    handler = TimedRotatingFileHandler(
        abs_path,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter or FileLogFormatter())
    return handler


# ==============================================================================
# 3. MetricLogger
# ==============================================================================


class MetricLogger:
    """Theo dõi, lưu trữ và kết xuất các chỉ số huấn luyện (Loss, LR, VRAM, Throughput)."""

    def __init__(
        self,
        filepath: Optional[str] = "logs/metrics.jsonl",
        buffered: bool = False,
    ) -> None:
        self.filepath = filepath
        self.buffered = buffered
        self.history: List[Dict[str, Any]] = []
        self._file_handle: Optional[TextIO] = None

        if self.filepath:
            abs_path = os.path.abspath(self.filepath)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            if self.buffered:
                self._file_handle = open(abs_path, "a", encoding="utf-8")

    def log_metrics(self, metrics: Dict[str, float], step: int) -> None:
        """Ghi nhận dictionary metrics tại một step."""
        entry: Dict[str, Any] = {
            "type": "metric",
            "timestamp": datetime.now().isoformat(),
            "step": step,
        }
        entry.update(metrics)
        self._record(entry)

    def flush(self) -> None:
        """Xả toàn bộ dữ liệu từ bộ đệm ra đĩa."""
        if self._file_handle and not self._file_handle.closed:
            try:
                self._file_handle.flush()
            except Exception:
                pass

    def close(self) -> None:
        """Đóng an toàn file handle nếu đang hoạt động."""
        if self._file_handle and not self._file_handle.closed:
            try:
                self._file_handle.flush()
                self._file_handle.close()
            except Exception:
                pass
            finally:
                self._file_handle = None

    def __enter__(self) -> "MetricLogger":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    def log_step(
        self,
        step: int,
        loss: float,
        lr: Optional[float] = None,
        vram_mb: Optional[float] = None,
        tokens_per_sec: Optional[float] = None,
        **extra_metrics: Any,
    ) -> Dict[str, Any]:
        """Ghi nhận chỉ số của một bước huấn luyện (step)."""
        entry: Dict[str, Any] = {
            "type": "step",
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "loss": float(loss),
        }
        if lr is not None:
            entry["lr"] = float(lr)
        if vram_mb is not None:
            entry["vram_mb"] = float(vram_mb)
        if tokens_per_sec is not None:
            entry["tokens_per_sec"] = float(tokens_per_sec)

        for k, v in extra_metrics.items():
            entry[k] = v

        self._record(entry)
        return entry

    def log_epoch(
        self,
        epoch: int,
        val_loss: Optional[float] = None,
        train_loss: Optional[float] = None,
        **extra_metrics: Any,
    ) -> Dict[str, Any]:
        """Ghi nhận chỉ số tổng kết một epoch."""
        entry: Dict[str, Any] = {
            "type": "epoch",
            "timestamp": datetime.now().isoformat(),
            "epoch": epoch,
        }
        if val_loss is not None:
            entry["val_loss"] = float(val_loss)
        if train_loss is not None:
            entry["train_loss"] = float(train_loss)

        for k, v in extra_metrics.items():
            entry[k] = v

        self._record(entry)
        return entry

    def _record(self, entry: Dict[str, Any]) -> None:
        """Lưu vào danh sách lịch sử và append vào file JSONL."""
        self.history.append(entry)
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        if self._file_handle and not self._file_handle.closed:
            try:
                self._file_handle.write(line)
            except Exception:
                pass
        elif self.filepath:
            try:
                with open(self.filepath, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass

    def get_history(self) -> List[Dict[str, Any]]:
        """Lấy toàn bộ lịch sử chỉ số."""
        return list(self.history)

    def get_best_metric(
        self, metric_key: str = "loss", mode: str = "min"
    ) -> Optional[Dict[str, Any]]:
        """Tìm bản ghi tốt nhất dựa trên một metric nhất định."""
        valid_entries = [
            e for e in self.history if metric_key in e and isinstance(e[metric_key], (int, float))
        ]
        if not valid_entries:
            return None

        if mode == "min":
            return min(valid_entries, key=lambda x: x[metric_key])
        else:
            return max(valid_entries, key=lambda x: x[metric_key])

    def print_summary(self) -> None:
        """Hiển thị bảng tóm tắt chỉ số huấn luyện."""
        if not self.history:
            print("Chưa có chỉ số huấn luyện nào được ghi nhận.")
            return

        best_loss_entry = self.get_best_metric("loss", mode="min")
        best_val_entry = self.get_best_metric("val_loss", mode="min")

        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(
                title="Tổng kết Chỉ số Huấn luyện (Training Metrics Summary)", show_header=True
            )
            table.add_column("Chỉ số", style="cyan", justify="left")
            table.add_column("Giá trị", style="green", justify="right")
            table.add_column("Thông tin bổ sung", style="yellow", justify="left")

            table.add_row(
                "Tổng số bản ghi", str(len(self.history)), f"File: {self.filepath or 'N/A'}"
            )

            if best_loss_entry:
                table.add_row(
                    "Min Train Loss",
                    f"{best_loss_entry['loss']:.4f}",
                    f"Tại Step {best_loss_entry.get('step', 'N/A')}",
                )

            if best_val_entry:
                table.add_row(
                    "Min Validation Loss",
                    f"{best_val_entry['val_loss']:.4f}",
                    f"Tại Epoch {best_val_entry.get('epoch', 'N/A')}",
                )

            console.print(table)
        except ImportError:
            print("\n=== Tổng kết Chỉ số Huấn luyện ===")
            print(f"Tổng số bản ghi: {len(self.history)}")
            if best_loss_entry:
                print(
                    f"Min Train Loss: {best_loss_entry['loss']:.4f} (Step {best_loss_entry.get('step')})"
                )
            if best_val_entry:
                print(
                    f"Min Val Loss: {best_val_entry['val_loss']:.4f} (Epoch {best_val_entry.get('epoch')})"
                )
            print("===================================\n")

    def clear(self) -> None:
        """Xóa lịch sử in-memory."""
        self.history.clear()


# ==============================================================================
# 4. LogManager & Public API
# ==============================================================================


class LogManager:
    """Quản trị viên cấu hình Logger tập trung cho toàn bộ hệ thống."""

    _initialized: bool = False
    _metric_logger: Optional[MetricLogger] = None
    _managed_handlers: List[logging.Handler] = []

    @classmethod
    def setup(
        cls,
        name: str = "ai-train",
        level: Union[str, int] = "INFO",
        log_file: Optional[str] = "logs/train.log",
        json_file: Optional[str] = None,
        use_rich: bool = True,
        force_reconfigure: bool = False,
        run_id: Optional[str] = None,
        experiment: Optional[str] = None,
    ) -> logging.Logger:
        """Khởi tạo và cấu hình root logger cùng các handler đa kênh."""
        if run_id:
            LogContext.set(run_id=run_id)
        if experiment:
            LogContext.set(experiment=experiment)

        if isinstance(level, str):
            level_int = getattr(logging, level.upper(), logging.INFO)
        else:
            level_int = level

        root_logger = logging.getLogger()

        if not cls._initialized or force_reconfigure:
            for h in list(cls._managed_handlers):
                if h in root_logger.handlers:
                    root_logger.removeHandler(h)
                    try:
                        h.close()
                    except Exception:
                        pass
            cls._managed_handlers.clear()

            # 1. Console Handler
            console_h = create_console_handler(level=level_int, use_rich=use_rich)
            root_logger.addHandler(console_h)
            cls._managed_handlers.append(console_h)

            # 2. Rotating File Handler
            if log_file:
                file_h = create_rotating_file_handler(
                    filepath=log_file,
                    level=logging.DEBUG,
                )
                root_logger.addHandler(file_h)
                cls._managed_handlers.append(file_h)

            # 3. JSON Metric Handler
            if json_file:
                json_h = create_json_metric_handler(
                    filepath=json_file,
                    level=logging.INFO,
                )
                root_logger.addHandler(json_h)
                cls._managed_handlers.append(json_h)

            context_filter = LogContextFilter()
            root_logger.addFilter(context_filter)

            root_logger.setLevel(logging.DEBUG)
            cls._initialized = True

        return logging.getLogger(name)

    @classmethod
    def get_logger(cls, name: str = "ai-train") -> logging.Logger:
        """Lấy instance Logger theo tên phân cấp. Tự khởi tạo nếu chưa setup."""
        if not cls._initialized:
            cls.setup(name=name)
        return logging.getLogger(name)

    @classmethod
    def get_metric_logger(
        cls, filepath: str = "logs/metrics.jsonl", buffered: bool = False
    ) -> MetricLogger:
        """Lấy instance MetricLogger duy nhất hoặc tạo mới."""
        if cls._metric_logger is None or cls._metric_logger.filepath != filepath:
            cls._metric_logger = MetricLogger(filepath=filepath, buffered=buffered)
        return cls._metric_logger


def setup_logger(
    name: str = "ai-train",
    level: Union[str, int] = "INFO",
    log_file: Optional[str] = "logs/train.log",
    json_file: Optional[str] = None,
    use_rich: bool = True,
    force_reconfigure: bool = False,
    run_id: Optional[str] = None,
    experiment: Optional[str] = None,
) -> logging.Logger:
    """Hàm tiện ích tương thích ngược để khởi tạo logger."""
    return LogManager.setup(
        name=name,
        level=level,
        log_file=log_file,
        json_file=json_file,
        use_rich=use_rich,
        force_reconfigure=force_reconfigure,
        run_id=run_id,
        experiment=experiment,
    )


def get_logger(name: str = "ai-train") -> logging.Logger:
    """Hàm tiện ích tương thích ngược để lấy logger."""
    return LogManager.get_logger(name=name)


def get_metric_logger(filepath: str = "logs/metrics.jsonl", buffered: bool = False) -> MetricLogger:
    """Hàm tiện ích lấy MetricLogger."""
    return LogManager.get_metric_logger(filepath=filepath, buffered=buffered)


__all__ = [
    "StandardConsoleFormatter",
    "FileLogFormatter",
    "JSONLogFormatter",
    "LogContext",
    "LogContextFilter",
    "create_console_handler",
    "create_rotating_file_handler",
    "create_json_metric_handler",
    "create_timed_rotating_file_handler",
    "MetricLogger",
    "LogManager",
    "setup_logger",
    "get_logger",
    "get_metric_logger",
]
