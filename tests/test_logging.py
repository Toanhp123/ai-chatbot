import json
import logging

from src.core.exceptions import ConfigurationError
from src.core.logging import (
    FileLogFormatter,
    JSONLogFormatter,
    LogContext,
    LogContextFilter,
    MetricLogger,
    StandardConsoleFormatter,
    create_console_handler,
    create_json_metric_handler,
    create_rotating_file_handler,
    create_timed_rotating_file_handler,
    get_logger,
    get_metric_logger,
    setup_logger,
)


def test_standard_console_formatter():
    formatter = StandardConsoleFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "[INFO   ]" in formatted
    assert "[test_logger]" in formatted
    assert "Test message" in formatted


def test_file_log_formatter():
    formatter = FileLogFormatter()
    record = logging.LogRecord(
        name="ai-train.test",
        level=logging.DEBUG,
        pathname="src/test.py",
        lineno=42,
        msg="File debug msg",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "DEBUG   " in formatted
    assert "ai-train.test" in formatted
    assert "test.py:42" in formatted
    assert "File debug msg" in formatted


def test_json_log_formatter():
    formatter = JSONLogFormatter()
    try:
        raise ValueError("Lỗi thử nghiệm JSON")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="json_test",
        level=logging.ERROR,
        pathname="src/json_test.py",
        lineno=100,
        msg="Có lỗi xảy ra",
        args=(),
        exc_info=exc_info,
    )
    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "ERROR"
    assert data["logger"] == "json_test"
    assert data["message"] == "Có lỗi xảy ra"
    assert data["source"]["line"] == 100
    assert "exception" in data
    assert "ValueError: Lỗi thử nghiệm JSON" in data["exception"]


def test_handlers_creation(tmp_path):
    console_h = create_console_handler(level="WARNING", use_rich=False)
    assert console_h.level == logging.WARNING

    log_file = tmp_path / "sub" / "test.log"
    file_h = create_rotating_file_handler(str(log_file), level="DEBUG")
    assert file_h.level == logging.DEBUG
    assert log_file.parent.exists()
    file_h.close()

    metric_file = tmp_path / "metrics.jsonl"
    json_h = create_json_metric_handler(str(metric_file), level="INFO")
    assert json_h.level == logging.INFO
    json_h.close()


def test_log_manager_and_backward_compatibility(tmp_path):
    log_file = tmp_path / "train.log"
    logger = setup_logger(
        name="test_app",
        level="INFO",
        log_file=str(log_file),
        use_rich=False,
        force_reconfigure=True,
    )

    assert logger.name == "test_app"
    logger.info("Test info message")

    # Kiểm tra get_logger
    same_logger = get_logger("test_app")
    assert same_logger is logger

    # Xác minh file log đã được ghi
    assert log_file.exists()
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Test info message" in content


def test_metric_logger(tmp_path):
    metric_file = tmp_path / "metrics.jsonl"
    metric_logger = MetricLogger(filepath=str(metric_file))

    metric_logger.log_step(step=10, loss=2.5, lr=0.001, vram_mb=1200.0, tokens_per_sec=500.0)
    metric_logger.log_step(step=20, loss=1.8, lr=0.0009, vram_mb=1250.0, tokens_per_sec=510.0)
    metric_logger.log_epoch(epoch=1, val_loss=1.95, train_loss=2.15)

    history = metric_logger.get_history()
    assert len(history) == 3

    best_loss = metric_logger.get_best_metric(metric_key="loss", mode="min")
    assert best_loss is not None
    assert best_loss["step"] == 20
    assert best_loss["loss"] == 1.8

    best_val = metric_logger.get_best_metric(metric_key="val_loss", mode="min")
    assert best_val is not None
    assert best_val["val_loss"] == 1.95

    # Test file JSONL output
    assert metric_file.exists()
    with open(metric_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 3
    assert lines[0]["loss"] == 2.5

    # Test print_summary does not raise
    metric_logger.print_summary()

    metric_logger.clear()
    assert len(metric_logger.get_history()) == 0


def test_metric_logger_context_manager(tmp_path):
    metric_file = tmp_path / "metrics_ctx.jsonl"
    logger = get_metric_logger(filepath=str(metric_file), buffered=True)

    assert isinstance(logger, MetricLogger)

    # Use context manager
    with logger as m:
        m.log_metrics({"train_loss": 0.45, "lr": 0.0005}, step=1)
        m.log_metrics({"train_loss": 0.32, "lr": 0.0004}, step=2)
        m.flush()

    # Verify file content after context exit (which auto-flushes & closes)
    assert metric_file.exists()
    with open(metric_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    assert len(records) == 2
    assert records[0]["step"] == 1
    assert records[0]["train_loss"] == 0.45
    assert records[1]["step"] == 2
    assert records[1]["train_loss"] == 0.32


def test_metric_logger_buffered_mode_manual(tmp_path):
    metric_file = tmp_path / "buffered_metrics.jsonl"
    ml = MetricLogger(filepath=str(metric_file), buffered=True)
    ml.log_metrics({"val_acc": 0.92}, step=10)
    ml.log_step(step=20, loss=0.15)
    ml.flush()
    ml.close()

    with open(metric_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    assert len(records) == 2
    assert records[0]["val_acc"] == 0.92
    assert records[1]["loss"] == 0.15


def test_json_log_formatter_ai_engine_error_extraction():
    formatter = JSONLogFormatter()
    try:
        raise ConfigurationError(
            message="Invalid model dimension configuration",
            details={"dim": -1, "expected": "> 0"},
            suggestion="Check hidden_dim in your config YAML",
        )
    except ConfigurationError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="ai-train.config",
        level=logging.ERROR,
        pathname="src/core/config/base.py",
        lineno=50,
        msg="Failed to parse model configuration",
        args=(),
        exc_info=exc_info,
    )
    # Gắn thêm context fields
    record.run_id = "run-2026-abc"
    record.experiment = "exp-bert-lora"
    record.rank = 1

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "ERROR"
    assert data["message"] == "Failed to parse model configuration"
    assert data["run_id"] == "run-2026-abc"
    assert data["experiment"] == "exp-bert-lora"
    assert data["rank"] == 1

    # Kiểm tra object ai_error trích xuất từ AIEngineError
    assert "ai_error" in data
    ai_err = data["ai_error"]
    assert ai_err["code"] == "ERR_CFG_INVALID"
    assert ai_err["severity"] == "ERROR"
    assert ai_err["is_recoverable"] is False
    assert ai_err["suggestion"] == "Check hidden_dim in your config YAML"
    assert ai_err["details"]["dim"] == -1


def test_log_context_and_filter():
    LogContext.set(run_id="run-test-01", experiment="exp-test", rank=2)

    context_filter = LogContextFilter()
    record = logging.LogRecord(
        name="test_worker",
        level=logging.INFO,
        pathname="worker.py",
        lineno=12,
        msg="Processing batch",
        args=(),
        exc_info=None,
    )

    allowed = context_filter.filter(record)
    assert allowed is True
    assert getattr(record, "run_id") == "run-test-01"
    assert getattr(record, "experiment") == "exp-test"
    assert getattr(record, "rank") == 2

    # Clear context
    LogContext.clear()
    record2 = logging.LogRecord(
        name="test_worker",
        level=logging.INFO,
        pathname="worker.py",
        lineno=15,
        msg="Processing finished",
        args=(),
        exc_info=None,
    )
    context_filter.filter(record2)
    assert getattr(record2, "run_id", None) is None
    assert getattr(record2, "experiment", None) is None
    assert getattr(record2, "rank", None) is None


def test_timed_rotating_file_handler(tmp_path):
    timed_file = tmp_path / "timed" / "server.log"
    handler = create_timed_rotating_file_handler(
        filepath=str(timed_file),
        when="midnight",
        interval=1,
        backup_count=7,
        level="DEBUG",
    )
    assert handler.level == logging.DEBUG
    assert timed_file.parent.exists()
    handler.close()
