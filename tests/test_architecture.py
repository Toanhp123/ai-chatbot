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
