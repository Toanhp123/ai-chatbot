"""
Trình hiển thị Báo cáo Chẩn đoán (Diagnostic Reporter):
- Kết xuất giao diện bảng Rich Console trực quan, phân khu rõ ràng
- Xuất báo cáo ra định dạng JSON cho Telemetry hoặc CI/CD
- Duy trì hàm tương thích ngược print_diagnostic_report()
"""

import json
import os
from typing import Any, Dict, Optional

from src.core.diagnostics.runner import (
    DiagnosticReport,
    DiagnosticsRunner,
    DiagnosticStatus,
)
from src.core.diagnostics.storage import verify_directories


def export_diagnostic_json(report: DiagnosticReport, filepath: str) -> None:
    """Xuất báo cáo chẩn đoán ra file JSON."""
    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)


def print_diagnostic_report(report: Optional[DiagnosticReport] = None) -> None:
    """In báo cáo chẩn đoán toàn diện ra console."""
    if report is None:
        verify_directories()
        runner = DiagnosticsRunner()
        report = runner.run()

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console(legacy_windows=False)

        # 1. Tiêu đề và trạng thái tổng quan
        if report.status == DiagnosticStatus.HEALTHY:
            status_badge = "[bold green]✅ HEALTHY (Tối ưu cho Huấn luyện & Suy luận)[/bold green]"
            border_color = "green"
        elif report.status == DiagnosticStatus.WARNING:
            status_badge = "[bold yellow]⚠️ WARNING (Có cảnh báo cần lưu ý)[/bold yellow]"
            border_color = "yellow"
        else:
            status_badge = "[bold red]❌ CRITICAL (Môi trường gặp sự cố nghiêm trọng)[/bold red]"
            border_color = "red"

        console.print()
        console.print(
            Panel(
                f"Thời gian kiểm tra: [cyan]{report.timestamp}[/cyan]\n"
                f"Đánh giá tổng thể: {status_badge}",
                title="🔍 BÁO CÁO CHẨN ĐOÁN HỆ THỐNG (SYSTEM HEALTH REPORT)",
                border_style=border_color,
            )
        )

        # 2. Bảng Phần mềm & Môi trường
        sys_info = report.system
        t_sys = Table(
            title="🖥️ Môi Trường & Phiên Bản Phần Mềm", show_header=True, header_style="bold cyan"
        )
        t_sys.add_column("Mục", style="bold")
        t_sys.add_column("Chi Tiết", style="green")
        t_sys.add_column("Đánh Giá", style="yellow")

        t_sys.add_row(
            "Hệ điều hành",
            f"{sys_info.get('os_platform')} ({sys_info.get('architecture')})",
            "✅ Tốt",
        )
        t_sys.add_row(
            "Python",
            f"{sys_info.get('python_version')} ({sys_info.get('python_executable')})",
            "✅ Tốt",
        )
        t_sys.add_row(
            "PyTorch",
            f"{sys_info.get('pytorch_version')} | CUDA: {sys_info.get('cuda_runtime_version')} | cuDNN: {sys_info.get('cudnn_version')}",
            "⚡ Chuẩn AI",
        )
        console.print(t_sys)

        # 3. Bảng Phần cứng & Bộ nhớ
        hw = report.hardware
        cpu = hw.get("cpu", {})
        mem = hw.get("memory", {})
        gpu = hw.get("gpu", {})

        t_hw = Table(
            title="⚡ Tài Nguyên Phần Cứng & Thiết Bị Tính Toán",
            show_header=True,
            header_style="bold magenta",
        )
        t_hw.add_column("Thiết Bị", style="bold")
        t_hw.add_column("Thông Số Kỹ Thuật", style="green")
        t_hw.add_column("Khả Dụng", style="yellow")

        t_hw.add_row(
            "Bộ xử lý CPU",
            f"{cpu.get('physical_cores')} nhân vật lý, {cpu.get('logical_cores')} luồng",
            f"Tải: {cpu.get('cpu_usage_percent', 'N/A')}%",
        )
        mem_percent = mem.get("percent_used")
        if isinstance(mem_percent, (int, float)):
            mem_available = f"Trống: {mem.get('available_gb')} GB ({100 - mem_percent:.1f}% rảnh)"
        else:
            mem_available = "Trống: chưa xác định (probe thất bại)"
        t_hw.add_row(
            "RAM Hệ thống",
            f"Tổng: {mem.get('total_gb') if mem.get('total_gb') is not None else 'N/A'} GB",
            mem_available,
        )

        if gpu.get("cuda_available"):
            for d in gpu.get("devices", []):
                t_hw.add_row(
                    f"GPU [{d.get('id')}]: {d.get('name')}",
                    f"Compute {d.get('compute_capability')} | VRAM Tổng: {d.get('vram_total_gb')} GB",
                    f"VRAM Trống: [bold green]{d.get('vram_free_gb')} GB[/bold green]",
                )
        else:
            t_hw.add_row(
                "Card đồ họa (GPU)", "Không phát hiện GPU CUDA (Chạy trên CPU)", "⚠️ Chậm hơn nhiều"
            )

        console.print(t_hw)

        # 3.5 Bảng Năng Lực Tăng Tốc Phần Cứng & AI Backends
        if gpu.get("cuda_available"):
            t_ai = Table(
                title="🚀 Năng Lực Tăng Tốc Phần Cứng & AI Backends (PyTorch SDPA)",
                show_header=True,
                header_style="bold cyan",
            )
            t_ai.add_column("Tính Năng / Nhân Tăng Tốc", style="bold")
            t_ai.add_column("Trạng Thái", justify="center")
            t_ai.add_column("Đánh Giá Kỹ Thuật", style="yellow")

            bf16_ok = gpu.get("bf16_supported", False)
            sdpa = gpu.get("sdpa_backends", {})
            recs = gpu.get("recommendations", {})

            t_ai.add_row(
                "Native Bfloat16 (BF16)",
                "[bold green]✅ Hỗ trợ[/bold green]"
                if bf16_ok
                else "[bold yellow]⚠️ Không hỗ trợ[/bold yellow]",
                "Tối ưu cho LLM, tránh underflow"
                if bf16_ok
                else "GPU Turing/cũ hơn: Khuyến nghị dùng FP16",
            )
            t_ai.add_row(
                "FlashAttention-2",
                "[bold green]✅ Sẵn sàng[/bold green]"
                if sdpa.get("flash_attention")
                else "[bold yellow]⚠️ Cần sm_80+[/bold yellow]",
                "Tốc độ cực nhanh, tiết kiệm VRAM bậc nhất"
                if sdpa.get("flash_attention")
                else "Tự động chuyển sang Cutlass/Math",
            )
            t_ai.add_row(
                "Memory-Efficient Attention (Cutlass)",
                "[bold green]✅ Sẵn sàng[/bold green]"
                if sdpa.get("memory_efficient")
                else "[bold red]❌ Chưa có[/bold red]",
                "Nhân Attention tối ưu cho GPU Turing (GTX 16xx, RTX 20xx)",
            )
            t_ai.add_row(
                "Khuyến nghị Precision",
                f"[bold magenta]{recs.get('recommended_precision', 'FP32').upper()}[/bold magenta]",
                recs.get("notes", "Cấu hình chuẩn"),
            )
            console.print(t_ai)

        # 4. Bảng Ổ đĩa & Quyền Thư mục
        storage = report.storage
        perms = report.permissions
        t_io = Table(
            title="💾 Ổ Đĩa & Phân Quyền Thư Mục Làm Việc",
            show_header=True,
            header_style="bold blue",
        )
        t_io.add_column("Thành Phần", style="bold")
        t_io.add_column("Dung Lượng / Trạng Thái", style="green")
        t_io.add_column("Quyền Truy Cập (I/O)", style="yellow")

        free_storage = storage.get("free_gb")
        storage_assessment = (
            "✅ Đủ an toàn"
            if isinstance(free_storage, (int, float)) and free_storage >= 5
            else "⚠️ Cần giải phóng"
            if isinstance(free_storage, (int, float))
            else "⚠️ Chưa xác định"
        )
        t_io.add_row(
            "Ổ đĩa làm việc",
            f"Trống: {free_storage if free_storage is not None else 'N/A'} GB / Tổng: {storage.get('total_gb') if storage.get('total_gb') is not None else 'N/A'} GB",
            storage_assessment,
        )

        for d_name, d_status in perms.items():
            perm_str = "R/W (Đọc & Ghi OK)" if d_status.get("writable") else "❌ Không có quyền ghi"
            t_io.add_row(
                f"Thư mục '{d_name}/'", "Tồn tại" if d_status.get("exists") else "Chưa có", perm_str
            )

        console.print(t_io)

        # 5. Cảnh báo và Khuyến nghị
        if report.warnings or report.suggestions:
            warn_content = ""
            for w in report.warnings:
                warn_content += f"• [yellow]Cảnh báo:[/] {w}\n"
            for s in report.suggestions:
                warn_content += f"• [cyan]Khuyến nghị:[/] {s}\n"

            console.print(
                Panel(
                    warn_content.strip(),
                    title="💡 LƯU Ý & KHUYẾN NGHỊ KHẮC PHỤC",
                    border_style="yellow",
                )
            )

        console.print()

    except ImportError:
        # Fallback cho console thuần không có Rich
        print(f"\n=== Báo Cáo Chẩn Đoán Hệ Thống ({report.status.value}) ===")
        print(f"Hệ điều hành: {report.system.get('os_platform')}")
        print(f"Python: {report.system.get('python_version')}")
        print(f"PyTorch: {report.system.get('pytorch_version')}")
        print(f"CUDA: {report.hardware.get('gpu', {}).get('cuda_available')}")
        print(f"Đĩa trống: {report.storage.get('free_gb')} GB")
        if report.warnings:
            print("Cảnh báo:")
            for w in report.warnings:
                print(f"  - {w}")
        print("===================================================\n")


def print_vram_scenarios_table(scenarios_data: Dict[str, Any]) -> None:
    """In bảng so sánh các kịch bản bộ nhớ VRAM huấn luyện trực quan."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console(legacy_windows=False)
        available_vram = scenarios_data.get("available_vram_gb", 0.0)

        table = Table(
            title="🧠 BẢNG DỰ TOÁN VRAM THEO KỊCH BẢN HUẤN LUYỆN (VRAM BUDGET SCENARIOS)",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Kịch Bản Huấn Luyện", style="bold")
        table.add_column("Độ Chính Xác", justify="center", style="magenta")
        table.add_column("Checkpointing", justify="center")
        table.add_column("VRAM Dự Toán", justify="right", style="green")
        table.add_column("Tỷ Lệ VRAM", justify="right", style="cyan")
        table.add_column("Đánh Giá Khả Thi", justify="center")

        for sc in scenarios_data.get("scenarios", []):
            cp_str = "Bật (Giảm 70%)" if sc.get("gradient_checkpointing") else "Tắt"
            status_str = (
                "[bold green]✅ Khả thi[/bold green]"
                if sc.get("feasible")
                else "[bold red]❌ Nguy cơ OOM[/bold red]"
            )
            table.add_row(
                sc.get("name", ""),
                sc.get("precision", "").upper(),
                cp_str,
                f"{sc.get('estimated_gb', 0):.2f} GB",
                f"{sc.get('utilization_pct', 0):.1f}%" if available_vram > 0 else "N/A",
                status_str,
            )

        console.print()
        console.print(table)

        rec = scenarios_data.get("recommended")
        if rec:
            console.print(
                Panel(
                    f"🎯 [bold green]Kịch Bản Khuyến Nghị:[/] [bold cyan]{rec.get('name')}[/bold cyan]\n"
                    f"• VRAM ước tính: [bold]{rec.get('estimated_gb')} GB[/bold] / {available_vram:.2f} GB khả dụng\n"
                    f"• Mô tả: {rec.get('description')}",
                    title="💡 AUTO-RECOMMENDATION CHO PHẦN CỨNG HIỆN TẠI",
                    border_style="green",
                )
            )
        console.print()

    except ImportError:
        print("\n=== BẢNG DỰ TOÁN VRAM THEO KỊCH BẢN ===")
        for sc in scenarios_data.get("scenarios", []):
            status = "KHẢ THI" if sc.get("feasible") else "NGUY CƠ OOM"
            print(f"- {sc.get('name')}: {sc.get('estimated_gb')} GB [{status}]")
        print("=======================================\n")
