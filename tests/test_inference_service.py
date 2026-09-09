import pytest

from src.application.inference.service import InferenceService
from src.core.exceptions import AIEngineError
from tests.application_support import concrete_inference_runtime, make_inference_service


def _service_without_assets(tmp_path) -> InferenceService:
    return make_inference_service(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing_default.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        backend="local",
    )


def test_inference_service_loads_existing_configured_vocab_on_startup(tmp_path):
    from src.data.tokenizers import CharTokenizer

    vocab_path = tmp_path / "vocab.json"
    CharTokenizer(vocab=list("abcd")).save_vocab(str(vocab_path))

    service = make_inference_service(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing_default.pt"),
        vocab_path=str(vocab_path),
    )

    assert concrete_inference_runtime(service).tokenizer is not None
    assert concrete_inference_runtime(service).tokenizer.vocab_size == 4


def test_failed_checkpoint_load_does_not_mutate_backend(tmp_path):
    service = _service_without_assets(tmp_path)

    with pytest.raises(FileNotFoundError):
        service.load_checkpoint(str(tmp_path / "missing.pt"), backend="pytorch")

    assert service.current_backend == "local"
    assert service.current_checkpoint_path is None
    assert concrete_inference_runtime(service).model is None
    assert concrete_inference_runtime(service).generator is None


def test_invalid_checkpoint_backend_is_rejected_without_mutating_state(tmp_path):
    service = _service_without_assets(tmp_path)

    with pytest.raises(AIEngineError):
        service.load_checkpoint(str(tmp_path / "missing.pt"), backend="invalid_backend_xyz")

    assert service.current_backend == "local"
    assert service.current_checkpoint_path is None


def test_checkpoint_listing_uses_safe_weights_only_loading(tmp_path, monkeypatch):
    """Listing checkpoints must not use unrestricted pickle deserialization."""
    import torch

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    torch.save({"step": 3, "val_loss": 1.2}, checkpoint_dir / "safe.pt")
    service = make_inference_service(
        checkpoint_dir=str(checkpoint_dir),
        default_checkpoint=str(tmp_path / "missing_default.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
    )

    real_load = torch.load
    calls = []

    def recording_load(*args, **kwargs):
        calls.append(kwargs.copy())
        return real_load(*args, **kwargs)

    monkeypatch.setattr("src.inference.checkpoint_loader.torch.load", recording_load)
    checkpoints = service.list_checkpoints()

    assert [item["filename"] for item in checkpoints] == ["safe.pt"]
    assert calls
    assert all(call.get("weights_only") is True for call in calls)


def test_checkpoint_load_requires_tokenizer_before_committing_state(tmp_path):
    import torch

    from src.core.config import ModelConfig
    from src.models.architectures.minigpt import MiniGPT

    cfg = ModelConfig(
        name="minigpt",
        vocab_size=8,
        block_size=8,
        n_embd=8,
        n_head=2,
        n_layer=1,
    )
    model = MiniGPT(cfg)
    checkpoint = tmp_path / "model.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": {"model": cfg.to_dict()},
        },
        checkpoint,
    )
    service = _service_without_assets(tmp_path)

    with pytest.raises(ValueError, match="tokenizer|từ vựng"):
        service.load_checkpoint(str(checkpoint))

    assert concrete_inference_runtime(service).model is None
    assert concrete_inference_runtime(service).generator is None
    assert service.current_checkpoint_path is None


def test_stream_generate_serializes_shared_generator_state(tmp_path):
    import threading
    import time

    from src.core.config import GenerationConfig

    class DummyTokenizer:
        def encode(self, text):
            return [1]

    class SharedStateGenerator:
        def __init__(self):
            self._state_lock = threading.Lock()
            self.active = 0
            self.max_active = 0

        def generate(self, prompt, config, streamer, return_output=False):
            with self._state_lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                # Long enough for two request workers to overlap without service isolation.
                time.sleep(0.08)
                streamer.on_token(prompt[-1])
            finally:
                with self._state_lock:
                    self.active -= 1
                streamer.on_finish()

    service = _service_without_assets(tmp_path)
    generator = SharedStateGenerator()
    concrete_inference_runtime(service).tokenizer = DummyTokenizer()  # type: ignore[assignment]
    concrete_inference_runtime(service).generator = generator  # type: ignore[assignment]

    start = threading.Barrier(3)
    outputs = []

    def consume(prompt: str) -> None:
        start.wait()
        events = list(service.stream_generate(prompt, GenerationConfig(max_new_tokens=1)))
        outputs.append(events)

    threads = [
        threading.Thread(target=consume, args=("A",)),
        threading.Thread(target=consume, args=("B",)),
    ]
    for thread in threads:
        thread.start()
    start.wait()
    for thread in threads:
        thread.join(timeout=2.0)
        assert not thread.is_alive()

    assert generator.max_active == 1
    assert len(outputs) == 2


def test_checkpoint_load_rejects_tokenizer_identity_mismatch(tmp_path):
    import torch

    from src.core.config import ModelConfig
    from src.data.tokenizers import CharTokenizer
    from src.data.tokenizers.base import get_tokenizer_identity
    from src.models.architectures.minigpt import MiniGPT

    tokenizer_a = CharTokenizer(vocab=list("abcd"))
    tokenizer_b = CharTokenizer(vocab=list("wxyz"))
    cfg = ModelConfig(
        name="minigpt",
        vocab_size=tokenizer_a.vocab_size,
        block_size=8,
        n_embd=8,
        n_head=2,
        n_layer=1,
    )
    model = MiniGPT(cfg)
    checkpoint = tmp_path / "model.pt"
    torch.save(
        {
            "checkpoint_version": 2,
            "model_state_dict": model.state_dict(),
            "config": {"model": cfg.to_dict()},
            "tokenizer_identity": get_tokenizer_identity(tokenizer_a),
        },
        checkpoint,
    )

    service = _service_without_assets(tmp_path)
    concrete_inference_runtime(service).tokenizer = tokenizer_b

    with pytest.raises(ValueError, match="tokenizer|vocab|từ vựng"):
        service.load_checkpoint(str(checkpoint))

    assert concrete_inference_runtime(service).model is None
    assert concrete_inference_runtime(service).generator is None
    assert service.current_checkpoint_path is None


def test_checkpoint_load_prefers_configured_vocab_file_over_stale_in_memory_tokenizer(tmp_path):
    import torch

    from src.core.config import ModelConfig
    from src.data.tokenizers import CharTokenizer
    from src.data.tokenizers.base import get_tokenizer_identity
    from src.models.architectures.minigpt import MiniGPT

    old_tokenizer = CharTokenizer(vocab=list("abcd"))
    new_tokenizer = CharTokenizer(vocab=list("wxyz"))
    vocab_path = tmp_path / "new_vocab.json"
    new_tokenizer.save_vocab(str(vocab_path))

    cfg = ModelConfig(
        name="minigpt",
        vocab_size=new_tokenizer.vocab_size,
        block_size=8,
        n_embd=8,
        n_head=2,
        n_layer=1,
    )
    model = MiniGPT(cfg)
    checkpoint = tmp_path / "new_model.pt"
    torch.save(
        {
            "checkpoint_version": 2,
            "model_state_dict": model.state_dict(),
            "config": {"model": cfg.to_dict()},
            "tokenizer_identity": get_tokenizer_identity(new_tokenizer),
        },
        checkpoint,
    )

    service = make_inference_service(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(vocab_path),
        device="cpu",
    )
    concrete_inference_runtime(service).tokenizer = old_tokenizer

    service.load_checkpoint(str(checkpoint))

    loaded_tokenizer = concrete_inference_runtime(service).tokenizer
    assert loaded_tokenizer is not None
    assert (
        get_tokenizer_identity(loaded_tokenizer)["fingerprint"]
        == get_tokenizer_identity(new_tokenizer)["fingerprint"]
    )


def test_checkpoint_listing_preserves_zero_validation_loss(tmp_path):
    import torch

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    torch.save({"step": 7, "val_loss": 0.0}, checkpoint_dir / "zero.pt")
    service = make_inference_service(
        checkpoint_dir=str(checkpoint_dir),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cpu",
    )

    [entry] = service.list_checkpoints()

    assert entry["val_loss"] == 0.0
    assert entry["is_best_val"] is True


def test_stream_done_counts_generated_token_ids_not_text_chunks(tmp_path):
    from src.core.config import GenerationConfig
    from src.generation.base import GenerationOutput

    class DummyTokenizer:
        def encode(self, text):
            return [1]

    class ChunkingGenerator:
        def generate(self, prompt, config, streamer, return_output=False):
            streamer.on_token("ă")
            streamer.on_finish()
            return GenerationOutput(
                text=prompt + "ă",
                prompt=prompt,
                generated_text="ă",
                token_ids=[196, 131],
                tokens_generated=2,
                tokens_per_second=20.0,
                elapsed_time_sec=0.1,
                finish_reason="length",
            )

    service = _service_without_assets(tmp_path)
    concrete_inference_runtime(service).tokenizer = DummyTokenizer()  # type: ignore[assignment]
    concrete_inference_runtime(service).generator = ChunkingGenerator()  # type: ignore[assignment]

    events = list(service.stream_generate("A", GenerationConfig(max_new_tokens=2)))
    done = next(event for event in events if event.get("type") == "done")

    assert done["token_count"] == 2


def test_checkpoint_v3_missing_embedded_tokenizer_state_is_rejected_atomically(tmp_path):
    import torch

    from src.core.config import ModelConfig
    from src.data.tokenizers import CharTokenizer
    from src.data.tokenizers.base import get_tokenizer_identity
    from src.models.architectures.minigpt import MiniGPT

    tokenizer = CharTokenizer(vocab=list("abcd"))
    vocab_path = tmp_path / "vocab.json"
    tokenizer.save_vocab(str(vocab_path))
    cfg = ModelConfig(
        name="minigpt",
        vocab_size=tokenizer.vocab_size,
        block_size=8,
        n_embd=8,
        n_head=2,
        n_layer=1,
    )
    checkpoint = tmp_path / "v3-missing-tokenizer-state.pt"
    torch.save(
        {
            "checkpoint_version": 3,
            "model_state_dict": MiniGPT(cfg).state_dict(),
            "config": {"model": cfg.to_dict()},
            "tokenizer_identity": get_tokenizer_identity(tokenizer),
        },
        checkpoint,
    )

    service = make_inference_service(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(vocab_path),
        device="cpu",
    )

    with pytest.raises(ValueError, match="v3|tokenizer state|Tokenizer state"):
        service.load_checkpoint(str(checkpoint))

    assert concrete_inference_runtime(service).model is None
    assert concrete_inference_runtime(service).generator is None
    assert service.current_checkpoint_path is None


def _write_portable_checkpoint(path, *, step: int = 1):
    import torch

    from src.core.config import ModelConfig
    from src.data.tokenizers import CharTokenizer
    from src.data.tokenizers.base import get_tokenizer_identity
    from src.models.architectures.minigpt import MiniGPT

    tokenizer = CharTokenizer(vocab=list("abcd"))
    cfg = ModelConfig(
        name="minigpt",
        vocab_size=tokenizer.vocab_size,
        block_size=8,
        n_embd=8,
        n_head=2,
        n_layer=1,
    )
    torch.save(
        {
            "checkpoint_version": 3,
            "model_state_dict": MiniGPT(cfg).state_dict(),
            "config": {"model": cfg.to_dict()},
            "tokenizer_identity": get_tokenizer_identity(tokenizer),
            "tokenizer_state": tokenizer.identity_payload(),
            "step": step,
            "val_loss": float(step),
        },
        path,
    )


def test_inference_service_from_engine_config_uses_custom_artifact_paths(tmp_path):
    from src.core.config import EngineConfig

    config = EngineConfig().copy(
        system=EngineConfig().system.copy(device="cpu"),
        data=EngineConfig().data.copy(vocab_file=str(tmp_path / "custom_vocab.json")),
        training=EngineConfig().training.copy(
            checkpoint_dir=str(tmp_path / "artifacts"),
            checkpoint_name="champion.pt",
        ),
    )

    service = make_inference_service(engine_config=config)

    assert service.checkpoint_dir == str(tmp_path / "artifacts")
    assert service.checkpoint_name == "champion.pt"
    assert service.vocab_path == str(tmp_path / "custom_vocab.json")


def test_checkpoint_listing_uses_configured_checkpoint_name_for_best_tag(tmp_path):
    import torch

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    torch.save({"step": 1, "val_loss": 1.0}, checkpoint_dir / "champion.pt")
    torch.save({"step": 2, "val_loss": 2.0}, checkpoint_dir / "other.pt")
    service = make_inference_service(
        checkpoint_dir=str(checkpoint_dir),
        checkpoint_name="champion.pt",
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cpu",
    )

    checkpoints = service.list_checkpoints()

    assert checkpoints[0]["filename"] == "champion.pt"
    assert checkpoints[0]["tag"] == "best"


def test_same_checkpoint_path_replacement_is_not_reported_active_until_reloaded(tmp_path):
    import time

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    checkpoint_path = checkpoint_dir / "best.pt"
    _write_portable_checkpoint(checkpoint_path, step=10)
    service = make_inference_service(
        checkpoint_dir=str(checkpoint_dir),
        checkpoint_name="best.pt",
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cpu",
    )

    service.load_checkpoint(str(checkpoint_path))
    [before] = service.list_checkpoints()
    assert before["is_active"] is True

    time.sleep(0.002)
    _write_portable_checkpoint(checkpoint_path, step=20)
    [after] = service.list_checkpoints()

    assert after["step"] == 20
    assert after["is_active"] is False
    assert service.current_checkpoint_path == str(checkpoint_path)


def test_configured_best_checkpoint_is_marked_and_protected_from_delete(tmp_path):
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    configured = checkpoint_dir / "custom-best.pt"
    _write_portable_checkpoint(configured, step=42)
    service = make_inference_service(
        checkpoint_dir=str(checkpoint_dir),
        checkpoint_name="custom-best.pt",
        default_checkpoint=str(checkpoint_dir / "missing.pt"),
        vocab_path=str(tmp_path / "missing-vocab.json"),
    )

    items = service.list_checkpoints()
    item = next(entry for entry in items if entry["filename"] == "custom-best.pt")
    assert item["is_configured_best"] is True

    with pytest.raises(ValueError, match="checkpoint tốt nhất"):
        service.delete_checkpoint("custom-best.pt")


def test_generation_rejected_while_training_owns_same_accelerator(tmp_path):
    from unittest.mock import Mock

    from src.core.accelerator import AcceleratorCoordinator
    from src.core.config import GenerationConfig
    from src.core.exceptions import AcceleratorBusyError

    coordinator = AcceleratorCoordinator()
    coordinator.reserve_training("cuda")
    service = make_inference_service(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cpu",
        accelerator_coordinator=coordinator,
    )
    concrete_inference_runtime(service).device = "cuda"
    concrete_inference_runtime(service).generator = Mock()
    concrete_inference_runtime(service).tokenizer = Mock()
    concrete_inference_runtime(service).model = Mock()

    with pytest.raises(AcceleratorBusyError):
        service.begin_generation("hello", GenerationConfig(max_new_tokens=1))

    assert service._admission.active_sessions == 0
    coordinator.release_training("cuda")


def test_set_backend_rebuilds_generator_on_current_active_device(tmp_path, monkeypatch):
    service = _service_without_assets(tmp_path)
    concrete_inference_runtime(service).device = "mps"
    concrete_inference_runtime(service).model = object()  # type: ignore[assignment]
    concrete_inference_runtime(service).tokenizer = object()  # type: ignore[assignment]
    observed = {}

    monkeypatch.setattr(
        "src.inference.runtime.validate_generator_backend",
        lambda backend: backend.lower().strip(),
    )

    def create_for_inference(backend, *, model, tokenizer, device):
        observed["backend"] = backend
        observed["device"] = device
        return object()

    monkeypatch.setattr(
        "src.inference.runtime.create_generator_for_inference",
        create_for_inference,
    )

    service.set_backend("local")

    assert observed == {"backend": "local", "device": "mps"}


def test_checkpoint_load_builds_generator_for_resolved_target_device(tmp_path, monkeypatch):
    import torch

    checkpoint_path = tmp_path / "model.pt"
    _write_portable_checkpoint(checkpoint_path)
    service = _service_without_assets(tmp_path)
    service.configured_device = "cuda"
    observed = {}

    class FakeModel(torch.nn.Module):
        def load_state_dict(self, state_dict, *args, **kwargs):
            return super().load_state_dict({}, strict=False)

        def to(self, device, *args, **kwargs):
            observed.setdefault("moves", []).append(str(device))
            return self

        def eval(self):
            return self

    monkeypatch.setattr(
        "src.inference.checkpoint_loader.create_model",
        lambda *args, **kwargs: FakeModel(),
    )
    monkeypatch.setattr(
        "src.inference.runtime.resolve_device",
        lambda requested: "cuda",
    )

    def create_for_inference(backend, *, model, tokenizer, device):
        observed["generator_device"] = device
        return object()

    monkeypatch.setattr(
        "src.inference.runtime.create_generator_for_inference",
        create_for_inference,
    )

    service.load_checkpoint(str(checkpoint_path))

    assert observed["generator_device"] == "cuda"
    assert service.device_str == "cuda"


def test_checkpoint_load_reserves_accelerator_before_deserializing(tmp_path, monkeypatch):
    from src.core.accelerator import AcceleratorCoordinator
    from src.core.exceptions import AcceleratorBusyError

    checkpoint_path = tmp_path / "model.pt"
    checkpoint_path.write_bytes(b"not-read")
    coordinator = AcceleratorCoordinator()
    coordinator.reserve_training("cuda")
    service = make_inference_service(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        device="cuda",
        accelerator_coordinator=coordinator,
    )
    monkeypatch.setattr(
        "src.inference.runtime.resolve_device",
        lambda requested: "cuda",
    )
    monkeypatch.setattr(
        "src.inference.checkpoint_loader.torch.load",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("checkpoint was read")),
    )

    try:
        with pytest.raises(AcceleratorBusyError):
            service.load_checkpoint(str(checkpoint_path))
    finally:
        coordinator.release_training("cuda")


def test_checkpoint_load_binds_active_revision_to_exact_loaded_inode(tmp_path, monkeypatch):
    import os

    from src.data.tokenizers import load_tokenizer_state as real_load_tokenizer_state

    checkpoint_path = tmp_path / "best.pt"
    replacement_path = tmp_path / "replacement.pt"
    _write_portable_checkpoint(checkpoint_path, step=10)
    _write_portable_checkpoint(replacement_path, step=20)

    service = make_inference_service(
        checkpoint_dir=str(tmp_path),
        checkpoint_name="best.pt",
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cpu",
    )
    loaded_identity = concrete_inference_runtime(service).checkpoint_identity(str(checkpoint_path))

    def replace_after_payload_was_loaded(state):
        tokenizer = real_load_tokenizer_state(state)
        os.replace(replacement_path, checkpoint_path)
        return tokenizer

    monkeypatch.setattr(
        "src.inference.checkpoint_loader.load_tokenizer_state",
        replace_after_payload_was_loaded,
    )

    service.load_checkpoint(str(checkpoint_path))

    assert concrete_inference_runtime(service).current_checkpoint_identity == loaded_identity
    [listed] = service.list_checkpoints()
    assert listed["step"] == 20
    assert listed["is_active"] is False


def test_checkpoint_listing_uses_one_checkpoint_directory_snapshot(tmp_path, monkeypatch):
    import os

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _write_portable_checkpoint(first / "first.pt", step=1)
    _write_portable_checkpoint(second / "second.pt", step=2)

    service = make_inference_service(
        checkpoint_dir=str(first),
        checkpoint_name="first.pt",
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cpu",
    )
    real_listdir = os.listdir
    switched = False

    def switch_directory_during_scan(path):
        nonlocal switched
        if not switched:
            switched = True
            service.set_checkpoint_dir(str(second))
        return real_listdir(path)

    monkeypatch.setattr("src.inference.checkpoint_catalog.os.listdir", switch_directory_during_scan)

    checkpoints = service.list_checkpoints()

    assert [item["filename"] for item in checkpoints] == ["first.pt"]
    assert checkpoints[0]["is_configured_best"] is True


def test_prepare_for_training_offloads_idle_inference_model_from_shared_accelerator(
    tmp_path, monkeypatch
):
    import torch

    class DummyTokenizer:
        pass

    class DummyGenerator:
        pass

    service = make_inference_service(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        device="cpu",
    )
    model = torch.nn.Linear(2, 2)
    concrete_inference_runtime(service).model = model  # type: ignore[assignment]
    concrete_inference_runtime(service).tokenizer = DummyTokenizer()  # type: ignore[assignment]
    concrete_inference_runtime(service).generator = DummyGenerator()  # type: ignore[assignment]
    concrete_inference_runtime(service).device = "cuda"
    concrete_inference_runtime(service).backend = "local"
    concrete_inference_runtime(service).current_checkpoint_path = "checkpoints/model.pt"
    concrete_inference_runtime(service).current_checkpoint_identity = (1, 2, 3, 4)
    created = []

    def create_for_inference(name, *, model, tokenizer, device):
        created.append((name, model, tokenizer, device))
        return DummyGenerator()

    monkeypatch.setattr(
        "src.inference.runtime.create_generator_for_inference",
        create_for_inference,
    )

    handoff = service.prepare_for_training("cuda:0")
    assert handoff.training_admission_reserved is False
    assert service.device_str == "cpu"
    assert created and created[-1][3] == "cpu"
    assert service.current_checkpoint_path == "checkpoints/model.pt"
    assert concrete_inference_runtime(service).current_checkpoint_identity == (1, 2, 3, 4)


def test_prepare_for_training_refuses_to_move_model_during_active_generation(tmp_path):
    from unittest.mock import Mock

    from src.core.exceptions import GenerationBusyError

    service = make_inference_service(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        device="cpu",
    )
    from src.core.config import GenerationConfig

    concrete_inference_runtime(service).device = "cuda"
    concrete_inference_runtime(service).model = object()  # type: ignore[assignment]
    concrete_inference_runtime(service).tokenizer = Mock()  # type: ignore[assignment]
    concrete_inference_runtime(service).generator = Mock()  # type: ignore[assignment]
    session = service.begin_generation("hello", GenerationConfig(max_new_tokens=1))
    try:
        with pytest.raises(GenerationBusyError):
            service.prepare_for_training("cuda")
        assert service.device_str == "cuda"
    finally:
        session.close()


def test_checkpoint_loaded_on_accelerator_holds_residency_until_offloaded(tmp_path, monkeypatch):
    import torch

    from src.core.accelerator import AcceleratorCoordinator
    from src.core.exceptions import AcceleratorBusyError

    checkpoint_path = tmp_path / "model.pt"
    _write_portable_checkpoint(checkpoint_path)
    coordinator = AcceleratorCoordinator()
    service = make_inference_service(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        device="cuda",
        accelerator_coordinator=coordinator,
    )

    class FakeModel(torch.nn.Module):
        def load_state_dict(self, state_dict, *args, **kwargs):
            return super().load_state_dict({}, strict=False)

        def to(self, device, *args, **kwargs):
            return self

        def eval(self):
            return self

    monkeypatch.setattr(
        "src.inference.checkpoint_loader.create_model",
        lambda *args, **kwargs: FakeModel(),
    )
    monkeypatch.setattr(
        "src.inference.runtime.resolve_device",
        lambda requested: "cuda",
    )
    monkeypatch.setattr(
        "src.inference.runtime.create_generator_for_inference",
        lambda *args, **kwargs: object(),
    )

    service.load_checkpoint(str(checkpoint_path))

    with pytest.raises(AcceleratorBusyError):
        coordinator.reserve_training("cuda")

    handoff = service.prepare_for_training("cuda")
    assert handoff.training_admission_reserved is True
    assert coordinator.snapshot()["cuda"]["training"] is True
    coordinator.release_training("cuda")


def test_legacy_path_setters_keep_canonical_engine_config_in_sync(tmp_path):
    from src.core.config import EngineConfig

    config = EngineConfig()
    service = make_inference_service(engine_config=config)
    new_checkpoint_dir = str(tmp_path / "other-checkpoints")
    new_vocab_path = str(tmp_path / "other-vocab.json")

    service.set_checkpoint_dir(new_checkpoint_dir)
    service.set_vocab_path(new_vocab_path)

    snapshot = service.get_engine_config()
    assert snapshot.training.checkpoint_dir == new_checkpoint_dir
    assert snapshot.data.vocab_file == new_vocab_path


def test_checkpoint_swap_to_cpu_offloads_previous_accelerator_model_before_releasing_residency(
    tmp_path, monkeypatch
):
    import torch

    from src.core.accelerator import AcceleratorCoordinator

    checkpoint_path = tmp_path / "cpu.pt"
    _write_portable_checkpoint(checkpoint_path)
    coordinator = AcceleratorCoordinator()
    service = make_inference_service(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        device="cpu",
        accelerator_coordinator=coordinator,
    )

    moves = []

    class PreviousModel(torch.nn.Module):
        def to(self, device, *args, **kwargs):
            moves.append(("previous", str(device)))
            return self

    class NewModel(torch.nn.Module):
        def load_state_dict(self, state_dict, *args, **kwargs):
            return super().load_state_dict({}, strict=False)

        def to(self, device, *args, **kwargs):
            moves.append(("new", str(device)))
            return self

        def eval(self):
            return self

    concrete_inference_runtime(service).model = PreviousModel()  # type: ignore[assignment]
    concrete_inference_runtime(service).tokenizer = object()  # type: ignore[assignment]
    concrete_inference_runtime(service).generator = object()  # type: ignore[assignment]
    concrete_inference_runtime(service).device = "cuda"
    service._residency_device = "cuda"
    coordinator.reserve_inference_residency("cuda")

    monkeypatch.setattr(
        "src.inference.checkpoint_loader.create_model",
        lambda *args, **kwargs: NewModel(),
    )
    monkeypatch.setattr(
        "src.inference.runtime.resolve_device",
        lambda requested: "cpu",
    )
    monkeypatch.setattr(
        "src.inference.runtime.create_generator_for_inference",
        lambda *args, **kwargs: object(),
    )

    service.load_checkpoint(str(checkpoint_path))

    assert ("previous", "cpu") in moves
    assert service.device_str == "cpu"
    assert service._residency_device is None
    coordinator.reserve_training("cuda")
    coordinator.release_training("cuda")


def test_training_handoff_rollback_restores_inference_residency_and_runtime(tmp_path, monkeypatch):
    import torch

    from src.core.accelerator import AcceleratorCoordinator

    coordinator = AcceleratorCoordinator()
    service = make_inference_service(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing.json"),
        device="cpu",
        accelerator_coordinator=coordinator,
    )

    class DummyTokenizer:
        pass

    previous_generator = object()

    class FakeModel(torch.nn.Module):
        def to(self, device, *args, **kwargs):
            return self

    model = FakeModel()
    concrete_inference_runtime(service).model = model  # type: ignore[assignment]
    concrete_inference_runtime(service).tokenizer = DummyTokenizer()  # type: ignore[assignment]
    concrete_inference_runtime(service).generator = previous_generator  # type: ignore[assignment]
    concrete_inference_runtime(service).backend = "local"
    concrete_inference_runtime(service).device = "cuda"
    service._residency_device = "cuda"
    coordinator.reserve_inference_residency("cuda")
    monkeypatch.setattr(
        "src.inference.runtime.create_generator_for_inference",
        lambda *args, **kwargs: object(),
    )

    handoff = service.prepare_for_training("cuda")
    assert service.device_str == "cpu"
    assert coordinator.snapshot()["cuda"]["training"] is True

    handoff.rollback()

    assert service.device_str == "cuda"
    assert concrete_inference_runtime(service).generator is previous_generator
    assert service._residency_device == "cuda"
    assert coordinator.snapshot()["cuda"] == {
        "training": False,
        "generation": 0,
        "inference_residency": 1,
    }
