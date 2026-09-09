import os

import pytest

from scripts.check_architecture import (
    check_architecture_boundaries,
    extract_imports_from_file,
    get_module_path,
)


def test_current_codebase_has_zero_architecture_violations():
    """Đảm bảo toàn bộ mã nguồn hiện tại trong src/ tuân thủ tuyệt đối ranh giới kiến trúc."""
    violations = check_architecture_boundaries("src")
    if violations:
        msg = "\n".join(
            f"- {v['filepath']}:{v['lineno']} [{v['source_module']}] -> {v['target_module']}: {v['reason']}"
            for v in violations
        )
        pytest.fail(f"Phát hiện vi phạm Clean Architecture trong dự án:\n{msg}")
    assert len(violations) == 0


def test_get_module_path():
    path = os.path.join("src", "core", "config", "model.py")
    mod = get_module_path(path)
    assert mod == "src.core.config.model"

    init_path = os.path.join("src", "core", "config", "__init__.py")
    init_mod = get_module_path(init_path)
    assert init_mod == "src.core.config"


def test_extract_imports_from_file(tmp_path):
    test_file = tmp_path / "sample.py"
    test_file.write_text(
        "import os\n"
        "import torch.nn as nn\n"
        "from src.core.exceptions import ModelArchitectureError\n"
        "from src.core.config import ModelConfig, EngineConfig\n",
        encoding="utf-8",
    )

    imports = extract_imports_from_file(str(test_file))
    imported_modules = [m for _, m in imports]

    assert "os" in imported_modules
    assert "torch.nn" in imported_modules
    assert "src.core.exceptions" in imported_modules
    assert "src.core.exceptions.ModelArchitectureError" in imported_modules
    assert "src.core.config.ModelConfig" in imported_modules


def test_architecture_boundary_checker_detects_violations(tmp_path):
    """Kiểm tra xem Architecture Linter có bắt được đoạn code cố tình vi phạm không."""
    src_dir = tmp_path / "src"
    models_dir = src_dir / "models"
    models_dir.mkdir(parents=True)

    bad_file = models_dir / "bad_model.py"
    bad_file.write_text(
        "# Model vi phạm: cố tình import từ training\nfrom src.training.trainer import Trainer\n",
        encoding="utf-8",
    )

    violations = check_architecture_boundaries(str(src_dir))
    assert len(violations) == 1
    v = violations[0]
    assert v["forbidden_rule"] == "src.training"
    assert "src.models" in v["rule_scope"]
    assert "bad_model.py" in v["filepath"]


def test_architecture_boundary_checker_detects_relative_import_violations(tmp_path):
    """Relative imports must not bypass the architecture boundary matrix."""
    src_dir = tmp_path / "src"
    models_dir = src_dir / "models"
    training_dir = src_dir / "training"
    models_dir.mkdir(parents=True)
    training_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (models_dir / "__init__.py").write_text("", encoding="utf-8")
    (training_dir / "__init__.py").write_text("", encoding="utf-8")

    bad_file = models_dir / "bad_relative.py"
    bad_file.write_text(
        "from ..training.trainer import Trainer\n",
        encoding="utf-8",
    )

    violations = check_architecture_boundaries(str(src_dir))
    assert len(violations) == 1
    assert violations[0]["forbidden_rule"] == "src.training"
    assert violations[0]["target_module"] == "src.training.trainer"


def test_model_registry_discovery_does_not_eagerly_import_architecture_package() -> None:
    from pathlib import Path

    registry_source = Path("src/models/registry.py").read_text(encoding="utf-8")
    architecture_init = Path("src/models/architectures/__init__.py").read_text(encoding="utf-8")

    assert "import src.models.architectures" not in registry_source
    assert "from src.models.architectures." not in architecture_init


def test_architecture_guardian_does_not_claim_more_than_it_checks() -> None:
    from pathlib import Path

    source = Path("scripts/check_architecture.py").read_text(encoding="utf-8")
    assert "CLEAN ARCHITECTURE 100% OK" not in source


def test_importing_core_config_is_side_effect_free(tmp_path) -> None:
    import json
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path.cwd()
    script = (
        "import json, os, sys; "
        "from src.core.config import ModelConfig; "
        "print(json.dumps({"
        "'torch_loaded': 'torch' in sys.modules, "
        "'rich_loaded': any(name == 'rich' or name.startswith('rich.') for name in sys.modules), "
        "'log_created': os.path.exists('logs/train.log')"
        "}))"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.strip())

    assert payload == {
        "torch_loaded": False,
        "rich_loaded": False,
        "log_created": False,
    }


def test_training_composition_roots_do_not_mutate_nested_config_in_place() -> None:
    import ast
    from pathlib import Path

    paths = [
        Path("main.py"),
        Path("src/application/training/service.py"),
        Path("src/ui/routes/diagnostics.py"),
    ]
    domains = {"system", "data", "model", "training", "generation"}
    violations = []

    def attribute_chain(node: ast.AST) -> list[str]:
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return list(reversed(parts))

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                if isinstance(node, ast.Assign):
                    targets = node.targets
                else:
                    targets = [node.target]
            for target in targets:
                chain = attribute_chain(target)
                if len(chain) >= 3 and chain[0] == "config" and chain[1] in domains:
                    violations.append(f"{path}:{getattr(node, 'lineno', 0)} -> {'.'.join(chain)}")

    assert violations == []


def test_training_composition_roots_use_runtime_plan_for_training_device() -> None:
    from pathlib import Path

    main_source = Path("main.py").read_text(encoding="utf-8")
    service_source = Path("src/application/training/service.py").read_text(encoding="utf-8")

    assert "resolve_device(config.system.device)" not in main_source
    assert "resolve_device(config.system.device)" not in service_source


def test_frontend_vram_budget_type_uses_backend_runtime_field_names() -> None:
    from pathlib import Path

    source = Path("frontend/src/entities/hardware/model/types.ts").read_text(encoding="utf-8")

    assert "device?: string;" in source
    assert "precision?: string;" in source
    assert "optimizer_type?: string;" in source
    assert "effective_device?: string;" not in source
    assert "effective_precision?: string;" not in source
    assert "effective_optimizer_type?: string;" not in source
    assert "effective_device: string;" in source
    assert "effective_precision: string;" in source
    assert "effective_optimizer: string;" in source
    assert "fallback_reasons: string[];" in source


def test_architecture_guardian_keeps_ui_adapters_out_of_inner_modules(tmp_path):
    src_dir = tmp_path / "src"
    ui_dir = src_dir / "ui"
    core_dir = src_dir / "core"
    ui_dir.mkdir(parents=True)
    core_dir.mkdir(parents=True)
    for folder in (src_dir, ui_dir, core_dir):
        (folder / "__init__.py").write_text("", encoding="utf-8")
    (ui_dir / "bad.py").write_text(
        "from src.core.config import EngineConfig\n",
        encoding="utf-8",
    )

    violations = check_architecture_boundaries(str(src_dir))

    assert any(
        violation["rule_scope"] == "src.ui" and violation["forbidden_rule"] == "src.core"
        for violation in violations
    )
