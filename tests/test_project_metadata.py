"""Project metadata must be portable and sufficient to bootstrap the runtime."""

import tomllib
from pathlib import Path


def _pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def test_runtime_dependencies_are_declared() -> None:
    project = _pyproject()["project"]
    declared = {
        dep.split("[", 1)[0].split("=", 1)[0].split(">", 1)[0].split("<", 1)[0].strip().lower()
        for dep in project.get("dependencies", [])
    }
    assert {
        "torch",
        "numpy",
        "pyyaml",
        "psutil",
        "rich",
        "fastapi",
        "pydantic",
        "uvicorn",
    } <= declared


def test_dev_quality_gate_dependencies_are_declared() -> None:
    extras = _pyproject()["project"].get("optional-dependencies", {})
    declared = " ".join(extras.get("dev", [])).lower()
    for package in ("pytest", "ruff", "pyright"):
        assert package in declared


def test_pyright_config_has_no_machine_specific_virtualenv_path() -> None:
    pyright = _pyproject().get("tool", {}).get("pyright", {})
    assert "venvPath" not in pyright
    assert "venv" not in pyright
