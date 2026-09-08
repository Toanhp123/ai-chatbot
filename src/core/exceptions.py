"""
Module quản lý ngoại lệ tập trung (Centralized Exceptions) cho AI Engine.
Bao gồm ErrorCode, ErrorSeverity và tất cả Exception classes chuẩn hóa.
"""

import datetime
import json
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorSeverity(str, Enum):
    """Mức độ nghiêm trọng của ngoại lệ trong hệ thống."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"

    def __str__(self) -> str:
        return self.value


class ErrorCode(str, Enum):
    # Lỗi chung
    UNKNOWN_ERROR = "ERR_UNKNOWN"

    # Lỗi cấu hình (Config)
    CONFIG_INVALID = "ERR_CFG_INVALID"
    CONFIG_NOT_FOUND = "ERR_CFG_NOT_FOUND"

    # Lỗi phần cứng (Hardware / CUDA)
    HARDWARE_CUDA_UNAVAILABLE = "ERR_HW_CUDA_UNAVAILABLE"
    HARDWARE_OOM = "ERR_HW_OOM"
    HARDWARE_PERMISSION = "ERR_HW_PERMISSION"

    # Lỗi đường ống dữ liệu (Data Pipeline)
    DATA_FILE_NOT_FOUND = "ERR_DAT_FILE_NOT_FOUND"
    DATA_VOCAB_EMPTY = "ERR_DAT_VOCAB_EMPTY"
    DATA_CORPUS_EMPTY = "ERR_DAT_CORPUS_EMPTY"

    # Lỗi kiến trúc mô hình (Model Architecture)
    MODEL_NOT_FOUND = "ERR_MOD_NOT_FOUND"
    MODEL_SHAPE_MISMATCH = "ERR_MOD_SHAPE_MISMATCH"
    MODEL_CONTEXT_EXCEEDED = "ERR_MOD_CONTEXT_EXCEEDED"

    # Lỗi trong quá trình huấn luyện (Training)
    TRAINING_DIVERGED = "ERR_TRN_DIVERGED"
    TRAINING_LOSS_NAN = "ERR_TRN_LOSS_NAN"
    TRAINING_GRAD_INF = "ERR_TRN_GRAD_INF"

    # Lỗi checkpoint
    CHECKPOINT_NOT_FOUND = "ERR_CKP_NOT_FOUND"
    CHECKPOINT_CORRUPTED = "ERR_CKP_CORRUPTED"

    # Lỗi sinh văn bản (Generation)
    GEN_SAMPLING_FAILED = "ERR_GEN_SAMPLING_FAILED"
    GEN_BACKEND_NOT_FOUND = "ERR_GEN_BACKEND_NOT_FOUND"
    GEN_EMPTY_PROMPT = "ERR_GEN_EMPTY_PROMPT"
    GEN_CONTEXT_EXCEEDED = "ERR_GEN_CONTEXT_EXCEEDED"

    # Lỗi tương thích giao thức (Protocols)
    PROTO_VIOLATION = "ERR_PROTO_VIOLATION"
    PROTO_SIGNATURE_MISMATCH = "ERR_PROTO_SIGNATURE_MISMATCH"

    # Lỗi kiểm định hệ thống (Diagnostics)
    DIAG_HEALTH_FAILED = "ERR_DIAG_HEALTH_FAILED"
    DIAG_VRAM_OVERFLOW = "ERR_DIAG_VRAM_OVERFLOW"

    def __str__(self) -> str:
        return self.value


class AIEngineError(Exception):
    """Ngoại lệ cơ sở cho toàn bộ lỗi trong hệ thống AI Engine."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        suggestion: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        is_recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        self.suggestion = suggestion
        self.severity = severity
        self.is_recoverable = is_recoverable
        self.cause = cause
        self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if cause is not None:
            self.__cause__ = cause

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thông tin ngoại lệ thành dictionary cấu trúc để ghi log."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": str(self.error_code),
            "message": self.message,
            "severity": str(self.severity),
            "is_recoverable": self.is_recoverable,
            "timestamp": self.timestamp,
            "details": self.details,
            "suggestion": self.suggestion,
            "cause": str(self.cause) if self.cause else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """Chuyển đổi thông tin ngoại lệ thành chuỗi JSON chuẩn hóa."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def __str__(self) -> str:
        parts = [f"[{self.error_code.value}] [{self.severity.value}] {self.message}"]
        if self.is_recoverable:
            parts.append("(Khả năng phục hồi: Có thể thử lại / Recoverable)")
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            parts.append(f"(Ngữ cảnh: {details_str})")
        if self.cause:
            parts.append(f"(Nguyên nhân gốc: {type(self.cause).__name__}: {self.cause})")
        if self.suggestion:
            parts.append(f"💡 [Gợi ý khắc phục]: {self.suggestion}")
        return " ".join(parts)


# --- Configuration Exceptions ---
class ConfigurationError(AIEngineError):
    """Ngoại lệ chung cho các sai sót trong cấu hình."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.CONFIG_INVALID,
        suggestion: Optional[str] = "Hãy kiểm tra lại file cấu hình YAML hoặc tham số dòng lệnh.",
    ):
        super().__init__(
            message=message, details=details, error_code=error_code, suggestion=suggestion
        )


class ConfigFileNotFoundError(ConfigurationError):
    """Ngoại lệ khi không tìm thấy file cấu hình chỉ định."""

    def __init__(self, filepath: str):
        super().__init__(
            message=f"Không tìm thấy file cấu hình tại đường dẫn: '{filepath}'",
            details={"filepath": filepath},
            error_code=ErrorCode.CONFIG_NOT_FOUND,
            suggestion="Kiểm tra lại đường dẫn file hoặc truyền đường dẫn chính xác qua cờ --config.",
        )


class ConfigValidationError(ConfigurationError):
    """Ngoại lệ khi giá trị tham số cấu hình vi phạm các ràng buộc logic."""

    pass


# --- Hardware Exceptions ---
class HardwareError(AIEngineError):
    """Ngoại lệ chung cho các lỗi phần cứng, driver CUDA, quyền ổ đĩa."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.HARDWARE_PERMISSION,
        suggestion: Optional[str] = "Kiểm tra quyền truy cập ổ đĩa hoặc tình trạng card đồ họa.",
    ):
        super().__init__(
            message=message, details=details, error_code=error_code, suggestion=suggestion
        )


class CudaUnavailableError(HardwareError):
    """Ngoại lệ khi yêu cầu thiết bị CUDA nhưng hệ thống không tìm thấy GPU hoặc Driver CUDA."""

    def __init__(self, message: str = "Không tìm thấy GPU hoặc CUDA Driver chưa được cài đặt!"):
        super().__init__(
            message=message,
            error_code=ErrorCode.HARDWARE_CUDA_UNAVAILABLE,
            suggestion="Cài đặt PyTorch với phiên bản CUDA phù hợp hoặc chuyển sang 'device: cpu' trong cấu hình.",
        )


class OutOfMemoryError(HardwareError):
    """Ngoại lệ khi GPU bị tràn bộ nhớ VRAM."""

    def __init__(self, message: str = "GPU hết bộ nhớ VRAM khả dụng (CUDA Out of Memory)!"):
        super().__init__(
            message=message,
            error_code=ErrorCode.HARDWARE_OOM,
            suggestion="Hãy giảm 'batch_size', giảm 'block_size' hoặc bật 'mixed_precision' để tiết kiệm VRAM.",
        )


# --- Data Pipeline Exceptions ---
class DataPipelineError(AIEngineError):
    """Ngoại lệ chung cho các lỗi đọc, làm sạch, tokenization hoặc batching dữ liệu."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.DATA_FILE_NOT_FOUND,
        suggestion: Optional[str] = "Kiểm tra lại file dữ liệu hoặc kết nối mạng để tải corpus.",
    ):
        super().__init__(
            message=message, details=details, error_code=error_code, suggestion=suggestion
        )


class VocabularyMissingError(DataPipelineError):
    """Ngoại lệ khi không tìm thấy file từ điển từ vựng (vocab.json)."""

    def __init__(self, vocab_path: str):
        super().__init__(
            message=f"Không tìm thấy file từ điển tại: '{vocab_path}'",
            details={"vocab_path": vocab_path},
            error_code=ErrorCode.DATA_VOCAB_EMPTY,
            suggestion="Chạy lại script huấn luyện hoặc DataPipeline để tự động sinh file vocab.json.",
        )


class DatasetEmptyError(DataPipelineError):
    """Ngoại lệ khi file dữ liệu huấn luyện rỗng hoặc có độ dài không đủ."""

    def __init__(
        self, message: str = "Tập dữ liệu huấn luyện rỗng hoặc quá ngắn so với block_size!"
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_CORPUS_EMPTY,
            suggestion="Cung cấp file dữ liệu văn bản có độ dài tối thiểu lớn hơn độ dài ngữ cảnh block_size.",
        )


# --- Model Architecture Exceptions ---
class ModelArchitectureError(AIEngineError):
    """Ngoại lệ chung cho các lỗi kiến trúc mô hình, shape tensor hoặc tính toán forward."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.MODEL_SHAPE_MISMATCH,
        suggestion: Optional[
            str
        ] = "Kiểm tra lại cấu hình số lớp, số heads và kích thước embedding.",
    ):
        super().__init__(
            message=message, details=details, error_code=error_code, suggestion=suggestion
        )


class ModelNotFoundError(ModelArchitectureError):
    """Ngoại lệ khi yêu cầu một mô hình chưa được đăng ký trong ModelRegistry."""

    def __init__(self, model_name: str, available_models: Optional[List[str]] = None):
        avail_str = ", ".join(available_models) if available_models else "chưa có"
        super().__init__(
            message=f"Không tìm thấy mô hình '{model_name}' trong Registry! (Mô hình khả dụng: [{avail_str}])",
            details={"requested": model_name, "available": available_models or []},
            error_code=ErrorCode.MODEL_NOT_FOUND,
            suggestion="Kiểm tra lại tên mô hình trong file config YAML hoặc đăng ký bằng @ModelRegistry.register.",
        )


class ContextLengthExceededError(ModelArchitectureError):
    """Ngoại lệ khi chuỗi token đầu vào vượt quá độ dài ngữ cảnh tối đa block_size."""

    def __init__(self, seq_len: int, max_block_size: int):
        super().__init__(
            message=f"Độ dài chuỗi đầu vào ({seq_len}) vượt quá giới hạn ngữ cảnh của mô hình ({max_block_size})!",
            details={"seq_len": seq_len, "max_block_size": max_block_size},
            error_code=ErrorCode.MODEL_CONTEXT_EXCEEDED,
            suggestion="Cắt ngắn bớt chuỗi đầu vào hoặc tăng block_size khi huấn luyện mô hình.",
        )


# --- Training Exceptions ---
class TrainingError(AIEngineError):
    """Ngoại lệ chung cho quy trình huấn luyện."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.TRAINING_DIVERGED,
        suggestion: Optional[str] = "Kiểm tra lại quá trình huấn luyện và siêu tham số.",
    ):
        super().__init__(
            message=message, details=details, error_code=error_code, suggestion=suggestion
        )


class TrainingDivergedError(TrainingError):
    """Ngoại lệ khi quá trình huấn luyện bị phân kỳ (Loss hoặc Gradient = NaN / Inf)."""

    def __init__(
        self,
        message: str = "Quá trình huấn luyện bị phân kỳ: Phát hiện NaN hoặc Inf trong Loss hoặc Gradient!",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            details=details,
            error_code=ErrorCode.TRAINING_LOSS_NAN,
            suggestion="Hãy hạ thấp learning_rate, tăng số bước warmup_iters, hoặc bật gradient clipping (grad_clip).",
        )


# --- Checkpoint Exceptions ---
class CheckpointError(AIEngineError):
    """Ngoại lệ chung cho các lỗi khi lưu hoặc nạp file checkpoint mô hình."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.CHECKPOINT_CORRUPTED,
        suggestion: Optional[
            str
        ] = "Kiểm tra lại đường dẫn checkpoint hoặc tính toàn vẹn của file.",
    ):
        super().__init__(
            message=message, details=details, error_code=error_code, suggestion=suggestion
        )


class CheckpointNotFoundError(CheckpointError):
    """Ngoại lệ khi không tìm thấy file checkpoint chỉ định."""

    def __init__(self, checkpoint_path: str):
        super().__init__(
            message=f"Không tìm thấy file checkpoint tại: '{checkpoint_path}'",
            details={"checkpoint_path": checkpoint_path},
            error_code=ErrorCode.CHECKPOINT_NOT_FOUND,
            suggestion="Hãy chạy 'python main.py train' trước để tạo checkpoint hoặc chỉ định đúng đường dẫn.",
        )


class CheckpointCorruptedError(CheckpointError):
    """Ngoại lệ khi file checkpoint bị hỏng hoặc thiếu key bắt buộc."""

    def __init__(self, checkpoint_path: str, missing_keys: Optional[List[str]] = None):
        super().__init__(
            message=f"File checkpoint '{checkpoint_path}' bị lỗi hoặc thiếu các keys: {missing_keys}",
            details={"checkpoint_path": checkpoint_path, "missing_keys": missing_keys or []},
            error_code=ErrorCode.CHECKPOINT_CORRUPTED,
            suggestion="Checkpoint có thể được lưu chưa hoàn tất. Hãy thử sử dụng một checkpoint khác.",
        )


# --- Generation Exceptions ---
class GenerationError(AIEngineError):
    """Ngoại lệ chung cho các lỗi phát sinh trong quá trình suy luận sinh văn bản."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.GEN_SAMPLING_FAILED,
        suggestion: Optional[
            str
        ] = "Kiểm tra lại câu mồi prompt, nhiệt độ temperature hoặc cấu hình sampler.",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        is_recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            details=details,
            error_code=error_code,
            suggestion=suggestion,
            severity=severity,
            is_recoverable=is_recoverable,
            cause=cause,
        )


class GeneratorBackendNotFoundError(GenerationError):
    """Ngoại lệ khi client yêu cầu generator backend chưa đăng ký."""

    def __init__(self, backend: str, available: Optional[List[str]] = None):
        available_list = available or []
        super().__init__(
            message=(
                f"Không tìm thấy Generator '{backend}'. Các generator khả dụng: {available_list}"
            ),
            details={"requested": backend, "available": available_list},
            error_code=ErrorCode.GEN_BACKEND_NOT_FOUND,
            suggestion="Chọn một generator backend trong danh sách khả dụng.",
            is_recoverable=True,
        )


class SamplingError(GenerationError):
    """Ngoại lệ khi thuật toán lấy mẫu xác suất gặp lỗi (Logits chứa NaN, tổng xác suất bằng 0...)."""

    def __init__(
        self,
        message: str = "Lỗi trong quá trình lấy mẫu phân phối xác suất (Sampling)!",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            details=details,
            error_code=ErrorCode.GEN_SAMPLING_FAILED,
            suggestion="Hãy kiểm tra logits đầu ra của mô hình hoặc hạ thấp tham số temperature.",
            severity=ErrorSeverity.ERROR,
            is_recoverable=True,
            cause=cause,
        )


# --- Diagnostics Exceptions ---
class DiagnosticError(AIEngineError):
    """Ngoại lệ chung cho các lỗi phát sinh trong quá trình kiểm định hệ thống / phần cứng."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.DIAG_HEALTH_FAILED,
        suggestion: Optional[
            str
        ] = "Chạy 'python main.py check' để chẩn đoán chi tiết môi trường phần cứng.",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        is_recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            details=details,
            error_code=error_code,
            suggestion=suggestion,
            severity=severity,
            is_recoverable=is_recoverable,
            cause=cause,
        )


class VRAMBudgetExceededError(DiagnosticError):
    """Ngoại lệ khi ngân sách VRAM ước tính vượt quá dung lượng bộ nhớ khả dụng của GPU."""

    def __init__(
        self,
        required_vram_gb: float,
        available_vram_gb: float,
        scenario: str = "Baseline",
    ):
        super().__init__(
            message=(
                f"VRAM ước tính ({required_vram_gb:.2f} GB) vượt quá dung lượng "
                f"khả dụng của GPU ({available_vram_gb:.2f} GB) trong kịch bản '{scenario}'!"
            ),
            details={
                "required_vram_gb": required_vram_gb,
                "available_vram_gb": available_vram_gb,
                "scenario": scenario,
            },
            error_code=ErrorCode.DIAG_VRAM_OVERFLOW,
            suggestion=(
                "Hãy kích hoạt 'gradient_checkpointing: true', chuyển sang precision 'amp_fp16' / 'amp_bf16', "
                "hoặc giảm 'batch_size' trong file config."
            ),
            severity=ErrorSeverity.WARNING,
            is_recoverable=True,
        )


# --- Protocol Exceptions (Backward Compatibility) ---
class ProtocolError(AIEngineError, TypeError):
    """Ngoại lệ khi vi phạm hợp đồng interface / protocol."""

    def __init__(
        self,
        message: str = "Đối tượng không tuân thủ giao thức yêu cầu!",
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.PROTO_VIOLATION,
        suggestion: Optional[
            str
        ] = "Đảm bảo đối tượng cài đặt đầy đủ thuộc tính và phương thức theo quy ước.",
        severity: ErrorSeverity = ErrorSeverity.CRITICAL,
    ):
        super().__init__(
            message=message,
            details=details,
            error_code=error_code,
            suggestion=suggestion,
            severity=severity,
        )


class ProtocolViolationError(ProtocolError):
    """Ngoại lệ khi vi phạm thỏa ước giao thức."""

    def __init__(
        self,
        target_class: str,
        missing_attrs: List[str],
        protocol_name: str = "Protocol",
    ):
        super().__init__(
            message=(
                f"Lớp '{target_class}' vi phạm thỏa ước của giao thức '{protocol_name}'! "
                f"Các thuộc tính/phương thức còn thiếu: {missing_attrs}"
            ),
            details={
                "target_class": target_class,
                "missing_attributes": missing_attrs,
                "protocol": protocol_name,
            },
            error_code=ErrorCode.PROTO_VIOLATION,
            suggestion=f"Đảm bảo rằng '{target_class}' cài đặt đầy đủ tất cả phương thức quy định.",
            severity=ErrorSeverity.CRITICAL,
        )


class SignatureMismatchError(ProtocolError):
    """Ngoại lệ khi chữ ký phương thức không khớp."""

    def __init__(
        self,
        method_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        d = {"method_name": method_name, "reason": reason}
        if details:
            d.update(details)
        super().__init__(
            message=f"Chữ ký phương thức '{method_name}' không tương thích: {reason}",
            details=d,
            error_code=ErrorCode.PROTO_SIGNATURE_MISMATCH,
            suggestion="Hãy kiểm tra lại các tham số đầu vào và kiểu trả về của phương thức.",
        )


__all__ = [
    "ErrorSeverity",
    "ErrorCode",
    "AIEngineError",
    "ConfigurationError",
    "ConfigFileNotFoundError",
    "ConfigValidationError",
    "HardwareError",
    "CudaUnavailableError",
    "OutOfMemoryError",
    "DataPipelineError",
    "VocabularyMissingError",
    "DatasetEmptyError",
    "ModelArchitectureError",
    "ModelNotFoundError",
    "ContextLengthExceededError",
    "TrainingError",
    "TrainingDivergedError",
    "CheckpointError",
    "CheckpointNotFoundError",
    "CheckpointCorruptedError",
    "GenerationError",
    "GeneratorBackendNotFoundError",
    "SamplingError",
    "DiagnosticError",
    "VRAMBudgetExceededError",
    "ProtocolError",
    "ProtocolViolationError",
    "SignatureMismatchError",
]
