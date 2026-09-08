"""
Bộ thu thập thông tin Môi trường & Hệ điều hành (System & Software Inspector):
- Hệ điều hành, kiến trúc máy chủ, phiên bản Python và runtime
- Phiên bản PyTorch, CUDA runtime và cuDNN
- Phiên bản các thư viện lõi (Rich, PyYAML, psutil, pytest)
- Các biến môi trường huấn luyện quan trọng
"""

import importlib
import os
import platform
import sys
from typing import Any, Dict

import torch


def get_installed_package_version(pkg_name: str) -> str:
    """Lấy phiên bản của một thư viện đã cài đặt, trả về 'N/A' nếu không có."""
    try:
        mod = importlib.import_module(pkg_name)
        return getattr(mod, "__version__", "Đã cài đặt")
    except ImportError:
        return "Chưa cài đặt"


def get_system_info() -> Dict[str, Any]:
    """Thu thập thông tin toàn diện về hệ điều hành, Python và runtime PyTorch/CUDA."""
    cudnn_ver = "N/A"
    try:
        if torch.backends.cudnn.is_available():
            raw_ver = torch.backends.cudnn.version()
            cudnn_ver = str(raw_ver) if raw_ver is not None else "Khả dụng"
    except Exception:
        pass

    env_vars = {
        "PYTHONIOENCODING": os.environ.get("PYTHONIOENCODING", "Chưa đặt"),
        "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", "Tất cả"),
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "Mặc định"),
    }

    core_packages = {
        "torch": torch.__version__,
        "rich": get_installed_package_version("rich"),
        "yaml": get_installed_package_version("yaml"),
        "psutil": get_installed_package_version("psutil"),
        "pytest": get_installed_package_version("pytest"),
    }

    return {
        "os_platform": platform.platform(),
        "os_system": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "pytorch_version": torch.__version__,
        "cuda_runtime_version": getattr(getattr(torch, "version", None), "cuda", None) or "N/A",
        "cudnn_version": cudnn_ver,
        "packages": core_packages,
        "environment_variables": env_vars,
    }
