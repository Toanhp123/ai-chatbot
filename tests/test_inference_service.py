import pytest

from src.core.exceptions import AIEngineError
from src.ui.services.inference_service import InferenceService


def _service_without_assets(tmp_path) -> InferenceService:
    return InferenceService(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing_default.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        backend="local",
    )


def test_failed_checkpoint_load_does_not_mutate_backend(tmp_path):
    service = _service_without_assets(tmp_path)

    with pytest.raises(FileNotFoundError):
        service.load_checkpoint(str(tmp_path / "missing.pt"), backend="pytorch")

    assert service.current_backend == "local"
    assert service.current_checkpoint_path is None
    assert service.model is None
    assert service.generator is None


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
    service = InferenceService(
        checkpoint_dir=str(checkpoint_dir),
        default_checkpoint=str(tmp_path / "missing_default.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
    )

    real_load = torch.load
    calls = []

    def recording_load(*args, **kwargs):
        calls.append(kwargs.copy())
        return real_load(*args, **kwargs)

    monkeypatch.setattr("src.ui.services.inference_service.torch.load", recording_load)
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

    assert service.model is None
    assert service.generator is None
    assert service.current_checkpoint_path is None


def test_stream_generate_serializes_shared_generator_state(tmp_path):
    import json
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
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = generator  # type: ignore[assignment]

    start = threading.Barrier(3)
    outputs = []

    def consume(prompt: str) -> None:
        start.wait()
        events = list(service.stream_generate(prompt, GenerationConfig(max_new_tokens=1)))
        outputs.append([json.loads(item.removeprefix("data: ").strip()) for item in events])

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
    service.tokenizer = tokenizer_b

    with pytest.raises(ValueError, match="tokenizer|vocab|từ vựng"):
        service.load_checkpoint(str(checkpoint))

    assert service.model is None
    assert service.generator is None
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

    service = InferenceService(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(vocab_path),
        device="cpu",
    )
    service.tokenizer = old_tokenizer

    service.load_checkpoint(str(checkpoint))

    loaded_tokenizer = service.tokenizer
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
    service = InferenceService(
        checkpoint_dir=str(checkpoint_dir),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cpu",
    )

    [entry] = service.list_checkpoints()

    assert entry["val_loss"] == 0.0
    assert entry["is_best_val"] is True


def test_stream_done_counts_generated_token_ids_not_text_chunks(tmp_path):
    import json

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
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = ChunkingGenerator()  # type: ignore[assignment]

    events = [
        json.loads(item.removeprefix("data: ").strip())
        for item in service.stream_generate("A", GenerationConfig(max_new_tokens=2))
    ]
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

    service = InferenceService(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(vocab_path),
        device="cpu",
    )

    with pytest.raises(ValueError, match="v3|tokenizer state|Tokenizer state"):
        service.load_checkpoint(str(checkpoint))

    assert service.model is None
    assert service.generator is None
    assert service.current_checkpoint_path is None
