"""
Bộ dò và kiểm tra Phần cứng (Hardware & Device Prober):
- CPU: Số nhân vật lý, số luồng xử lý, mức tải
- RAM: Dung lượng tổng, khả dụng, phần trăm sử dụng
- GPU & CUDA: Kiểm tra card đồ họa, compute capability, VRAM tổng/trống, test cấp phát tensor
"""

import os
from typing import Any, Dict, List, Optional, Tuple

import torch

from src.core.diagnostics.probe import ProbeResult


def get_cpu_info() -> Dict[str, Any]:
    """Thu thập thông tin số nhân, luồng CPU và mức tải."""
    physical_cores = None
    logical_cores = os.cpu_count() or 1
    cpu_percent = None

    probe = ProbeResult.ok(True)
    try:
        import psutil

        physical_cores = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True) or logical_cores
        cpu_percent = psutil.cpu_percent(interval=0.1)
    except Exception as exc:
        probe = ProbeResult.failed(exc)

    return {
        "physical_cores": physical_cores or logical_cores,
        "logical_cores": logical_cores,
        "cpu_usage_percent": cpu_percent,
        "probe": probe.to_dict(),
    }


def get_memory_info() -> Dict[str, Any]:
    """Thu thập dung lượng RAM hệ thống."""
    total_gb = None
    available_gb = None
    used_gb = None
    percent = None
    probe = ProbeResult.ok(True)

    try:
        import psutil

        mem = psutil.virtual_memory()
        total_gb = round(mem.total / (1024**3), 2)
        available_gb = round(mem.available / (1024**3), 2)
        used_gb = round((mem.total - mem.available) / (1024**3), 2)
        percent = mem.percent
    except Exception as exc:
        probe = ProbeResult.failed(exc)

    return {
        "total_gb": total_gb,
        "available_gb": available_gb,
        "used_gb": used_gb,
        "percent_used": percent,
        "probe": probe.to_dict(),
    }


def check_bf16_support() -> bool:
    """Kiểm tra xem GPU và PyTorch có hỗ trợ kiểu dữ liệu bfloat16 hay không."""
    if not torch.cuda.is_available():
        return False
    try:
        is_supported = getattr(torch.cuda, "is_bf16_supported", None)
        if callable(is_supported):
            return bool(is_supported())
        major, _ = torch.cuda.get_device_capability(0)
        return major >= 8
    except Exception:
        return False


def check_attention_backends() -> Dict[str, Any]:
    """Kiểm tra tính khả dụng của 3 nhân Attention trong PyTorch 2.x SDPA."""
    backends: Dict[str, Any] = {
        "flash_attention": False,
        "memory_efficient": False,
        "math_attention": True,
    }
    if not torch.cuda.is_available():
        backends["probe"] = ProbeResult.unsupported(
            "CUDA không khả dụng; chỉ backend math có thể dùng."
        ).to_dict()
        return backends

    try:
        backends["flash_attention"] = (
            torch.cuda.get_device_capability(0)[0] >= 8
            and getattr(torch.backends.cuda, "flash_sdp_enabled", lambda: False)()
        )
        backends["memory_efficient"] = (
            torch.cuda.get_device_capability(0)[0] >= 7
            and getattr(torch.backends.cuda, "mem_efficient_sdp_enabled", lambda: False)()
        )
        backends["math_attention"] = getattr(
            torch.backends.cuda, "math_sdp_enabled", lambda: True
        )()
        backends["probe"] = ProbeResult.ok(True).to_dict()
    except Exception as exc:
        backends["probe"] = ProbeResult.failed(exc).to_dict()

    return backends


def get_hardware_recommendations(
    compute_capability: Optional[str] = None, vram_free_gb: float = 0.0
) -> Dict[str, Any]:
    """Đưa ra khuyến nghị cấu hình tối ưu nhất theo phần cứng thực tế."""
    has_cuda = torch.cuda.is_available()
    bf16_ok = check_bf16_support()
    backends = check_attention_backends()

    if not has_cuda:
        return {
            "device": "cpu",
            "recommended_precision": "float32",
            "recommended_batch_size": 8,
            "gradient_checkpointing": False,
            "attention_backend": "math",
            "notes": "Huấn luyện trên CPU: Khuyến nghị dùng FP32 và batch size nhỏ.",
        }

    # Đề xuất precision
    cap_val = float(compute_capability) if compute_capability else 0.0
    if bf16_ok and cap_val >= 8.0:
        rec_prec = "bfloat16"
        prec_note = "GPU Ampere/Ada (sm_80+): Hỗ trợ Native BF16 tối ưu cho LLM."
    elif cap_val >= 7.0:
        rec_prec = "float16"
        prec_note = "GPU Volta/Turing (sm_70/75): Khuyến nghị dùng FP16 với GradScaler."
    else:
        rec_prec = "float32"
        prec_note = "GPU đời cũ: Khuyến nghị dùng FP32 để đảm bảo độ chính xác."

    # Đề xuất attention
    if backends["flash_attention"]:
        rec_attn = "flash_attention_2"
    elif backends["memory_efficient"]:
        rec_attn = "cutlass_memory_efficient"
    else:
        rec_attn = "math"

    # Đề xuất gradient checkpointing theo VRAM
    rec_checkpointing = vram_free_gb < 8.0

    return {
        "device": "cuda",
        "recommended_precision": rec_prec,
        "recommended_batch_size": 32 if vram_free_gb >= 8.0 else (16 if vram_free_gb >= 4.0 else 8),
        "gradient_checkpointing": rec_checkpointing,
        "attention_backend": rec_attn,
        "notes": f"{prec_note} Nhân Attention: {rec_attn}. "
        + (
            "Bật Gradient Checkpointing để tiết kiệm VRAM."
            if rec_checkpointing
            else "VRAM thoải mái."
        ),
    }


def get_gpu_info() -> Dict[str, Any]:
    """Thu thập thông tin chi tiết về GPU và trạng thái VRAM qua CUDA."""
    try:
        cuda_available = bool(torch.cuda.is_available())
        device_count = torch.cuda.device_count() if cuda_available else 0
        probe = (
            ProbeResult.ok(True)
            if cuda_available
            else ProbeResult.unsupported("CUDA không khả dụng trên runtime hiện tại.")
        )
    except Exception as exc:
        cuda_available = False
        device_count = 0
        probe = ProbeResult.failed(exc)
    devices: List[Dict[str, Any]] = []

    if cuda_available:
        for i in range(device_count):
            props = torch.cuda.get_device_properties(i)
            major, minor = torch.cuda.get_device_capability(i)

            try:
                free_bytes, total_bytes = torch.cuda.mem_get_info(i)
                free_gb = round(free_bytes / (1024**3), 2)
                total_gb = round(total_bytes / (1024**3), 2)
                used_gb = round((total_bytes - free_bytes) / (1024**3), 2)
            except Exception:
                total_gb = round(props.total_memory / (1024**3), 2)
                allocated = torch.cuda.memory_allocated(i) / (1024**3)
                free_gb = round(total_gb - allocated, 2)
                used_gb = round(allocated, 2)

            device_info = {
                "id": i,
                "name": torch.cuda.get_device_name(i),
                "compute_capability": f"{major}.{minor}",
                "multi_processor_count": getattr(props, "multi_processor_count", None),
                "vram_total_gb": total_gb,
                "vram_free_gb": free_gb,
                "vram_used_gb": used_gb,
            }
            devices.append(device_info)

    primary_gpu = devices[0] if devices else None
    primary_cap = primary_gpu["compute_capability"] if primary_gpu else None
    primary_free_vram = primary_gpu["vram_free_gb"] if primary_gpu else 0.0

    return {
        "cuda_available": cuda_available,
        "device_count": device_count,
        "devices": devices,
        "primary_gpu": primary_gpu,
        "bf16_supported": check_bf16_support(),
        "sdpa_backends": check_attention_backends(),
        "recommendations": get_hardware_recommendations(primary_cap, primary_free_vram),
        "probe": probe.to_dict(),
    }


def probe_cuda_device(device_id: int = 0) -> Tuple[bool, str]:
    """Kiểm tra phản hồi thực tế của GPU bằng cách cấp phát và tính toán một tensor nhỏ."""
    if not torch.cuda.is_available():
        return False, "CUDA không khả dụng trên thiết bị này"

    if device_id >= torch.cuda.device_count():
        return False, f"Không tìm thấy GPU với ID {device_id}"

    try:
        device = f"cuda:{device_id}"
        # Cấp phát tensor và thực hiện phép nhân ma trận kiểm tra tính toán
        x = torch.ones((256, 256), device=device)
        y = torch.matmul(x, x)
        result_sum = float(y.sum().item())
        del x, y
        torch.cuda.empty_cache()
        return True, f"GPU {device_id} phản hồi tính toán bình thường (checksum: {result_sum:.0f})"
    except Exception as e:
        return False, f"Lỗi kiểm tra tính toán trên GPU {device_id}: {str(e)}"
