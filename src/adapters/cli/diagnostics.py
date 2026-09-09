"""Terminal rendering and exit-code adapters for diagnostics use cases."""

from __future__ import annotations

from typing import Iterable, Optional

from src.application.diagnostics import DiagnosticsApplicationService
from src.core.diagnostics import print_diagnostic_report, print_vram_scenarios_table
from src.utils.tensor_inspector import print_model_summary


def print_system_report() -> None:
    print_diagnostic_report()


def print_scenarios(
    service: DiagnosticsApplicationService,
    source: Optional[str],
    overrides: Iterable[str] = (),
) -> None:
    print_vram_scenarios_table(service.scenarios_from_config(source, tuple(overrides)))


def print_inspect(
    service: DiagnosticsApplicationService,
    source: Optional[str],
    overrides: Iterable[str] = (),
) -> None:
    print_model_summary(service.model_for_inspection(source, tuple(overrides)))


def run_quality_gates_cli() -> int:
    from scripts.check_all import main as run_quality_gates

    return int(run_quality_gates())


__all__ = [
    "print_system_report",
    "print_scenarios",
    "print_inspect",
    "run_quality_gates_cli",
]
