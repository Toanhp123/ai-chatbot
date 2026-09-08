import pytest

from src.core.config import (
    BaseConfig,
    DataConfig,
    EngineConfig,
    GenerationConfig,
    ModelConfig,
    TrainingConfig,
    apply_overrides,
    interpolate_env_vars,
)
from src.core.exceptions import ConfigurationError


def test_default_config_valid():
    config = EngineConfig()
    config.validate()
    assert config.model.n_embd % config.model.n_head == 0
    assert config.model.tie_word_embeddings is True
    assert config.model.bias is False
    assert config.training.gradient_accumulation_steps == 1
    assert config.training.gradient_checkpointing is False
    assert config.training.precision == "float32"
    assert config.training.optimizer_type == "adamw"
    assert config.data.num_workers == 0
    assert config.data.pin_memory is True


def test_invalid_n_embd_division():
    # n_embd = 100 không chia hết cho n_head = 6
    cfg = ModelConfig(n_embd=100, n_head=6)
    with pytest.raises(ConfigurationError):
        cfg.validate()


def test_invalid_batch_size():
    cfg = TrainingConfig(batch_size=0)
    with pytest.raises(ConfigurationError):
        cfg.validate()


def test_invalid_split_ratio():
    cfg = DataConfig(split_ratio=1.5)
    with pytest.raises(ConfigurationError):
        cfg.validate()


def test_load_yaml_config():
    config = EngineConfig.from_yaml("configs/truyen_kieu.yaml")
    assert config.model.name == "minigpt"
    assert config.training.batch_size == 64
    assert config.model.tie_word_embeddings is True
    assert config.training.optimizer_type == "adamw"


def test_config_copy_with_overrides():
    orig = TrainingConfig(batch_size=32, learning_rate=1e-3)
    copied = orig.copy(batch_size=16)
    assert copied.batch_size == 16
    assert copied.learning_rate == 1e-3
    assert orig.batch_size == 32  # Immutable


def test_env_var_interpolation(monkeypatch):
    monkeypatch.setenv("TEST_AI_BATCH_SIZE", "128")
    monkeypatch.setenv("TEST_AI_MODEL_NAME", "gpt_custom")

    raw_text = "batch_size: ${TEST_AI_BATCH_SIZE}\nname: ${TEST_AI_MODEL_NAME}\nfallback: ${NON_EXISTENT_VAR:-default_val}"
    interpolated = interpolate_env_vars(raw_text)

    assert "batch_size: 128" in interpolated
    assert "name: gpt_custom" in interpolated
    assert "fallback: default_val" in interpolated


def test_env_var_missing_raises_error():
    raw_text = "secret: ${COMPLETELY_UNDEFINED_VAR_XYZ}"
    with pytest.raises(ConfigurationError) as excinfo:
        interpolate_env_vars(raw_text)
    assert "COMPLETELY_UNDEFINED_VAR_XYZ" in str(excinfo.value)


def test_apply_overrides_types():
    data = {
        "training": {
            "batch_size": 64,
            "learning_rate": 0.001,
            "gradient_checkpointing": False,
            "precision": "float32",
        },
        "model": {"n_layer": 4},
    }
    overrides = [
        "training.batch_size=32",
        "training.learning_rate=0.0005",
        "training.gradient_checkpointing=true",
        "training.precision=amp_bf16",
        "model.n_layer=8",
    ]
    updated = apply_overrides(data, overrides)

    assert updated["training"]["batch_size"] == 32
    assert isinstance(updated["training"]["batch_size"], int)
    assert updated["training"]["learning_rate"] == 0.0005
    assert isinstance(updated["training"]["learning_rate"], float)
    assert updated["training"]["gradient_checkpointing"] is True
    assert updated["training"]["precision"] == "amp_bf16"
    assert updated["model"]["n_layer"] == 8


def test_apply_overrides_invalid_format():
    data = {"training": {"batch_size": 32}}
    with pytest.raises(ConfigurationError):
        apply_overrides(data, ["training.batch_size_without_equal"])


def test_yaml_load_with_overrides():
    config = EngineConfig.from_yaml(
        "configs/truyen_kieu.yaml",
        overrides=[
            "training.batch_size=16",
            "training.gradient_accumulation_steps=4",
            "model.n_layer=2",
        ],
    )
    assert config.training.batch_size == 16
    assert config.training.gradient_accumulation_steps == 4
    assert config.model.n_layer == 2


def test_typo_suggestion_domain_config():
    # Gõ nhầm 'block_siz' thay vì 'block_size'
    data = {"n_embd": 192, "block_siz": 64}
    with pytest.raises(ConfigurationError) as excinfo:
        ModelConfig.from_kwargs_safe(data)
    assert "block_siz" in str(excinfo.value)
    assert "block_size" in str(excinfo.value)


def test_typo_suggestion_engine_config():
    # Gõ nhầm 'trainning' thay vì 'training'
    data = {"trainning": {"batch_size": 32}}
    with pytest.raises(ConfigurationError) as excinfo:
        EngineConfig.from_dict(data)
    assert "trainning" in str(excinfo.value)
    assert "training" in str(excinfo.value)


def test_new_fields_validation():
    # tie_word_embeddings
    with pytest.raises(ConfigurationError):
        ModelConfig(tie_word_embeddings="not_a_bool").validate()  # type: ignore

    # gradient_accumulation_steps
    with pytest.raises(ConfigurationError):
        TrainingConfig(gradient_accumulation_steps=0).validate()

    # precision
    with pytest.raises(ConfigurationError):
        TrainingConfig(precision="invalid_precision").validate()

    # optimizer_type
    with pytest.raises(ConfigurationError):
        TrainingConfig(optimizer_type="unknown_opt").validate()

    # num_workers
    with pytest.raises(ConfigurationError):
        DataConfig(num_workers=-1).validate()


def test_from_kwargs_safe_non_dataclass():
    class PlainClass:
        pass

    with pytest.raises(ConfigurationError) as excinfo:
        BaseConfig.from_kwargs_safe.__func__(PlainClass, {})  # type: ignore
    assert "không phải là dataclass hợp lệ" in str(excinfo.value)


def test_model_kwargs_and_use_cache_config():
    # model_kwargs valid and invalid
    cfg = ModelConfig(model_kwargs={"rope_theta": 10000.0, "multiple_of": 64})
    cfg.validate()
    assert cfg.model_kwargs["rope_theta"] == 10000.0

    with pytest.raises(ConfigurationError):
        ModelConfig(model_kwargs="not_a_dict").validate()  # type: ignore

    # GenerationConfig use_cache
    gen_cfg = GenerationConfig(use_cache=True)
    gen_cfg.validate()
    assert gen_cfg.use_cache is True

    with pytest.raises(ConfigurationError):
        GenerationConfig(use_cache="not_a_bool").validate()  # type: ignore


def test_subdomain_typo_via_engine_config():
    # Gõ nhầm trường bên trong sub-domain qua EngineConfig.from_dict
    data = {"system": {"devce": "cpu"}}
    with pytest.raises(ConfigurationError) as excinfo:
        EngineConfig.from_dict(data)
    assert "devce" in str(excinfo.value)
    assert "device" in str(excinfo.value)


def test_protocol_errors_exported():
    from src.core import ProtocolError, ProtocolViolationError, SignatureMismatchError

    assert issubclass(ProtocolViolationError, ProtocolError)
    assert issubclass(SignatureMismatchError, ProtocolError)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("eval_iters", 0),
        ("min_lr", -1e-6),
        ("weight_decay", -0.1),
        ("grad_clip", -1.0),
    ],
)
def test_training_config_rejects_invalid_runtime_ranges(field: str, value: object) -> None:
    """Reject values that otherwise fail late or silently alter training behavior."""
    cfg = TrainingConfig(**{field: value})  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        cfg.validate()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("checkpoint_name", "../best.pt"),
        ("checkpoint_name", r"..\\best.pt"),
        ("run_name", "../escape"),
        ("run_name", r"..\\escape"),
    ],
)
def test_training_config_rejects_unsafe_checkpoint_path_components(
    field: str, value: str
) -> None:
    cfg = TrainingConfig(**{field: value})  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        cfg.validate()
