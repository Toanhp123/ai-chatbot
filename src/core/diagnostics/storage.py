"""
Kiểm toán Bộ nhớ & Phân quyền Lưu trữ (Storage & Permission Auditor):
- Quét dung lượng đĩa trống tại thư mục làm việc
- Kiểm tra quyền truy cập I/O (Read, Write, Delete) trên các thư mục trọng yếu
- Đảm bảo an toàn không bị gián đoạn giữa chừng do thiếu dung lượng hoặc lỗi cấp quyền
"""

import os
import shutil
from typing import Any, Dict, Sequence

from src.core.exceptions import HardwareError


def get_disk_info(path: str = ".") -> Dict[str, Any]:
    """Kiểm tra thông số dung lượng lưu trữ của ổ đĩa chứa đường dẫn path."""
    try:
        total, used, free = shutil.disk_usage(path)
        total_gb = round(total / (1024**3), 2)
        used_gb = round(used / (1024**3), 2)
        free_gb = round(free / (1024**3), 2)
        percent_used = round((used / total) * 100, 1) if total > 0 else 0.0
    except Exception:
        total_gb, used_gb, free_gb, percent_used = 0.0, 0.0, 0.0, 0.0

    return {
        "path": os.path.abspath(path),
        "total_gb": total_gb,
        "used_gb": used_gb,
        "free_gb": free_gb,
        "percent_used": percent_used,
    }


def verify_directory_permissions(
    paths: Sequence[str] = ("logs", "checkpoints", "data", "configs"),
) -> Dict[str, Dict[str, bool]]:
    """Kiểm tra quyền truy cập chi tiết (Read, Write, Delete) cho danh sách thư mục."""
    results: Dict[str, Dict[str, bool]] = {}

    for d in paths:
        status = {"exists": False, "readable": False, "writable": False}
        try:
            os.makedirs(d, exist_ok=True)
            status["exists"] = os.path.isdir(d)

            # Test Read
            _ = os.listdir(d)
            status["readable"] = True

            # Test Write & Delete
            test_file = os.path.join(d, ".perm_test")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("healthcheck")
            os.remove(test_file)
            status["writable"] = True
        except Exception:
            pass

        results[d] = status

    return results


def verify_directories(required_dirs: Sequence[str] = ("logs", "checkpoints", "data")) -> bool:
    """Hàm tương thích ngược: đảm bảo các thư mục bắt buộc tồn tại và có quyền ghi.

    Ném HardwareError nếu không thể ghi vào thư mục.
    """
    for d in required_dirs:
        try:
            os.makedirs(d, exist_ok=True)
            test_file = os.path.join(d, ".perm_test")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test_file)
        except Exception as e:
            raise HardwareError(
                f"Không có quyền ghi vào thư mục bắt buộc '{d}': {e}",
                details={"directory": d, "error": str(e)},
                suggestion=f"Hãy cấp quyền ghi cho thư mục '{d}' hoặc chạy ứng dụng với quyền phù hợp.",
            )
    return True
