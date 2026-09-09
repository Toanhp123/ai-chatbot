from pathlib import Path
from typing import cast

from scripts.check_architecture import check_architecture_boundaries


def test_application_config_provider_owns_default_source_and_returns_isolated_snapshots(tmp_path):
    from src.adapters.config.yaml_provider import YamlConfigProvider
    from src.application.config import ConfigRequest, ConfigurationService

    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    path = config_dir / "engine.yaml"
    path.write_text("training:\n  batch_size: 7\n", encoding="utf-8")

    provider = YamlConfigProvider(default_path=str(path))
    service = ConfigurationService(provider)

    first = service.resolve(ConfigRequest())
    second = service.resolve(ConfigRequest(overrides=("training.batch_size=9",)))

    assert first.training.batch_size == 7
    assert second.training.batch_size == 9
    assert first.training.batch_size == 7
    assert service.default_path == str(path)


def test_config_snapshot_is_detached_from_caller_mutation(tmp_path):
    from src.adapters.config.yaml_provider import YamlConfigProvider
    from src.application.config import ConfigRequest, ConfigurationService

    path = tmp_path / "engine.yaml"
    path.write_text("model:\n  vocab_size: 129\n", encoding="utf-8")
    service = ConfigurationService(YamlConfigProvider(default_path=str(path)))
    original = service.resolve(ConfigRequest())
    snapshot = service.snapshot(original)

    original.model.vocab_size = 999

    assert snapshot.model.vocab_size == 129


def test_architecture_guardian_enforces_layer_direction(tmp_path):
    src = tmp_path / "src"
    (src / "core").mkdir(parents=True)
    (src / "application").mkdir(parents=True)
    (src / "ui").mkdir(parents=True)
    for folder in (src, src / "core", src / "application", src / "ui"):
        (folder / "__init__.py").write_text("", encoding="utf-8")

    (src / "core" / "bad.py").write_text(
        "from src.application.config import ConfigurationService\n", encoding="utf-8"
    )
    (src / "application" / "bad.py").write_text(
        "from src.ui.app import create_app\n", encoding="utf-8"
    )

    violations = check_architecture_boundaries(str(src))
    pairs = {(v["rule_scope"], v["forbidden_rule"]) for v in violations}

    assert ("src.core", "src.application") in pairs
    assert ("src.application", "src.ui") in pairs


def test_main_cli_does_not_import_inner_modules_directly():
    source = Path("main.py").read_text(encoding="utf-8")
    forbidden = (
        "from src.core",
        "from src.data",
        "from src.models",
        "from src.training",
        "from src.generation",
        "from src.utils",
    )
    assert not any(token in source for token in forbidden)


def test_generation_session_exposes_transport_neutral_events():
    import threading

    from src.application.inference.session import GenerationSession
    from src.core.config import GenerationConfig
    from src.generation.base import BaseGenerator, GenerationOutput

    class FakeGenerator:
        def generate(self, prompt, config, streamer, return_output, **kwargs):
            del config, return_output, kwargs
            streamer.on_token("X")
            return GenerationOutput(
                text=prompt + "X",
                prompt=prompt,
                generated_text="X",
                token_ids=[1],
                tokens_generated=1,
                elapsed_time_sec=0.01,
                tokens_per_second=100.0,
                finish_reason="length",
                prompt_tokens_input=1,
                prompt_tokens_used=1,
                prompt_truncated=False,
            )

    session = GenerationSession(
        generator_provider=lambda: cast(BaseGenerator, FakeGenerator()),
        prompt="A",
        config=GenerationConfig(max_new_tokens=1),
        execution_lock=threading.Lock(),
        release_admission=lambda: None,
    )

    events = list(session.iter_events())

    assert [event["type"] for event in events] == ["start", "token", "done"]
    assert events[-1]["full_text"] == "AX"


def test_cli_diagnostics_adapter_owns_vram_rendering(tmp_path, monkeypatch):
    from src.adapters.cli.diagnostics import print_scenarios
    from src.adapters.config import YamlConfigProvider
    from src.application.config import ConfigurationService
    from src.application.diagnostics import DiagnosticsApplicationService

    path = tmp_path / "engine.yaml"
    path.write_text("system:\n  device: cpu\n", encoding="utf-8")
    service = DiagnosticsApplicationService(
        ConfigurationService(YamlConfigProvider(default_path=str(path)))
    )
    scenarios = {"scenarios": [], "recommended": None}
    captured = {}
    monkeypatch.setattr(
        "src.application.diagnostics.service.analyze_vram_scenarios",
        lambda **kwargs: scenarios,
    )
    monkeypatch.setattr(
        "src.adapters.cli.diagnostics.print_vram_scenarios_table",
        lambda value: captured.setdefault("value", value),
    )

    print_scenarios(service, None)

    assert captured["value"] is scenarios


def test_cli_config_arguments_delegate_default_source_to_config_provider():
    from main import build_parser

    parser = build_parser()

    assert parser.parse_args(["train"]).config is None
    assert parser.parse_args(["estimate"]).config is None
    assert parser.parse_args(["inspect"]).config is None


def test_main_cli_checkpoint_loading_is_application_owned():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "torch.load" not in source
    assert "ModelRegistry" not in source
    assert "load_tokenizer" not in source
    assert "get_generator" not in source
    assert "Trainer(" not in source


def test_web_adapters_do_not_import_inner_modules_directly():
    forbidden = (
        "from src.core",
        "from src.data",
        "from src.models",
        "from src.training",
        "from src.generation",
        "from src.utils",
    )
    violations = []
    for path in Path("src/ui").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in forbidden):
            violations.append(str(path))
    assert violations == []


def test_inference_preferences_follow_shared_configuration_authority_without_reapply(tmp_path):
    from src.adapters.config import YamlConfigProvider
    from src.application.config import ConfigurationService
    from src.application.inference import InferenceService
    from src.core.config import EngineConfig

    path = tmp_path / "engine.yaml"
    path.write_text("system:\n  device: cpu\n", encoding="utf-8")
    config_service = ConfigurationService(YamlConfigProvider(default_path=str(path)))
    initial = EngineConfig().copy(
        system=EngineConfig().system.copy(device="cpu"),
        data=EngineConfig().data.copy(vocab_file="data/first.json"),
        training=EngineConfig().training.copy(
            checkpoint_dir="checkpoints/first",
            checkpoint_name="first.pt",
        ),
    )
    config_service.activate(initial)
    service = InferenceService.from_engine_config(initial, config_service=config_service)

    updated = initial.copy(
        system=initial.system.copy(device="cuda"),
        data=initial.data.copy(vocab_file="data/second.json"),
        training=initial.training.copy(
            checkpoint_dir="checkpoints/second",
            checkpoint_name="second.pt",
        ),
    )
    config_service.activate(updated)

    assert service.checkpoint_dir == "checkpoints/second"
    assert service.checkpoint_name == "second.pt"
    assert service.vocab_path == "data/second.json"
    assert service.configured_device == "cuda"


def test_inference_preferences_are_not_stored_as_parallel_shadow_fields(tmp_path):
    from src.application.inference import InferenceService

    service = InferenceService(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        vocab_path=str(tmp_path / "missing.json"),
        device="cpu",
    )

    shadow_fields = {
        "checkpoint_dir",
        "checkpoint_name",
        "vocab_path",
        "configured_device",
        "default_generation_config",
    }
    assert shadow_fields.isdisjoint(service.__dict__)


def test_cli_generate_defaults_are_delegated_to_canonical_config():
    from main import build_parser

    args = build_parser().parse_args(["generate"])

    assert args.config is None
    assert args.checkpoint is None
    assert args.vocab is None
    assert args.tokens is None
    assert args.temp is None
    assert args.top_k is None
    assert args.top_p is None
    assert args.min_p is None
    assert args.repetition_penalty is None
    assert args.greedy is None
    assert args.no_cache is None


def _make_training_launch_plan():
    from src.application.training.contracts import TrainingFeasibility, TrainingPlan
    from src.core.config import EngineConfig
    from src.core.runtime import RuntimeCapabilities, resolve_training_plan

    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cpu"))
    runtime_plan = resolve_training_plan(
        config,
        capabilities=RuntimeCapabilities(
            cuda_available=False,
            mps_available=False,
            bf16_supported=False,
            bitsandbytes_available=False,
        ),
    )
    return TrainingPlan(
        requested_config=config,
        config=config,
        runtime_plan=runtime_plan,
        feasibility=TrainingFeasibility(
            feasible=True,
            message="ok",
            estimated_gb=0.0,
            estimated_mb=0.0,
        ),
    )


def test_training_launch_application_commits_config_only_after_background_start():
    from src.application.training.launch import TrainingLaunchApplicationService

    plan = _make_training_launch_plan()
    config = plan.requested_config
    events = []

    class FakeInference:
        def prepare_for_training(self, device):
            from src.application.inference import InferenceTrainingHandoff

            events.append(("prepare", device))
            return InferenceTrainingHandoff()

    class FakeTraining:
        def start_training(self, *, plan, admission_reserved=False):
            assert admission_reserved is False
            events.append(("start", plan))

    class FakeConfig:
        def activate(self, value):
            events.append(("activate", value))

    TrainingLaunchApplicationService(
        training_service=FakeTraining(),
        inference_service=FakeInference(),
        config_service=FakeConfig(),
    ).start(plan)

    assert events == [
        ("prepare", "cpu"),
        ("start", plan),
        ("activate", config),
    ]


def test_training_launch_application_does_not_activate_config_when_start_fails():
    import pytest

    from src.application.training.launch import TrainingLaunchApplicationService

    activated = []
    plan = _make_training_launch_plan()

    class FakeInference:
        def prepare_for_training(self, device):
            from src.application.inference import InferenceTrainingHandoff

            del device
            return InferenceTrainingHandoff()

    class FakeTraining:
        def start_training(self, *, plan, admission_reserved=False):
            del plan, admission_reserved
            raise RuntimeError("busy")

    class FakeConfig:
        def activate(self, value):
            activated.append(value)

    with pytest.raises(RuntimeError, match="busy"):
        TrainingLaunchApplicationService(
            training_service=FakeTraining(),
            inference_service=FakeInference(),
            config_service=FakeConfig(),
        ).start(plan)

    assert activated == []


def test_ui_adapters_do_not_manually_sync_inference_config():
    for path in Path("src/ui/routes").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "apply_engine_config" not in source, str(path)


def test_inference_construction_does_not_overwrite_shared_canonical_config(tmp_path):
    from src.adapters.config import YamlConfigProvider
    from src.application.config import ConfigurationService
    from src.application.inference import InferenceService
    from src.core.config import EngineConfig

    path = tmp_path / "engine.yaml"
    path.write_text("system:\n  device: cpu\n", encoding="utf-8")
    config_service = ConfigurationService(YamlConfigProvider(default_path=str(path)))
    base = EngineConfig()
    canonical = base.copy(
        system=base.system.copy(device="cpu", seed=9876),
        data=base.data.copy(
            source_url="https://example.test/corpus.txt",
            split_ratio=0.73,
            cleaner_type="none",
            vocab_file=str(tmp_path / "vocab.json"),
        ),
        model=base.model.copy(n_layer=7, n_embd=256, n_head=8),
        training=base.training.copy(
            batch_size=3,
            max_iters=77,
            checkpoint_dir=str(tmp_path / "checkpoints"),
            checkpoint_name="custom.pt",
        ),
        generation=base.generation.copy(max_new_tokens=123),
    )
    config_service.activate(canonical)

    InferenceService.from_engine_config(canonical, config_service=config_service)

    assert config_service.current().to_dict() == canonical.to_dict()


def test_training_launch_rolls_back_inference_handoff_when_background_start_fails():
    import pytest

    from src.application.training.launch import TrainingLaunchApplicationService

    plan = _make_training_launch_plan()
    events = []

    from src.application.inference import InferenceTrainingHandoff

    class FakeInference:
        def prepare_for_training(self, device):
            events.append(("prepare", device))
            return InferenceTrainingHandoff(
                training_admission_reserved=True,
                rollback=lambda: events.append("rollback"),
            )

    class FakeTraining:
        def start_training(self, *, plan, admission_reserved=False):
            events.append(("start", admission_reserved))
            raise RuntimeError("busy")

    class FakeConfig:
        def activate(self, value):
            events.append(("activate", value))

    with pytest.raises(RuntimeError, match="busy"):
        TrainingLaunchApplicationService(
            training_service=FakeTraining(),
            inference_service=FakeInference(),
            config_service=FakeConfig(),
        ).start(plan)

    assert events == [("prepare", "cpu"), ("start", True), "rollback"]


def test_training_launch_start_command_owns_resume_revision_pinning(tmp_path):
    from src.application.inference import InferenceTrainingHandoff
    from src.application.training import TrainingCommand
    from src.application.training.launch import TrainingLaunchApplicationService

    base_plan = _make_training_launch_plan()
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    checkpoint = checkpoint_dir / "resume.pt"
    checkpoint.write_bytes(b"pinned")
    captured = {}

    class FakeTrainingApplication:
        def plan(self, command):
            captured["command"] = command
            return base_plan

    class FakeInference:
        def prepare_for_training(self, device):
            return InferenceTrainingHandoff()

    class FakeTraining:
        def start_training(self, *, plan, admission_reserved=False):
            captured["plan"] = plan

    class FakeConfig:
        def activate(self, config):
            captured["active"] = config

    def resolve_resume(path, root):
        captured["resolve"] = (path, root)
        return str(checkpoint)

    service = TrainingLaunchApplicationService(
        training_service=FakeTraining(),
        inference_service=FakeInference(),
        config_service=FakeConfig(),
        training_application=FakeTrainingApplication(),
    )

    result = service.start_command(
        TrainingCommand(),
        resume_checkpoint="resume.pt",
        resume_path_resolver=resolve_resume,
    )

    assert captured["resolve"] == (
        "resume.pt",
        base_plan.requested_config.training.checkpoint_dir,
    )
    assert result.resume_checkpoint == str(checkpoint)
    assert result.resume_checkpoint_identity is not None
    assert captured["plan"] == result


def test_training_run_factory_requires_application_resolved_runtime_plan():
    import inspect

    from src.application.training import TrainingRunFactory

    parameter = inspect.signature(TrainingRunFactory.prepare).parameters["runtime_plan"]
    assert parameter.default is inspect.Parameter.empty


def test_application_cleaner_policy_owns_gemini_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from src.application.data_policy import build_application_cleaner

    cleaner = build_application_cleaner(
        "gemini",
        clean_line_numbers=True,
        cache_dir=str(tmp_path / "gemini-app-policy"),
    )

    cleaned = cleaner("1.. Trăm năm trong cõi người ta")
    assert "1.." not in cleaned
    assert "Trăm năm trong cõi người ta" in cleaned


def test_cli_runtime_adapter_configures_logging_without_application_wrapper(monkeypatch):
    from src.core.config import EngineConfig

    captured = {}

    def fake_configure(system_config, name="ai-train", **kwargs):
        captured["system_config"] = system_config
        captured["name"] = name
        return object()

    monkeypatch.setattr("src.adapters.cli.runtime.configure_logging_from_system", fake_configure)
    from src.adapters.cli.runtime import configure_cli_logging

    config = EngineConfig()
    configure_cli_logging(config, name="cli")

    assert captured == {"system_config": config.system, "name": "cli"}


def test_diagnostics_application_exposes_data_not_cli_rendering():
    from src.application.diagnostics import DiagnosticsApplicationService

    assert not hasattr(DiagnosticsApplicationService, "print_scenarios_from_config")
    assert not hasattr(DiagnosticsApplicationService, "print_inspect")
    assert not hasattr(DiagnosticsApplicationService, "print_system_report")
    assert not hasattr(DiagnosticsApplicationService, "run_quality_gates_cli")


def test_legacy_application_runtime_wrapper_module_is_removed():
    assert not Path("src/application/runtime/service.py").exists()


def test_main_cli_uses_outer_runtime_and_diagnostics_renderers():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "ApplicationRuntimeService" not in source
    assert ".print_scenarios_from_config(" not in source
    assert ".print_inspect(" not in source
    assert ".print_system_report(" not in source
    assert ".run_quality_gates_cli(" not in source


def test_background_training_service_consumes_only_preplanned_training_plan():
    import inspect

    from src.application.training.background import TrainingService

    parameters = inspect.signature(TrainingService.start_training).parameters
    assert tuple(parameters) == ("self", "plan", "admission_reserved")
    assert parameters["plan"].default is inspect.Parameter.empty


def test_diagnostics_application_does_not_own_outer_tooling_or_log_file_io():
    source = Path("src/application/diagnostics/service.py").read_text(encoding="utf-8")

    assert "scripts.check_all" not in source
    assert "def run_quality_gates" not in source
    assert "def logs" not in source


def test_application_error_facade_exports_only_outer_contract_without_wildcard():
    source = Path("src/application/errors.py").read_text(encoding="utf-8")

    assert "import *" not in source
    from src.application import errors

    assert set(errors.__all__) == {"AIEngineError", "ConfigurationError", "ErrorCode"}
