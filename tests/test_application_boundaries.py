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


def test_application_runtime_service_configures_logging_from_canonical_config(monkeypatch):
    from src.core.config import EngineConfig

    captured = {}

    def fake_configure(system_config, name="ai-train", **kwargs):
        captured["system_config"] = system_config
        captured["name"] = name
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(
        "src.application.runtime.service.configure_logging_from_system",
        fake_configure,
    )
    from src.application.runtime.service import ApplicationRuntimeService

    config = EngineConfig()
    ApplicationRuntimeService.configure_logging(config, name="cli")

    assert captured["system_config"] is config.system
    assert captured["name"] == "cli"


def test_diagnostics_application_owns_cli_vram_rendering(tmp_path, monkeypatch):
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
        "src.application.diagnostics.service.print_vram_scenarios_table",
        lambda value: captured.setdefault("value", value),
    )

    service.print_scenarios_from_config(None)

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
            events.append(("prepare", device))

    class FakeTraining:
        def start_training(self, *, plan):
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
            del device

    class FakeTraining:
        def start_training(self, *, plan):
            del plan
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
