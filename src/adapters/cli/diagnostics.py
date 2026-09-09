"""Terminal rendering and exit-code adapters for diagnostics use cases."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from src.application.diagnostics import DiagnosticsApplicationService


def _console():
    try:
        from rich.console import Console

        return Console(legacy_windows=False)
    except ImportError:
        return None


def _render_system_report(report: Dict[str, Any]) -> None:
    console = _console()
    if console is None:
        print(f"\n=== Báo Cáo Chẩn Đoán Hệ Thống ({report.get('status', 'UNKNOWN')}) ===")
        print(f"Hệ điều hành: {report.get('system', {}).get('os_platform')}")
        print(f"Python: {report.get('system', {}).get('python_version')}")
        print(f"PyTorch: {report.get('system', {}).get('pytorch_version')}")
        print(f"CUDA: {report.get('hardware', {}).get('gpu', {}).get('cuda_available')}")
        print(f"Đĩa trống: {report.get('storage', {}).get('free_gb')} GB")
        for warning in report.get("warnings", []):
            print(f"  - Cảnh báo: {warning}")
        print("===================================================\n")
        return

    from rich.panel import Panel
    from rich.table import Table

    status = str(report.get("status", "UNKNOWN"))
    system = report.get("system", {})
    hardware = report.get("hardware", {})
    cpu = hardware.get("cpu", {})
    memory = hardware.get("memory", {})
    gpu = hardware.get("gpu", {})
    storage = report.get("storage", {})

    console.print()
    console.print(
        Panel(
            f"Thời gian kiểm tra: [cyan]{report.get('timestamp', 'N/A')}[/cyan]\n"
            f"Đánh giá tổng thể: [bold]{status}[/bold]",
            title="🔍 BÁO CÁO CHẨN ĐOÁN HỆ THỐNG",
        )
    )

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Thành phần", style="bold")
    table.add_column("Thông tin")
    table.add_row("Hệ điều hành", str(system.get("os_platform", "N/A")))
    table.add_row("Python", str(system.get("python_version", "N/A")))
    table.add_row("PyTorch", str(system.get("pytorch_version", "N/A")))
    table.add_row(
        "CPU",
        f"{cpu.get('physical_cores', 'N/A')} core / {cpu.get('logical_cores', 'N/A')} thread",
    )
    table.add_row(
        "RAM",
        f"{memory.get('available_gb', 'N/A')} GB trống / {memory.get('total_gb', 'N/A')} GB",
    )
    if gpu.get("cuda_available"):
        primary = gpu.get("primary_gpu") or {}
        table.add_row(
            "GPU",
            f"{primary.get('name', 'CUDA')} | {primary.get('vram_free_gb', 'N/A')} GB VRAM trống",
        )
    else:
        table.add_row("GPU", "Không phát hiện CUDA")
    table.add_row("Ổ đĩa", f"{storage.get('free_gb', 'N/A')} GB trống")
    console.print(table)

    notes = [
        *(f"• [yellow]Cảnh báo:[/] {x}" for x in report.get("warnings", [])),
        *(f"• [cyan]Khuyến nghị:[/] {x}" for x in report.get("suggestions", [])),
    ]
    if notes:
        console.print(Panel("\n".join(notes), title="💡 LƯU Ý & KHUYẾN NGHỊ"))
    console.print()


def _render_vram_scenarios(scenarios_data: Dict[str, Any]) -> None:
    console = _console()
    if console is None:
        print("\n=== BẢNG DỰ TOÁN VRAM THEO KỊCH BẢN ===")
        for scenario in scenarios_data.get("scenarios", []):
            status = "KHẢ THI" if scenario.get("feasible") else "NGUY CƠ OOM"
            print(f"- {scenario.get('name')}: {scenario.get('estimated_gb')} GB [{status}]")
        print("=======================================\n")
        return

    from rich.panel import Panel
    from rich.table import Table

    available_vram = scenarios_data.get("available_vram_gb", 0.0)
    table = Table(
        title="🧠 BẢNG DỰ TOÁN VRAM THEO KỊCH BẢN HUẤN LUYỆN",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Kịch Bản", style="bold")
    table.add_column("Precision", justify="center")
    table.add_column("Checkpointing", justify="center")
    table.add_column("VRAM", justify="right")
    table.add_column("Tỷ Lệ", justify="right")
    table.add_column("Khả Thi", justify="center")
    for scenario in scenarios_data.get("scenarios", []):
        table.add_row(
            str(scenario.get("name", "")),
            str(scenario.get("precision", "")).upper(),
            "Bật" if scenario.get("gradient_checkpointing") else "Tắt",
            f"{scenario.get('estimated_gb', 0):.2f} GB",
            f"{scenario.get('utilization_pct', 0):.1f}%" if available_vram else "N/A",
            "✅" if scenario.get("feasible") else "❌",
        )
    console.print()
    console.print(table)
    recommended = scenarios_data.get("recommended")
    if recommended:
        console.print(
            Panel(
                f"[bold cyan]{recommended.get('name')}[/bold cyan]\n"
                f"VRAM: {recommended.get('estimated_gb')} GB / {available_vram:.2f} GB\n"
                f"{recommended.get('description', '')}",
                title="💡 KỊCH BẢN KHUYẾN NGHỊ",
            )
        )
    console.print()


def _render_model_inspection(info: Dict[str, Any]) -> None:
    console = _console()
    if console is None:
        print(f"\n=== MODEL {info.get('model_name', 'N/A')} ===")
        print(
            f"Tổng tham số: {info.get('total_parameters_formatted', info.get('total_parameters'))}"
        )
        for layer in info.get("layers", []):
            print(f"- {layer.get('name')}: {layer.get('params')} params {layer.get('shape')}")
        print("==============================\n")
        return

    from rich.table import Table

    table = Table(
        title=f"🧠 Phân Tích Mô Hình: {info.get('model_name', 'N/A')}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Tham số / Tensor", style="white")
    table.add_column("Shape", style="yellow")
    table.add_column("Số tham số", justify="right", style="green")
    table.add_column("Gradient", justify="center")
    for layer in info.get("layers", []):
        table.add_row(
            str(layer.get("name", "")),
            str(layer.get("shape", [])),
            f"{int(layer.get('params', 0)):,}",
            "Có" if layer.get("trainable") else "Không",
        )
    console.print(table)
    console.print(
        f"[bold green]Tổng số tham số: {info.get('total_parameters_formatted', info.get('total_parameters', 0))}[/bold green]\n"
    )


def print_system_report(service: DiagnosticsApplicationService) -> None:
    _render_system_report(service.report())


def print_scenarios(
    service: DiagnosticsApplicationService,
    source: Optional[str],
    overrides: Iterable[str] = (),
) -> None:
    _render_vram_scenarios(service.scenarios_from_config(source, tuple(overrides)))


def print_inspect(
    service: DiagnosticsApplicationService,
    source: Optional[str],
    overrides: Iterable[str] = (),
) -> None:
    config_source = source
    info = service.inspect(source=config_source, overrides=tuple(overrides))
    _render_model_inspection(info)


def run_quality_gates_cli() -> int:
    from scripts.check_all import main as run_quality_gates

    return int(run_quality_gates())


__all__ = [
    "print_system_report",
    "print_scenarios",
    "print_inspect",
    "run_quality_gates_cli",
]
