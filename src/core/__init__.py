"""Public core API with lazy exports.

Keeping this package initializer side-effect free is intentional: importing a
lightweight value object such as ``src.core.config.ModelConfig`` must not load
Torch/Rich or configure filesystem-backed logging.
"""

from importlib import import_module
from typing import Dict, Tuple

_EXPORTS: Dict[str, Tuple[str, str]] = {
    # Exceptions & codes
    "ErrorCode": ("src.core.exceptions", "ErrorCode"),
    "ErrorSeverity": ("src.core.exceptions", "ErrorSeverity"),
    "AIEngineError": ("src.core.exceptions", "AIEngineError"),
    "ConfigurationError": ("src.core.exceptions", "ConfigurationError"),
    "ConfigFileNotFoundError": ("src.core.exceptions", "ConfigFileNotFoundError"),
    "ConfigValidationError": ("src.core.exceptions", "ConfigValidationError"),
    "HardwareError": ("src.core.exceptions", "HardwareError"),
    "CudaUnavailableError": ("src.core.exceptions", "CudaUnavailableError"),
    "OutOfMemoryError": ("src.core.exceptions", "OutOfMemoryError"),
    "DataPipelineError": ("src.core.exceptions", "DataPipelineError"),
    "VocabularyMissingError": ("src.core.exceptions", "VocabularyMissingError"),
    "DatasetEmptyError": ("src.core.exceptions", "DatasetEmptyError"),
    "ModelArchitectureError": ("src.core.exceptions", "ModelArchitectureError"),
    "ModelNotFoundError": ("src.core.exceptions", "ModelNotFoundError"),
    "ContextLengthExceededError": ("src.core.exceptions", "ContextLengthExceededError"),
    "TrainingError": ("src.core.exceptions", "TrainingError"),
    "TrainingDivergedError": ("src.core.exceptions", "TrainingDivergedError"),
    "CheckpointError": ("src.core.exceptions", "CheckpointError"),
    "CheckpointNotFoundError": ("src.core.exceptions", "CheckpointNotFoundError"),
    "CheckpointCorruptedError": ("src.core.exceptions", "CheckpointCorruptedError"),
    "GenerationError": ("src.core.exceptions", "GenerationError"),
    "GeneratorBackendNotFoundError": ("src.core.exceptions", "GeneratorBackendNotFoundError"),
    "SamplingError": ("src.core.exceptions", "SamplingError"),
    "DiagnosticError": ("src.core.exceptions", "DiagnosticError"),
    "VRAMBudgetExceededError": ("src.core.exceptions", "VRAMBudgetExceededError"),
    "ProtocolError": ("src.core.exceptions", "ProtocolError"),
    "ProtocolViolationError": ("src.core.exceptions", "ProtocolViolationError"),
    "SignatureMismatchError": ("src.core.exceptions", "SignatureMismatchError"),
    # Config
    "BaseConfig": ("src.core.config", "BaseConfig"),
    "EngineConfig": ("src.core.config", "EngineConfig"),
    "SystemConfig": ("src.core.config", "SystemConfig"),
    "DataConfig": ("src.core.config", "DataConfig"),
    "ModelConfig": ("src.core.config", "ModelConfig"),
    "TrainingConfig": ("src.core.config", "TrainingConfig"),
    "GenerationConfig": ("src.core.config", "GenerationConfig"),
    # Logging
    "setup_logger": ("src.core.logging", "setup_logger"),
    "get_logger": ("src.core.logging", "get_logger"),
    "get_metric_logger": ("src.core.logging", "get_metric_logger"),
    "LogContext": ("src.core.logging", "LogContext"),
    "MetricLogger": ("src.core.logging", "MetricLogger"),
    # Diagnostics
    "check_hardware_and_environment": (
        "src.core.diagnostics",
        "check_hardware_and_environment",
    ),
    "print_diagnostic_report": ("src.core.diagnostics", "print_diagnostic_report"),
    "estimate_vram_budget": ("src.core.diagnostics", "estimate_vram_budget"),
    "DiagnosticsRunner": ("src.core.diagnostics", "DiagnosticsRunner"),
}

__all__ = [
    "ErrorCode",
    "ErrorSeverity",
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
    "BaseConfig",
    "EngineConfig",
    "SystemConfig",
    "DataConfig",
    "ModelConfig",
    "TrainingConfig",
    "GenerationConfig",
    "setup_logger",
    "get_logger",
    "get_metric_logger",
    "LogContext",
    "MetricLogger",
    "check_hardware_and_environment",
    "print_diagnostic_report",
    "estimate_vram_budget",
    "DiagnosticsRunner",
]


def __getattr__(name: str):
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_EXPORTS))
