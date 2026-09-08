"""
Trình điều phối kiểm tra chất lượng mã nguồn toàn diện (Unified Quality Gates Runner):
Tự động kích hoạt 5 chốt chặn chất lượng:
1. Format Gate: Kiểm tra định dạng chuẩn PEP 8 bằng Ruff
2. Lint Gate: Kiểm tra lỗi cú pháp, biến/import thừa bằng Ruff
3. Architecture Gate: Kiểm tra ranh giới Clean Architecture / Modular Monolith
4. Diagnostics Gate: Kiểm tra sức khỏe phần cứng, CUDA, VRAM và quyền ổ đĩa
5. Test Suite Gate: Chạy toàn bộ bộ kiểm thử tự động PyTest
"""

import os
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List

if sys.platform == "win32":
    try:
        reconfigure_out = getattr(sys.stdout, "reconfigure", None)
        if callable(reconfigure_out):
            reconfigure_out(encoding="utf-8", errors="replace")
        reconfigure_err = getattr(sys.stderr, "reconfigure", None)
        if callable(reconfigure_err):
            reconfigure_err(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Đảm bảo thư mục gốc nằm trong sys.path khi chạy script độc lập
sys.path.insert(0, os.path.abspath("."))

from scripts.check_architecture import check_architecture_boundaries
from src.core.diagnostics.runner import DiagnosticsRunner, DiagnosticStatus


def _missing_module(res: subprocess.CompletedProcess[str], module: str) -> bool:
    output = f"{res.stdout}\n{res.stderr}"
    return f"No module named {module}" in output


def run_format_gate() -> Dict[str, Any]:
    """Gate 1: Kiểm tra định dạng mã nguồn bằng Ruff Formatter."""
    t0 = time.time()
    res = subprocess.run(
        [sys.executable, "-m", "ruff", "format", ".", "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - t0
    passed = res.returncode == 0
    missing_tool = _missing_module(res, "ruff")
    details = (
        "Mã nguồn tuân thủ 100% định dạng chuẩn"
        if passed
        else (
            "Ruff chưa được cài trong môi trường hiện tại (cài extra dev của dự án)"
            if missing_tool
            else "Có file chưa được format (chạy 'ruff format .')"
        )
    )
    return {
        "name": "1. Format Gate",
        "tool": "Ruff Formatter",
        "passed": passed,
        "elapsed": elapsed,
        "details": details,
        "error_output": (res.stderr.strip() or res.stdout.strip()) if not passed else "",
    }


def run_lint_gate() -> Dict[str, Any]:
    """Gate 2: Kiểm tra linter và sắp xếp import bằng Ruff Linter."""
    t0 = time.time()
    res = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - t0
    passed = res.returncode == 0
    missing_tool = _missing_module(res, "ruff")
    details = (
        "0 lỗi cú pháp, 0 biến/import thừa"
        if passed
        else (
            "Ruff chưa được cài trong môi trường hiện tại (cài extra dev của dự án)"
            if missing_tool
            else "Phát hiện vi phạm linter (chạy 'ruff check . --fix')"
        )
    )
    return {
        "name": "2. Lint Gate",
        "tool": "Ruff Linter",
        "passed": passed,
        "elapsed": elapsed,
        "details": details,
        "error_output": (res.stdout.strip() or res.stderr.strip()) if not passed else "",
    }


def run_type_gate() -> Dict[str, Any]:
    """Gate 3: Kiểm tra kiểu dữ liệu tĩnh và bắt Dead Code / Unreachable bằng Pyright."""
    t0 = time.time()
    res = subprocess.run(
        [sys.executable, "-m", "pyright"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - t0
    passed = res.returncode == 0
    missing_tool = _missing_module(res, "pyright")
    details = (
        "0 lỗi kiểu dữ liệu & 0 dead/unreachable code"
        if passed
        else (
            "Pyright chưa được cài trong môi trường hiện tại (cài extra dev của dự án)"
            if missing_tool
            else "Phát hiện lỗi kiểu hoặc dead/unreachable code (chạy 'pyright')"
        )
    )
    return {
        "name": "3. Type Check Gate",
        "tool": "Pyright",
        "passed": passed,
        "elapsed": elapsed,
        "details": details,
        "error_output": (res.stdout.strip() or res.stderr.strip()) if not passed else "",
    }


def run_architecture_gate() -> Dict[str, Any]:
    """Gate 4: Kiểm tra ranh giới phân tầng Clean Architecture."""
    t0 = time.time()
    violations = check_architecture_boundaries("src")
    elapsed = time.time() - t0
    passed = len(violations) == 0
    arch_err = ""
    if not passed:
        arch_err = "\n".join([f"• {v['file']}:{v['line']} - {v['message']}" for v in violations])
    return {
        "name": "4. Architecture Gate",
        "tool": "AST Boundary Linter",
        "passed": passed,
        "elapsed": elapsed,
        "details": "Ranh giới các tầng hoàn toàn phân lập"
        if passed
        else f"Có {len(violations)} câu lệnh import sai phân tầng",
        "error_output": arch_err,
    }


def run_diagnostics_gate() -> Dict[str, Any]:
    """Gate 5: Kiểm tra sức khỏe phần cứng, CUDA và thư mục làm việc."""
    t0 = time.time()
    runner = DiagnosticsRunner()
    report = runner.run(test_tensor_allocation=True)
    elapsed = time.time() - t0
    passed = report.status != DiagnosticStatus.CRITICAL
    diag_err = ""
    if not passed:
        diag_err = f"Trạng thái hệ thống: {report.status.value}"

    return {
        "name": "5. Diagnostics Gate",
        "tool": "DiagnosticsRunner",
        "passed": passed,
        "elapsed": elapsed,
        "details": f"Trạng thái: {report.status.value}"
        if passed
        else "Phần cứng hoặc quyền I/O thư mục gặp lỗi CRITICAL",
        "error_output": diag_err,
    }


def run_test_suite_gate() -> Dict[str, Any]:
    """Gate 6: Thực thi toàn bộ bộ kiểm thử tự động pytest."""
    t0 = time.time()
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-v"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - t0
    passed = res.returncode == 0
    return {
        "name": "6. Test Suite Gate",
        "tool": "PyTest",
        "passed": passed,
        "elapsed": elapsed,
        "details": "100% tests PASSED" if passed else "Có test bị FAILED trong thư mục tests/",
        "error_output": (res.stdout.strip() or res.stderr.strip()) if not passed else "",
    }


def main() -> int:
    """Điều phối toàn bộ chu trình Quality Gates."""
    gates: List[Callable[[], Dict[str, Any]]] = [
        run_format_gate,
        run_lint_gate,
        run_type_gate,
        run_architecture_gate,
        run_diagnostics_gate,
        run_test_suite_gate,
    ]

    total_start = time.time()
    results: List[Dict[str, Any]] = []

    for gate_fn in gates:
        res = gate_fn()
        results.append(res)

    total_elapsed = time.time() - total_start
    all_passed = all(r["passed"] for r in results)

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console(legacy_windows=False)
        console.print()

        table = Table(
            title="🛡️ BẢNG TỔNG KẾT QUALITY GATES (SYSTEM AUDIT REPORT)",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Chốt Chặn (Gate)", style="bold")
        table.add_column("Công Cụ Kiểm Tra", style="magenta")
        table.add_column("Thời Gian", justify="right", style="cyan")
        table.add_column("Kết Quả", justify="center")
        table.add_column("Chi Tiết Đánh Giá", style="yellow")

        for r in results:
            status_str = (
                "[bold green]✅ PASS[/bold green]"
                if r["passed"]
                else "[bold red]❌ FAIL[/bold red]"
            )
            table.add_row(
                r["name"],
                r["tool"],
                f"{r['elapsed']:.2f}s",
                status_str,
                r["details"],
            )

        console.print(table)
        console.print()

        if all_passed:
            console.print(
                Panel(
                    f"[bold green]🎉 TẤT CẢ 6 QUALITY GATES ĐỀU ĐẠT CHUẨN 100%![/bold green]\n"
                    f"Hệ thống đã sẵn sàng cho Commit, Push hoặc Deploy an toàn. (Tổng thời gian: {total_elapsed:.2f}s)",
                    title="🏆 KIỂM TOÁN HOÀN TẤT THÀNH CÔNG",
                    border_style="green",
                )
            )
            console.print()
            return 0
        else:
            for r in results:
                if not r["passed"] and r.get("error_output"):
                    console.print(
                        Panel(
                            r["error_output"],
                            title=f"🔍 Chi Tiết Lỗi: {r['name']} ({r['tool']})",
                            border_style="red",
                        )
                    )
            console.print(
                Panel(
                    "[bold red]❌ MỘT SỐ QUALITY GATES CHƯA ĐẠT CHUẨN![/bold red]\n"
                    "Vui lòng sửa các lỗi được liệt kê ở bảng phía trên trước khi tiếp tục.",
                    title="⚠️ KIỂM TOÁN THẤT BẠI",
                    border_style="red",
                )
            )
            console.print()
            return 1

    except ImportError:
        print("\n=== BẢNG TỔNG KẾT QUALITY GATES ===")
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"[{status}] {r['name']} ({r['tool']}) in {r['elapsed']:.2f}s: {r['details']}")
            if not r["passed"] and r.get("error_output"):
                print(f"  >>> Chi Tiết:\n{r['error_output']}")
        print(f"Tổng thời gian: {total_elapsed:.2f}s")
        print("===================================\n")
        return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
