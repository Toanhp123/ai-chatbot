"""
Bộ công cụ Debug và kiểm tra an toàn cho Tensor:
- Phát hiện NaN, Inf trong activations và gradients
- Theo dõi VRAM thời gian thực
- Phân tích chi tiết tham số từng tầng của mô hình
"""

from typing import Dict, Tuple

import torch
import torch.nn as nn

from src.core.exceptions import TrainingDivergedError


def assert_valid_tensor(tensor: torch.Tensor, name: str = "tensor") -> None:
    """Kiểm tra tensor có chứa NaN hoặc Inf hay không."""
    if torch.isnan(tensor).any():
        raise TrainingDivergedError(f"Phát hiện giá trị NaN trong {name}!", {"tensor_name": name})
    if torch.isinf(tensor).any():
        raise TrainingDivergedError(f"Phát hiện giá trị Inf trong {name}!", {"tensor_name": name})


def check_model_gradients(model: nn.Module) -> Tuple[bool, float]:
    """Kiểm tra toàn bộ gradient của mô hình và tính norm tối đa."""
    max_norm = 0.0
    for name, param in model.named_parameters():
        if param.grad is not None:
            if torch.isnan(param.grad).any():
                raise TrainingDivergedError(f"Phát hiện NaN trong gradient của tham số: {name}")
            if torch.isinf(param.grad).any():
                raise TrainingDivergedError(f"Phát hiện Inf trong gradient của tham số: {name}")
            norm = param.grad.data.norm(2).item()
            if norm > max_norm:
                max_norm = norm
    return True, max_norm


def get_cuda_memory_mb() -> Dict[str, float]:
    """Lấy lượng VRAM hiện tại đang cấp phát và đỉnh điểm (Peak)."""
    if not torch.cuda.is_available():
        return {"allocated_mb": 0.0, "reserved_mb": 0.0, "peak_mb": 0.0}
    return {
        "allocated_mb": round(torch.cuda.memory_allocated() / (1024**2), 2),
        "reserved_mb": round(torch.cuda.memory_reserved() / (1024**2), 2),
        "peak_mb": round(torch.cuda.max_memory_allocated() / (1024**2), 2),
    }


def print_model_summary(model: nn.Module):
    """In bảng cấu trúc các tầng và số lượng tham số bằng Rich Table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(
        title="🧠 Phân Tích Cấu Trúc Tham Số Mô Hình", show_header=True, header_style="bold cyan"
    )
    table.add_column("Tên Tầng (Layer)", style="white")
    table.add_column("Kiểu Module", style="yellow")
    table.add_column("Số Tham Số", justify="right", style="green")
    table.add_column("Đòi Hỏi Gradient", justify="center", style="magenta")

    total_params = 0
    trainable_params = 0

    for name, module in model.named_children():
        num = sum(p.numel() for p in module.parameters())
        requires_grad = any(p.requires_grad for p in module.parameters())
        table.add_row(
            name, module.__class__.__name__, f"{num:,}", "Có" if requires_grad else "Không"
        )
        total_params += num
        if requires_grad:
            trainable_params += num

    console.print(table)
    console.print(
        f"[bold green]Tổng số tham số: {total_params:,} | Tham số huấn luyện: {trainable_params:,}[/bold green]\n"
    )
