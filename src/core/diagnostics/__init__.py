"""
Hệ thống Diagnostics & Health Check chuẩn Modular Monolith:
- system: Giám sát môi trường phần mềm & runtime PyTorch / CUDA
- hardware: Giám sát thiết bị CPU, RAM và GPU
- storage: Kiểm toán dung lượng đĩa và phân quyền truy cập
- estimator: Ước tính ngân sách bộ nhớ VRAM cho Transformer
- runner: Điều phối thăm dò và phân loại trạng thái sức khỏe
- reporter: Kết xuất giao diện báo cáo Rich / JSON
"""

from src.core.diagnostics.estimator import (
    analyze_vram_scenarios,
    calculate_approx_transformer_params,
    check_memory_feasibility,
    estimate_vram_budget,
)
from src.core.diagnostics.hardware import (
    check_attention_backends,
    check_bf16_support,
    get_cpu_info,
    get_gpu_info,
    get_hardware_recommendations,
    get_memory_info,
    probe_cuda_device,
)
from src.core.diagnostics.reporter import (
    export_diagnostic_json,
    print_diagnostic_report,
    print_vram_scenarios_table,
)
from src.core.diagnostics.runner import (
    DiagnosticReport,
    DiagnosticsRunner,
    DiagnosticStatus,
    check_hardware_and_environment,
)
from src.core.diagnostics.storage import (
    get_disk_info,
    verify_directories,
    verify_directory_permissions,
)
from src.core.diagnostics.system import get_system_info

__all__ = [
    "get_system_info",
    "get_cpu_info",
    "get_memory_info",
    "get_gpu_info",
    "check_bf16_support",
    "check_attention_backends",
    "get_hardware_recommendations",
    "probe_cuda_device",
    "get_disk_info",
    "verify_directory_permissions",
    "verify_directories",
    "calculate_approx_transformer_params",
    "estimate_vram_budget",
    "check_memory_feasibility",
    "analyze_vram_scenarios",
    "DiagnosticStatus",
    "DiagnosticReport",
    "DiagnosticsRunner",
    "check_hardware_and_environment",
    "print_diagnostic_report",
    "print_vram_scenarios_table",
    "export_diagnostic_json",
]
