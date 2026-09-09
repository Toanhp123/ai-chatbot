"""Outer I/O for developer diagnostics endpoints.

Application diagnostics stays focused on use cases over domain/config capabilities;
quality-gate process execution and log-file access belong to the outer adapter layer.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict


class DiagnosticsRuntimeAdapter:
    @staticmethod
    def run_quality_gates() -> Dict[str, Any]:
        from scripts.check_all import (
            run_architecture_gate,
            run_diagnostics_gate,
            run_format_gate,
            run_lint_gate,
            run_test_suite_gate,
            run_type_gate,
        )

        gates = [
            run_format_gate,
            run_lint_gate,
            run_type_gate,
            run_architecture_gate,
            run_diagnostics_gate,
            run_test_suite_gate,
        ]
        started = time.time()
        results = [gate() for gate in gates]
        return {
            "all_passed": all(result.get("passed", False) for result in results),
            "total_elapsed": round(time.time() - started, 2),
            "results": results,
        }

    @staticmethod
    def logs(lines: int = 80) -> Dict[str, Any]:
        candidate_files = ["logs/train.log", "logs/engine.log"]
        log_file = next((path for path in candidate_files if os.path.exists(path)), None)
        if not log_file and os.path.exists("logs"):
            candidates = [
                os.path.join("logs", filename)
                for filename in os.listdir("logs")
                if filename.endswith(".log")
            ]
            if candidates:
                candidates.sort(key=os.path.getmtime, reverse=True)
                log_file = candidates[0]
        if not log_file or not os.path.exists(log_file):
            return {"logs": [], "total_lines": 0, "file": "logs/train.log"}
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
                all_lines = handle.readlines()
            tail = [line.rstrip() for line in all_lines[-lines:] if line.strip()]
            return {
                "logs": tail,
                "total_lines": len(all_lines),
                "file": log_file.replace("\\", "/"),
            }
        except OSError as exc:
            return {
                "logs": [f"Lỗi khi đọc file log: {exc}"],
                "total_lines": 0,
                "file": log_file.replace("\\", "/"),
            }


__all__ = ["DiagnosticsRuntimeAdapter"]
