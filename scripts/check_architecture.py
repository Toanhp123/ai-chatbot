"""
Bộ kiểm toán & khóa chặt ranh giới kiến trúc (Architecture Guardian):
Sử dụng phân tích cú pháp tĩnh AST (Abstract Syntax Tree) để quét toàn bộ mã nguồn
và ngăn chặn bất kỳ hành vi phá vỡ nguyên lý Clean Architecture / Modular Monolith.
"""

import ast
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

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

# Ma trận ranh giới phụ thuộc (Dependency Boundaries Matrix)
# Key: Module nguồn
# Value: Danh sách các module bị CẤM import (Forbidden Imports)
FORBIDDEN_DEPENDENCIES: Dict[str, List[str]] = {
    # Tầng Core: Lõi trừu tượng, tuyệt đối không phụ thuộc vào bất kỳ tầng bên ngoài nào
    "src.core": [
        "src.data",
        "src.models",
        "src.training",
        "src.generation",
        "src.utils",
        "src.ui",
        "src.application",
        "src.adapters",
    ],
    # Tầng Models: Chỉ phụ thuộc Core & Utils, không biết gì về Data hay Training/Generation/UI
    "src.models": [
        "src.data",
        "src.training",
        "src.generation",
        "src.inference",
        "src.ui",
        "src.application",
        "src.adapters",
    ],
    # Tầng Data: Chỉ phụ thuộc Core & Utils, không phụ thuộc Models, Training hay UI
    "src.data": [
        "src.models",
        "src.training",
        "src.generation",
        "src.inference",
        "src.ui",
        "src.application",
        "src.adapters",
    ],
    # Tầng Generation: Phụ thuộc Core & Utils, không phụ thuộc Training, Data hay UI
    "src.generation": [
        "src.training",
        "src.data",
        "src.models",
        "src.inference",
        "src.ui",
        "src.application",
        "src.adapters",
    ],
    # Tầng Training: Tuân thủ Dependency Inversion, không import trực tiếp concrete DataPipeline, Generator hay UI
    "src.training": [
        "src.data.dataset.DataPipeline",
        "src.data.pipeline",
        "src.inference",
        "src.ui",
        "src.application",
        "src.adapters",
    ],
    # Tầng Utils: Tiện ích thuần túy, không phụ thuộc các domain nghiệp vụ hay UI
    "src.utils": [
        "src.data",
        "src.models",
        "src.training",
        "src.generation",
        "src.ui",
        "src.application",
        "src.adapters",
        "src.inference",
    ],
    # Inference is an inner runtime capability assembled from data/model/generation modules.
    "src.inference": [
        "src.training",
        "src.ui",
        "src.application",
        "src.adapters",
    ],
    # Application orchestrates inner capabilities but never knows transport/UI adapters.
    "src.application": ["src.ui", "src.adapters"],
    # UI is an outer adapter: it may depend on application/adapters, never inner capabilities.
    "src.ui": [
        "src.core",
        "src.data",
        "src.models",
        "src.training",
        "src.generation",
        "src.utils",
        "src.inference",
    ],
    # Adapters are outer I/O implementations. Capability bypasses are forbidden below.
    "src.adapters": [
        "src.data",
        "src.models",
        "src.training",
        "src.generation",
        "src.inference",
        "src.utils",
    ],
}

# Application can depend on capability contracts only through these stable public facades.
FACADE_ONLY_DEPENDENCIES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "src.training": {
        "src.data": ("src.data.api",),
        "src.models": ("src.models.api",),
        "src.generation": ("src.generation.api",),
    },
    "src.inference": {
        "src.data": ("src.data.api",),
        "src.models": ("src.models.api",),
        "src.generation": ("src.generation.api",),
    },
    "src.application": {
        "src.data": ("src.data.api",),
        "src.models": ("src.models.api",),
        "src.training": ("src.training.api",),
        "src.generation": ("src.generation.api",),
        "src.inference": ("src.inference.api",),
    },
    # Adapters may use stable domain/config error contracts, but no core mechanics.
    "src.adapters": {
        "src.core": ("src.core.config", "src.core.exceptions"),
    },
}


def get_module_path(filepath: str, root_dir: Optional[str] = None) -> str:
    """Chuyển đổi đường dẫn file thành tên module Python dạng dot-separated."""
    abs_path = os.path.abspath(filepath)
    if root_dir is not None:
        try:
            rel_path = os.path.relpath(abs_path, os.path.abspath(root_dir))
        except ValueError:
            rel_path = abs_path
    else:
        norm_path = abs_path.replace("\\", "/")
        if "/src/" in norm_path:
            idx = norm_path.rfind("/src/")
            rel_path = norm_path[idx + 1 :]
        elif norm_path.endswith("/src"):
            rel_path = "src"
        else:
            try:
                rel_path = os.path.relpath(abs_path, os.path.abspath("."))
            except ValueError:
                rel_path = abs_path

    rel_path = os.path.splitext(rel_path)[0]
    parts = rel_path.replace("\\", "/").split("/")
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(p for p in parts if p)


def extract_imports_from_file(
    filepath: str, source_module: Optional[str] = None
) -> List[Tuple[int, str]]:
    """Trích xuất import và resolve relative import theo module nguồn khi có thể."""
    imports: List[Tuple[int, str]] = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
    except Exception as e:
        print(f"Lỗi cú pháp khi phân tích AST file {filepath}: {e}")
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level > 0:
                if not source_module:
                    continue
                package = (
                    source_module
                    if os.path.basename(filepath) == "__init__.py"
                    else source_module.rpartition(".")[0]
                )
                package_parts = [p for p in package.split(".") if p]
                keep = len(package_parts) - (node.level - 1)
                if keep < 0:
                    continue
                base_parts = package_parts[:keep]
                if module:
                    base_parts.extend(module.split("."))
                module = ".".join(base_parts)
            imports.append((node.lineno, module))
            for alias in node.names:
                imports.append((node.lineno, f"{module}.{alias.name}" if module else alias.name))

    return imports


def check_architecture_boundaries(
    source_dir: str = "src", root_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Quét toàn bộ thư mục nguồn và kiểm tra ranh giới phụ thuộc kiến trúc."""
    violations: List[Dict[str, Any]] = []

    if root_dir is None:
        abs_src = os.path.abspath(source_dir)
        if os.path.basename(abs_src) == "src":
            root_dir = os.path.dirname(abs_src)
        else:
            root_dir = abs_src

    for root, _, files in os.walk(source_dir):
        for file in files:
            if not file.endswith(".py"):
                continue

            filepath = os.path.join(root, file)
            source_module = get_module_path(filepath, root_dir=root_dir)

            # Tìm xem source_module thuộc nhóm quy tắc nào
            matched_rule_source = None
            matching_rules = [
                rule_src
                for rule_src in FORBIDDEN_DEPENDENCIES
                if source_module == rule_src or source_module.startswith(rule_src + ".")
            ]
            if matching_rules:
                matched_rule_source = max(matching_rules, key=len)

            if not matched_rule_source:
                continue

            forbidden_targets = FORBIDDEN_DEPENDENCIES[matched_rule_source]
            imports = extract_imports_from_file(filepath, source_module=source_module)

            seen_violations = set()
            for lineno, target_module in imports:
                for forbidden in forbidden_targets:
                    if target_module == forbidden or target_module.startswith(forbidden + "."):
                        violation_key = (lineno, forbidden)
                        if violation_key in seen_violations:
                            continue
                        seen_violations.add(violation_key)
                        violations.append(
                            {
                                "filepath": filepath,
                                "lineno": lineno,
                                "source_module": source_module,
                                "rule_scope": matched_rule_source,
                                "target_module": target_module,
                                "forbidden_rule": forbidden,
                                "reason": f"Module '{matched_rule_source}' không được phép phụ thuộc vào '{forbidden}' (Vi phạm Dependency Inversion / Clean Architecture).",
                            }
                        )

                facade_rules = FACADE_ONLY_DEPENDENCIES.get(matched_rule_source, {})
                for capability_root, allowed_prefixes in facade_rules.items():
                    if not (
                        target_module == capability_root
                        or target_module.startswith(capability_root + ".")
                    ):
                        continue
                    if any(
                        target_module == allowed or target_module.startswith(allowed + ".")
                        for allowed in allowed_prefixes
                    ):
                        continue
                    violation_key = (lineno, f"{capability_root}.* via public facade")
                    if violation_key in seen_violations:
                        continue
                    seen_violations.add(violation_key)
                    violations.append(
                        {
                            "filepath": filepath,
                            "lineno": lineno,
                            "source_module": source_module,
                            "rule_scope": matched_rule_source,
                            "target_module": target_module,
                            "forbidden_rule": capability_root,
                            "reason": (
                                f"Module '{matched_rule_source}' chỉ được phép phụ thuộc vào "
                                f"public facade {allowed_prefixes} của '{capability_root}', không phải implementation nội bộ."
                            ),
                        }
                    )

    return violations


def main() -> int:
    """Hàm thực thi chính cho Architecture Checker CLI."""
    violations = check_architecture_boundaries("src")

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console(legacy_windows=False)
        console.print()

        if not violations:
            console.print(
                Panel(
                    "[bold green]✅ RANH GIỚI PHỤ THUỘC ĐÃ CẤU HÌNH: PASS[/bold green]\n"
                    "Không phát hiện vi phạm nào đối với ma trận dependency hiện tại!",
                    title="🏛️ ARCHITECTURE GUARDIAN",
                    border_style="green",
                )
            )
            console.print()
            return 0

        console.print(
            Panel(
                f"[bold red]❌ PHÁT HIỆN {len(violations)} LỖI VI PHẠM RANH GIỚI KIẾN TRÚC![/bold red]\n"
                "Mã nguồn đang có các câu lệnh import vi phạm cấu trúc Modular Monolith.",
                title="🏛️ ARCHITECTURE GUARDIAN VIOLATION",
                border_style="red",
            )
        )

        table = Table(
            title="Danh Sách Vi Phạm Kiến Trúc", show_header=True, header_style="bold red"
        )
        table.add_column("File & Dòng", style="cyan")
        table.add_column("Module Hiện Tại", style="yellow")
        table.add_column("Import Bị Cấm", style="red bold")
        table.add_column("Lý Do Vi Phạm", style="white")

        for v in violations:
            table.add_row(
                f"{v['filepath']}:{v['lineno']}",
                v["source_module"],
                v["target_module"],
                v["reason"],
            )

        console.print(table)
        console.print()
        return 1

    except ImportError:
        if not violations:
            print("✅ ARCHITECTURE CHECK: PASS (0 violations)")
            return 0

        print(f"❌ ARCHITECTURE CHECK: FAIL ({len(violations)} violations)")
        for v in violations:
            print(
                f"  - {v['filepath']}:{v['lineno']} in {v['source_module']} imports {v['target_module']}"
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
