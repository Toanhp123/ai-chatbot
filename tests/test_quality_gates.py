"""Quality gate runner diagnostics must distinguish missing tools from code failures."""

from types import SimpleNamespace

from scripts.check_all import run_format_gate, run_lint_gate, run_type_gate


def _missing_module(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=1,
        stdout="",
        stderr=f"python: No module named {name}",
    )


def test_format_gate_reports_missing_ruff(monkeypatch) -> None:
    monkeypatch.setattr("scripts.check_all.subprocess.run", lambda *a, **k: _missing_module("ruff"))
    result = run_format_gate()
    assert result["passed"] is False
    assert "chưa được cài" in result["details"]


def test_lint_gate_reports_missing_ruff(monkeypatch) -> None:
    monkeypatch.setattr("scripts.check_all.subprocess.run", lambda *a, **k: _missing_module("ruff"))
    result = run_lint_gate()
    assert result["passed"] is False
    assert "chưa được cài" in result["details"]


def test_type_gate_reports_missing_pyright(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.check_all.subprocess.run", lambda *a, **k: _missing_module("pyright")
    )
    result = run_type_gate()
    assert result["passed"] is False
    assert "chưa được cài" in result["details"]
