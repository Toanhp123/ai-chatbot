import json

from src.core.config.model import ModelConfig
from src.core.config.system import SystemConfig
from src.core.config.training import TrainingConfig
from src.core.diagnostics import (
    DiagnosticReport,
    DiagnosticsRunner,
    DiagnosticStatus,
    analyze_vram_scenarios,
    calculate_approx_transformer_params,
    check_attention_backends,
    check_bf16_support,
    check_hardware_and_environment,
    check_memory_feasibility,
    estimate_vram_budget,
    export_diagnostic_json,
    get_cpu_info,
    get_disk_info,
    get_gpu_info,
    get_hardware_recommendations,
    get_memory_info,
    get_system_info,
    print_vram_scenarios_table,
    verify_directories,
    verify_directory_permissions,
)


def test_system_info_collector():
    info = get_system_info()
    assert "os_platform" in info
    assert "python_version" in info
    assert "pytorch_version" in info
    assert "packages" in info
    assert "torch" in info["packages"]
    assert "environment_variables" in info


def test_hardware_info_collector():
    cpu = get_cpu_info()
    assert cpu["logical_cores"] >= 1
    assert cpu["physical_cores"] >= 1

    mem = get_memory_info()
    assert mem["total_gb"] > 0
    assert mem["available_gb"] >= 0

    gpu = get_gpu_info()
    assert "cuda_available" in gpu
    assert "device_count" in gpu
    assert isinstance(gpu["devices"], list)


def test_storage_and_permissions(tmp_path):
    disk = get_disk_info(str(tmp_path))
    assert disk["total_gb"] > 0
    assert disk["free_gb"] > 0

    sub_dir = tmp_path / "test_diag_dir"
    perms = verify_directory_permissions([str(sub_dir)])
    assert str(sub_dir) in perms
    assert perms[str(sub_dir)]["writable"] is True
    assert perms[str(sub_dir)]["readable"] is True

    # Test verify_directories
    assert verify_directories([str(sub_dir)]) is True


def test_vram_estimator():
    model_cfg = ModelConfig(
        name="minigpt",
        vocab_size=128,
        block_size=128,
        n_layer=4,
        n_head=4,
        n_embd=128,
    )
    train_cfg = TrainingConfig(
        batch_size=32,
        learning_rate=3e-4,
        max_iters=100,
    )

    budget = estimate_vram_budget(model_config=model_cfg, training_config=train_cfg)
    assert budget["total_parameters"] > 0
    assert budget["total_estimated_mb"] > 0
    assert "parameters" in budget["components_mb"]
    assert "gradients" in budget["components_mb"]
    assert "optimizer_states" in budget["components_mb"]
    assert "activations" in budget["components_mb"]
    assert "cuda_context_overhead" in budget["components_mb"]

    feasible, msg, _ = check_memory_feasibility(
        model_config=model_cfg,
        training_config=train_cfg,
        available_vram_gb=4.0,
    )

    assert feasible is True
    assert "đủ an toàn" in msg

    # Kiểm tra trường hợp vượt quá VRAM
    not_feasible, msg_fail, _ = check_memory_feasibility(
        model_config=model_cfg,
        training_config=train_cfg,
        available_vram_gb=0.1,  # Cố tình đặt rất thấp
        safety_margin_gb=0.5,
    )
    assert not_feasible is False
    assert "CẢNH BÁO" in msg_fail


def test_diagnostics_runner_and_report():
    runner = DiagnosticsRunner()
    report = runner.run(test_tensor_allocation=False)

    assert isinstance(report, DiagnosticReport)
    assert report.status in (
        DiagnosticStatus.HEALTHY,
        DiagnosticStatus.WARNING,
        DiagnosticStatus.CRITICAL,
    )
    assert "os_platform" in report.system
    assert "cpu" in report.hardware
    assert "free_gb" in report.storage

    data = report.to_dict()
    assert data["status"] in ("HEALTHY", "WARNING", "CRITICAL")
    assert isinstance(data["warnings"], list)


def test_export_diagnostic_json(tmp_path):
    runner = DiagnosticsRunner()
    report = runner.run(test_tensor_allocation=False)

    json_path = tmp_path / "diagnostics_report.json"
    export_diagnostic_json(report, str(json_path))

    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert "status" in loaded
    assert "system" in loaded
    assert "hardware" in loaded


def test_backward_compatibility():
    legacy_report = check_hardware_and_environment()
    assert "os" in legacy_report
    assert "python_version" in legacy_report
    assert "pytorch_version" in legacy_report
    assert "cuda_available" in legacy_report
    assert "vram_total_gb" in legacy_report
    assert "vram_free_gb" in legacy_report
    assert "disk_free_gb" in legacy_report
    assert legacy_report["status"] in ("PASS", "WARN", "FAIL")


def test_weight_tying_parameter_calculation():
    params_tied = calculate_approx_transformer_params(
        vocab_size=1000,
        block_size=256,
        n_layer=4,
        n_head=4,
        n_embd=128,
        tie_word_embeddings=True,
    )
    params_untied = calculate_approx_transformer_params(
        vocab_size=1000,
        block_size=256,
        n_layer=4,
        n_head=4,
        n_embd=128,
        tie_word_embeddings=False,
    )
    # Khác biệt đúng bằng vocab_size * n_embd (1000 * 128 = 128,000)
    assert params_untied - params_tied == 1000 * 128


def test_bf16_and_sdpa_backend_detection():
    bf16_ok = check_bf16_support()
    assert isinstance(bf16_ok, bool)

    backends = check_attention_backends()
    assert "flash_attention" in backends
    assert "memory_efficient" in backends
    assert "math_attention" in backends

    recs = get_hardware_recommendations("7.5", 6.0)
    assert "recommended_precision" in recs
    assert "recommended_batch_size" in recs
    assert "gradient_checkpointing" in recs


def test_gradient_checkpointing_vram_reduction():
    model_cfg = ModelConfig(vocab_size=500, block_size=256, n_layer=6, n_head=4, n_embd=128)
    train_cfg = TrainingConfig(batch_size=32)

    budget_standard = estimate_vram_budget(
        model_config=model_cfg, training_config=train_cfg, gradient_checkpointing=False
    )
    budget_checkpointed = estimate_vram_budget(
        model_config=model_cfg, training_config=train_cfg, gradient_checkpointing=True
    )

    act_std = budget_standard["components_mb"]["activations"]
    act_cp = budget_checkpointed["components_mb"]["activations"]
    assert act_cp < act_std
    assert budget_checkpointed["total_estimated_mb"] < budget_standard["total_estimated_mb"]


def test_multi_scenario_vram_analysis():
    model_cfg = ModelConfig(vocab_size=500, block_size=128, n_layer=4, n_head=4, n_embd=128)
    train_cfg = TrainingConfig(batch_size=16)

    res = analyze_vram_scenarios(
        model_config=model_cfg, training_config=train_cfg, available_vram_gb=6.0
    )
    assert "scenarios" in res
    assert len(res["scenarios"]) == 4
    assert res["recommended"] is not None
    assert res["recommended"]["feasible"] is True

    # Test in bảng kịch bản không phát sinh ngoại lệ
    print_vram_scenarios_table(res)


def test_vram_scenarios_respect_explicit_cpu_runtime() -> None:
    model_cfg = ModelConfig(vocab_size=500, block_size=128, n_layer=2, n_head=4, n_embd=128)
    train_cfg = TrainingConfig(batch_size=16)

    res = analyze_vram_scenarios(
        model_config=model_cfg,
        training_config=train_cfg,
        system_config=SystemConfig(device="cpu"),
        available_vram_gb=0.01,
    )

    assert all(item["effective_device"] == "cpu" for item in res["scenarios"])
    assert all(item["feasible"] is True for item in res["scenarios"])


def test_architecture_aware_parameter_estimator_matches_minigpt_model() -> None:
    from src.core.diagnostics.estimator import calculate_model_params
    from src.models.registry import ModelRegistry

    config = ModelConfig(
        name="minigpt",
        vocab_size=257,
        block_size=96,
        n_embd=96,
        n_head=6,
        n_layer=3,
        bias=True,
        tie_word_embeddings=False,
    )
    config.validate()
    model = ModelRegistry.create(config.name, config)

    assert calculate_model_params(config) == sum(p.numel() for p in model.parameters())


def test_architecture_aware_parameter_estimator_matches_llama_custom_mlp() -> None:
    from src.core.diagnostics.estimator import calculate_model_params
    from src.models.registry import ModelRegistry

    config = ModelConfig(
        name="llama",
        vocab_size=257,
        block_size=96,
        n_embd=96,
        n_head=6,
        n_layer=3,
        bias=True,
        tie_word_embeddings=False,
        model_kwargs={"intermediate_size": 1024, "multiple_of": 64},
    )
    config.validate()
    model = ModelRegistry.create(config.name, config)

    assert calculate_model_params(config) == sum(p.numel() for p in model.parameters())


def test_vram_estimator_uses_runtime_micro_batch_semantics() -> None:
    model_cfg = ModelConfig(n_embd=96, n_head=6, n_layer=2, block_size=64)
    train_cfg = TrainingConfig(batch_size=16, gradient_accumulation_steps=4)

    budget = estimate_vram_budget(model_config=model_cfg, training_config=train_cfg)

    assert budget["micro_batch_size"] == 16
    assert budget["effective_batch_size"] == 64
    assert budget["gradient_accumulation_steps"] == 4


def test_vram_estimator_uses_training_config_runtime_fields_by_default() -> None:
    model_cfg = ModelConfig(n_embd=96, n_head=6, n_layer=2, block_size=64)
    train_cfg = TrainingConfig(
        batch_size=8,
        precision="amp_fp16",
        optimizer_type="sgd",
        gradient_checkpointing=True,
    )

    budget = estimate_vram_budget(model_config=model_cfg, training_config=train_cfg)

    assert budget["requested_precision"] == "amp_fp16"
    assert budget["requested_optimizer_type"] == "sgd"
    assert budget["gradient_checkpointing"] is True


def test_memory_probe_failure_is_explicit_not_fake_zero(monkeypatch) -> None:
    import sys

    class BrokenPsutil:
        @staticmethod
        def virtual_memory():
            raise OSError("memory probe failed")

    monkeypatch.setitem(sys.modules, "psutil", BrokenPsutil())

    info = get_memory_info()

    assert info["probe"]["status"] == "FAILED"
    assert info["total_gb"] is None
    assert info["available_gb"] is None
    assert "memory probe failed" in info["probe"]["error"]


def test_disk_probe_failure_is_explicit_not_fake_zero(monkeypatch) -> None:
    import src.core.diagnostics.storage as storage

    def broken_disk_usage(path: str):
        raise OSError(f"cannot stat {path}")

    monkeypatch.setattr(storage.shutil, "disk_usage", broken_disk_usage)

    info = get_disk_info(".")

    assert info["probe"]["status"] == "FAILED"
    assert info["total_gb"] is None
    assert info["free_gb"] is None
    assert "cannot stat" in info["probe"]["error"]


def test_runner_does_not_turn_failed_capacity_probe_into_low_capacity_warning(monkeypatch) -> None:
    import src.core.diagnostics.runner as runner_module

    failed_probe = {"status": "FAILED", "error": "probe unavailable", "value": None}
    monkeypatch.setattr(
        runner_module,
        "get_disk_info",
        lambda path: {
            "path": path,
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
            "percent_used": None,
            "probe": failed_probe,
        },
    )
    monkeypatch.setattr(
        runner_module,
        "get_memory_info",
        lambda: {
            "total_gb": None,
            "available_gb": None,
            "used_gb": None,
            "percent_used": None,
            "probe": failed_probe,
        },
    )
    monkeypatch.setattr(
        runner_module,
        "get_gpu_info",
        lambda: {
            "cuda_available": False,
            "device_count": 0,
            "devices": [],
            "primary_gpu": None,
            "recommendations": {},
        },
    )
    monkeypatch.setattr(
        runner_module,
        "verify_directory_permissions",
        lambda paths: {p: {"exists": True, "readable": True, "writable": True} for p in paths},
    )

    report = runner_module.DiagnosticsRunner().run(test_tensor_allocation=False)

    assert not any("Dung lượng đĩa trống cực thấp" in warning for warning in report.warnings)
    assert not any("RAM hệ thống khả dụng dưới" in warning for warning in report.warnings)
    assert any("Không thể đo dung lượng đĩa" in warning for warning in report.warnings)
    assert any("Không thể đo dung lượng RAM" in warning for warning in report.warnings)


def test_reporter_accepts_failed_capacity_probes_without_numeric_coercion() -> None:
    from src.core.diagnostics.reporter import print_diagnostic_report
    from src.core.diagnostics.runner import DiagnosticReport, DiagnosticStatus

    failed_probe = {"status": "FAILED", "error": "probe unavailable", "value": None}
    report = DiagnosticReport(
        status=DiagnosticStatus.WARNING,
        system={},
        hardware={
            "cpu": {},
            "memory": {
                "total_gb": None,
                "available_gb": None,
                "percent_used": None,
                "probe": failed_probe,
            },
            "gpu": {"cuda_available": False, "devices": []},
        },
        storage={
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
            "percent_used": None,
            "probe": failed_probe,
        },
        permissions={},
    )

    print_diagnostic_report(report)
