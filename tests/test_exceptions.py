import json

import pytest

from src.core.exceptions import (
    AIEngineError,
    CheckpointError,
    CheckpointNotFoundError,
    ConfigFileNotFoundError,
    ConfigurationError,
    CudaUnavailableError,
    DiagnosticError,
    ErrorCode,
    ErrorSeverity,
    GenerationError,
    HardwareError,
    ProtocolError,
    SamplingError,
    SignatureMismatchError,
    TrainingDivergedError,
    VRAMBudgetExceededError,
)


def test_base_ai_engine_error_structure():
    err = AIEngineError(
        message="Lỗi thử nghiệm",
        details={"key": "val"},
        error_code=ErrorCode.UNKNOWN_ERROR,
        suggestion="Thử lại sau",
        severity=ErrorSeverity.CRITICAL,
        is_recoverable=True,
    )
    assert err.error_code == ErrorCode.UNKNOWN_ERROR
    assert err.severity == ErrorSeverity.CRITICAL
    assert err.is_recoverable is True
    assert err.details["key"] == "val"
    assert "Lỗi thử nghiệm" in str(err)
    assert "[ERR_UNKNOWN]" in str(err)
    assert "[CRITICAL]" in str(err)
    assert "💡 [Gợi ý khắc phục]: Thử lại sau" in str(err)
    assert "Recoverable" in str(err)
    assert hasattr(err, "timestamp") and len(err.timestamp) > 0

    data = err.to_dict()
    assert data["error_code"] == "ERR_UNKNOWN"
    assert data["error_type"] == "AIEngineError"
    assert data["severity"] == "CRITICAL"
    assert data["is_recoverable"] is True
    assert data["timestamp"] == err.timestamp

    # Test serialization JSON
    json_str = err.to_json()
    parsed = json.loads(json_str)
    assert parsed["error_code"] == "ERR_UNKNOWN"
    assert parsed["is_recoverable"] is True


def test_exception_chaining_and_cause():
    orig_exc = ValueError("Lỗi gốc giá trị không hợp lệ")
    err = AIEngineError(
        message="Lỗi tầng cao",
        cause=orig_exc,
    )
    assert err.cause is orig_exc
    assert err.__cause__ is orig_exc
    assert "ValueError" in str(err)
    assert "Lỗi gốc giá trị không hợp lệ" in str(err)
    assert err.to_dict()["cause"] is not None


def test_config_file_not_found_error():
    err = ConfigFileNotFoundError("invalid/path/config.yaml")
    assert isinstance(err, ConfigurationError)
    assert isinstance(err, AIEngineError)
    assert err.error_code == ErrorCode.CONFIG_NOT_FOUND
    assert "invalid/path/config.yaml" in str(err)


def test_hardware_cuda_unavailable_error():
    err = CudaUnavailableError()
    assert isinstance(err, HardwareError)
    assert err.error_code == ErrorCode.HARDWARE_CUDA_UNAVAILABLE
    assert err.suggestion is not None and "device: cpu" in err.suggestion


def test_training_diverged_error():
    err = TrainingDivergedError(details={"step": 500, "loss": "nan"})
    assert isinstance(err, AIEngineError)
    assert err.error_code == ErrorCode.TRAINING_LOSS_NAN
    assert err.details["loss"] == "nan"


def test_checkpoint_not_found_error():
    err = CheckpointNotFoundError("checkpoints/missing.pt")
    assert isinstance(err, CheckpointError)
    assert err.error_code == ErrorCode.CHECKPOINT_NOT_FOUND


def test_generation_exceptions():
    err = GenerationError("Lỗi sinh chuỗi")
    assert isinstance(err, AIEngineError)
    assert err.error_code == ErrorCode.GEN_SAMPLING_FAILED

    sample_err = SamplingError("Logits có NaN")
    assert isinstance(sample_err, GenerationError)
    assert sample_err.is_recoverable is True


def test_protocols_exceptions():
    proto_err = ProtocolError(
        message="Class không tuân thủ giao thức",
        details={"missing": ["forward"]},
    )
    assert isinstance(proto_err, AIEngineError)
    assert isinstance(proto_err, TypeError)
    assert proto_err.error_code == ErrorCode.PROTO_VIOLATION

    # Kiểm tra tính tương thích: try...except TypeError bắt được ProtocolError
    with pytest.raises(TypeError):
        raise proto_err

    # Kiểm tra tính tương thích: try...except AIEngineError bắt được ProtocolError
    with pytest.raises(AIEngineError):
        raise proto_err

    sig_err = SignatureMismatchError("forward", "thiếu tham số idx")
    assert isinstance(sig_err, ProtocolError)
    assert isinstance(sig_err, TypeError)
    assert sig_err.error_code == ErrorCode.PROTO_SIGNATURE_MISMATCH
    assert sig_err.details["method_name"] == "forward"


def test_diagnostics_exceptions():
    diag_err = DiagnosticError("Môi trường lỗi")
    assert isinstance(diag_err, AIEngineError)
    assert diag_err.error_code == ErrorCode.DIAG_HEALTH_FAILED

    vram_err = VRAMBudgetExceededError(required_vram_gb=12.5, available_vram_gb=8.0)
    assert isinstance(vram_err, DiagnosticError)
    assert vram_err.error_code == ErrorCode.DIAG_VRAM_OVERFLOW
    assert vram_err.is_recoverable is True
    assert vram_err.severity == ErrorSeverity.WARNING
    assert "12.50 GB" in str(vram_err)
    assert "8.00 GB" in str(vram_err)


def test_unknown_generator_has_stable_typed_error_code():
    from src.core.exceptions import GeneratorBackendNotFoundError

    error = GeneratorBackendNotFoundError("missing", ["local"])

    assert str(error.error_code) == "ERR_GEN_BACKEND_NOT_FOUND"
    assert error.details == {"requested": "missing", "available": ["local"]}
