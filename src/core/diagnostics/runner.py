"""
Trình điều phối Kiểm tra Hệ thống (System Health Diagnostics Runner):
- Tổng hợp toàn bộ các kết quả thăm dò từ System, Hardware, Storage và Permissions
- Phân loại trạng thái hệ thống: HEALTHY, WARNING, CRITICAL
- Đưa ra danh sách cảnh báo và khuyến nghị xử lý tức thì (Actionable Suggestions)
- Duy trì hàm tương thích ngược check_hardware_and_environment()
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from src.core.diagnostics.hardware import (
    get_cpu_info,
    get_gpu_info,
    get_memory_info,
    probe_cuda_device,
)
from src.core.diagnostics.storage import get_disk_info, verify_directory_permissions
from src.core.diagnostics.system import get_system_info
from src.core.logging import get_logger

logger = get_logger("Diagnostics")


class DiagnosticStatus(str, Enum):
    """Trạng thái sức khỏe của môi trường hệ thống."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class DiagnosticReport:
    """Báo cáo chi tiết kết quả chẩn đoán hệ thống."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: DiagnosticStatus = DiagnosticStatus.HEALTHY
    system: Dict[str, Any] = field(default_factory=dict)
    hardware: Dict[str, Any] = field(default_factory=dict)
    storage: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    recommendations: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành từ điển có thể tuần tự hóa JSON."""
        data = asdict(self)
        data["status"] = self.status.value
        return data


class DiagnosticsRunner:
    """Thực thi toàn diện các bài kiểm tra sức khỏe của ứng dụng."""

    def __init__(self):
        self.logger = logger

    def run(self, test_tensor_allocation: bool = True) -> DiagnosticReport:
        """Thu thập dữ liệu và phân tích mức độ an toàn của môi trường."""
        system_info = get_system_info()
        cpu_info = get_cpu_info()
        memory_info = get_memory_info()
        gpu_info = get_gpu_info()
        disk_info = get_disk_info(".")
        perm_info = verify_directory_permissions(("logs", "checkpoints", "data", "configs"))

        warnings: List[str] = []
        suggestions: List[str] = []
        status = DiagnosticStatus.HEALTHY

        # 1. Đánh giá ổ đĩa
        free_disk = disk_info.get("free_gb", 0.0)
        if free_disk < 1.0:
            status = DiagnosticStatus.CRITICAL
            warnings.append(
                f"Dung lượng đĩa trống cực thấp ({free_disk} GB)! Huấn luyện có thể bị crash."
            )
            suggestions.append(
                "Giải phóng dung lượng ổ đĩa ngay để tránh lỗi ghi checkpoint hoặc log."
            )
        elif free_disk < 5.0:
            if status != DiagnosticStatus.CRITICAL:
                status = DiagnosticStatus.WARNING
            warnings.append(f"Dung lượng đĩa khả dụng dưới 5GB ({free_disk} GB).")
            suggestions.append("Nên dọn dẹp các checkpoint cũ không cần thiết.")

        # 2. Đánh giá quyền thư mục
        for directory, perms in perm_info.items():
            if not perms.get("writable", False):
                status = DiagnosticStatus.CRITICAL
                warnings.append(f"Không có quyền ghi vào thư mục '{directory}'!")
                suggestions.append(f"Cấp quyền ghi (write permission) cho thư mục '{directory}'.")

        # 3. Đánh giá GPU & CUDA
        if not gpu_info.get("cuda_available", False):
            if status != DiagnosticStatus.CRITICAL:
                status = DiagnosticStatus.WARNING
            warnings.append(
                "Không phát hiện GPU CUDA. Quá trình huấn luyện/suy luận sẽ chạy trên CPU."
            )
            suggestions.append(
                "Nếu bạn có GPU NVIDIA, hãy kiểm tra driver và cài đặt bản PyTorch có CUDA."
            )
        else:
            primary_gpu = gpu_info.get("primary_gpu")
            if primary_gpu:
                free_vram = primary_gpu.get("vram_free_gb", 0.0)
                if free_vram < 1.0:
                    if status != DiagnosticStatus.CRITICAL:
                        status = DiagnosticStatus.WARNING
                    warnings.append(f"VRAM khả dụng rất thấp ({free_vram} GB).")
                    suggestions.append("Đóng các ứng dụng đồ họa khác hoặc giảm batch_size.")

            # Test tensor allocation
            if test_tensor_allocation and gpu_info.get("device_count", 0) > 0:
                success, msg = probe_cuda_device(0)
                if not success:
                    status = DiagnosticStatus.CRITICAL
                    warnings.append(f"GPU Probe thất bại: {msg}")
                    suggestions.append("Khởi động lại driver CUDA hoặc kiểm tra card đồ họa.")

        # 4. Đánh giá RAM
        free_ram = memory_info.get("available_gb", 0.0)
        if free_ram > 0 and free_ram < 1.0:
            if status != DiagnosticStatus.CRITICAL:
                status = DiagnosticStatus.WARNING
            warnings.append(f"RAM hệ thống khả dụng dưới 1GB ({free_ram} GB).")
            suggestions.append("Giải phóng bớt bộ nhớ RAM máy tính.")

        # 5. Khuyến nghị phần cứng
        recommendations = gpu_info.get("recommendations", {})
        if recommendations.get("gradient_checkpointing"):
            suggestions.append(
                "Khuyến nghị bật 'gradient_checkpointing' để giảm 70% bộ nhớ activation khi huấn luyện."
            )
        rec_prec = recommendations.get("recommended_precision")
        if rec_prec and rec_prec != "float32":
            suggestions.append(
                f"Phần cứng tối ưu cho chế độ Mixed Precision '{rec_prec}' (tăng tốc huấn luyện)."
            )

        report = DiagnosticReport(
            status=status,
            system=system_info,
            hardware={
                "cpu": cpu_info,
                "memory": memory_info,
                "gpu": gpu_info,
            },
            storage=disk_info,
            permissions=perm_info,
            recommendations=recommendations,
            warnings=warnings,
            suggestions=suggestions,
        )

        return report


def check_hardware_and_environment() -> Dict[str, Any]:
    """Hàm tương thích ngược với API diagnostics cũ."""
    runner = DiagnosticsRunner()
    report = runner.run(test_tensor_allocation=True)

    primary_gpu = report.hardware["gpu"].get("primary_gpu")
    status_str = "PASS"
    if report.status == DiagnosticStatus.WARNING:
        status_str = "WARN"
    elif report.status == DiagnosticStatus.CRITICAL:
        status_str = "FAIL"

    return {
        "os": report.system.get("os_platform"),
        "python_version": report.system.get("python_version"),
        "pytorch_version": report.system.get("pytorch_version"),
        "cuda_available": report.hardware["gpu"].get("cuda_available", False),
        "gpu_count": report.hardware["gpu"].get("device_count", 0),
        "gpu_name": primary_gpu.get("name") if primary_gpu else None,
        "vram_total_gb": primary_gpu.get("vram_total_gb", 0.0) if primary_gpu else 0.0,
        "vram_free_gb": primary_gpu.get("vram_free_gb", 0.0) if primary_gpu else 0.0,
        "disk_free_gb": report.storage.get("free_gb", 0.0),
        "status": status_str,
    }
