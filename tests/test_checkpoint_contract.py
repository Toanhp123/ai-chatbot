from typing import cast

import pytest
import torch

from src.core.config import EngineConfig, ModelConfig
from src.data.batch_provider import get_batch_provider
from src.data.tokenizers import CharTokenizer
from src.data.tokenizers.base import get_tokenizer_identity
from src.generation.generator import TextGenerator
from src.models.registry import ModelRegistry
from src.training.trainer import Trainer


def _tiny_config() -> EngineConfig:
    cfg = EngineConfig()
    cfg.model.vocab_size = 8
    cfg.model.block_size = 4
    cfg.model.n_embd = 8
    cfg.model.n_head = 2
    cfg.model.n_layer = 1
    cfg.model.dropout = 0.0
    cfg.training.batch_size = 2
    cfg.training.max_iters = 1
    cfg.training.eval_interval = 1
    cfg.training.eval_iters = 1
    return cfg


def test_cli_checkpoint_loader_rejects_tokenizer_identity_mismatch(tmp_path) -> None:
    from main import load_generator_from_checkpoint

    tokenizer_a = CharTokenizer(vocab=list("abcdef"))
    tokenizer_b = CharTokenizer(vocab=list("uvwxyz"))
    vocab_path = tmp_path / "vocab.json"
    tokenizer_b.save_vocab(str(vocab_path))

    cfg = ModelConfig(
        name="minigpt",
        vocab_size=tokenizer_a.vocab_size,
        block_size=4,
        n_embd=8,
        n_head=2,
        n_layer=1,
        dropout=0.0,
    )
    model = ModelRegistry.create("minigpt", cfg)
    checkpoint_path = tmp_path / "model.pt"
    torch.save(
        {
            "checkpoint_version": 2,
            "model_state_dict": model.state_dict(),
            "config": {"model": cfg.to_dict()},
            "tokenizer_identity": get_tokenizer_identity(tokenizer_a),
        },
        checkpoint_path,
    )

    with pytest.raises(Exception, match="Tokenizer|tokenizer|vocab|từ vựng"):
        load_generator_from_checkpoint(str(checkpoint_path), str(vocab_path), device="cpu")


def test_v2_resume_requires_runtime_tokenizer_identity_match(tmp_path) -> None:
    cfg = _tiny_config()
    tokenizer = CharTokenizer(vocab=list("abcdef"))
    cfg.model.vocab_size = tokenizer.vocab_size
    model = ModelRegistry.create("minigpt", cfg.model)
    provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    source_trainer = Trainer(
        model=model, batch_provider=provider, config=cfg, tokenizer=tokenizer, device="cpu"
    )
    state = source_trainer.get_checkpoint_state()
    # Exercise the legacy v2 contract explicitly: v3 embeds tokenizer state and can
    # reconstruct it when the runtime tokenizer is absent.
    state["checkpoint_version"] = 2
    state.pop("tokenizer_state", None)
    state["step"] = 1
    path = tmp_path / "resume.pt"
    torch.save(state, path)

    target_model = ModelRegistry.create("minigpt", cfg.model)
    target_before = {
        key: value.detach().clone() for key, value in target_model.state_dict().items()
    }
    target_trainer = Trainer(model=target_model, batch_provider=provider, config=cfg, device="cpu")
    with pytest.raises(ValueError, match="Tokenizer|tokenizer"):
        target_trainer.resume_from_checkpoint(str(path))

    for key, value in target_model.state_dict().items():
        assert torch.equal(value, target_before[key]), key


def test_trainer_without_tokenizer_does_not_emit_invalid_checkpoint_v2() -> None:
    cfg = _tiny_config()
    model = ModelRegistry.create("minigpt", cfg.model)
    provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    trainer = Trainer(model=model, batch_provider=provider, config=cfg, device="cpu")

    state = trainer.get_checkpoint_state()

    assert state["checkpoint_version"] == 1
    assert state["tokenizer_identity"] is None


def test_v3_checkpoint_embeds_reconstructable_tokenizer_state(tmp_path) -> None:
    from main import load_generator_from_checkpoint

    tokenizer = CharTokenizer(vocab=list("abcdef"))
    cfg = _tiny_config()
    cfg.model.vocab_size = tokenizer.vocab_size
    model = ModelRegistry.create("minigpt", cfg.model)
    provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    trainer = Trainer(
        model=model, batch_provider=provider, config=cfg, tokenizer=tokenizer, device="cpu"
    )
    state = trainer.get_checkpoint_state()

    assert state["checkpoint_version"] >= 3
    assert state["tokenizer_state"] == state["tokenizer_identity"]["payload"]

    path = tmp_path / "portable.pt"
    torch.save(state, path)
    generator = cast(
        TextGenerator,
        load_generator_from_checkpoint(
            str(path), str(tmp_path / "missing-vocab.json"), device="cpu"
        ),
    )

    assert (
        get_tokenizer_identity(generator.tokenizer)["fingerprint"]
        == get_tokenizer_identity(tokenizer)["fingerprint"]
    )


def test_dataloader_provider_resume_restores_exact_batch_sequence(tmp_path) -> None:
    from src.data.batch_provider import DataLoaderBatchProvider
    from src.data.dataset import TextDataset

    train = torch.arange(0, 64, dtype=torch.long) % 8
    val = torch.arange(0, 48, dtype=torch.long) % 8
    source = DataLoaderBatchProvider(TextDataset(train, 4), TextDataset(val, 4), num_workers=0)

    torch.manual_seed(1234)
    _ = source.get_train_batch(3, 4, "cpu")
    saved_rng = torch.get_rng_state().clone()
    state = source.state_dict()
    expected_x, expected_y = source.get_train_batch(3, 4, "cpu")

    resumed = DataLoaderBatchProvider(TextDataset(train, 4), TextDataset(val, 4), num_workers=0)
    resumed.load_state_dict(state)
    torch.set_rng_state(saved_rng)
    actual_x, actual_y = resumed.get_train_batch(3, 4, "cpu")

    assert torch.equal(actual_x, expected_x)
    assert torch.equal(actual_y, expected_y)


def test_resume_provider_mismatch_is_rejected_before_model_mutation(tmp_path) -> None:
    from src.data.batch_provider import DataLoaderBatchProvider
    from src.data.dataset import TextDataset

    cfg = _tiny_config()
    tokenizer = CharTokenizer(vocab=list("abcdef"))
    cfg.model.vocab_size = tokenizer.vocab_size
    source_model = ModelRegistry.create("minigpt", cfg.model)
    source_provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    source = Trainer(
        model=source_model,
        batch_provider=source_provider,
        config=cfg,
        tokenizer=tokenizer,
        device="cpu",
    )
    state = source.get_checkpoint_state()
    state["step"] = 1
    path = tmp_path / "provider-mismatch.pt"
    torch.save(state, path)

    target_model = ModelRegistry.create("minigpt", cfg.model)
    before = {key: value.detach().clone() for key, value in target_model.state_dict().items()}
    train = torch.randint(0, cfg.model.vocab_size, (32,))
    val = torch.randint(0, cfg.model.vocab_size, (32,))
    target_provider = DataLoaderBatchProvider(TextDataset(train, 4), TextDataset(val, 4))
    target = Trainer(
        model=target_model,
        batch_provider=target_provider,
        config=cfg,
        tokenizer=tokenizer,
        device="cpu",
    )

    with pytest.raises(ValueError, match="Batch provider"):
        target.resume_from_checkpoint(str(path))

    for key, value in target_model.state_dict().items():
        assert torch.equal(value, before[key]), key


def test_v3_resume_rejects_corrupted_embedded_tokenizer_state(tmp_path) -> None:
    cfg = _tiny_config()
    tokenizer = CharTokenizer(vocab=list("abcdef"))
    cfg.model.vocab_size = tokenizer.vocab_size
    model = ModelRegistry.create("minigpt", cfg.model)
    provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    source = Trainer(
        model=model, batch_provider=provider, config=cfg, tokenizer=tokenizer, device="cpu"
    )
    state = source.get_checkpoint_state()
    state["tokenizer_state"] = dict(state["tokenizer_state"])
    state["tokenizer_state"]["vocab"] = list("uvwxyz")
    path = tmp_path / "corrupt-tokenizer.pt"
    torch.save(state, path)

    target_model = ModelRegistry.create("minigpt", cfg.model)
    target = Trainer(
        model=target_model, batch_provider=provider, config=cfg, tokenizer=None, device="cpu"
    )

    with pytest.raises(ValueError, match="Tokenizer|tokenizer"):
        target.resume_from_checkpoint(str(path))


def test_cli_v3_checkpoint_requires_embedded_tokenizer_state(tmp_path) -> None:
    from main import load_generator_from_checkpoint

    tokenizer = CharTokenizer(vocab=list("abcdef"))
    vocab_path = tmp_path / "vocab.json"
    tokenizer.save_vocab(str(vocab_path))
    cfg = ModelConfig(
        name="minigpt",
        vocab_size=tokenizer.vocab_size,
        block_size=4,
        n_embd=8,
        n_head=2,
        n_layer=1,
        dropout=0.0,
    )
    model = ModelRegistry.create("minigpt", cfg)
    checkpoint_path = tmp_path / "v3-missing-tokenizer-state.pt"
    torch.save(
        {
            "checkpoint_version": 3,
            "model_state_dict": model.state_dict(),
            "config": {"model": cfg.to_dict()},
            "tokenizer_identity": get_tokenizer_identity(tokenizer),
        },
        checkpoint_path,
    )

    with pytest.raises(Exception, match="v3|tokenizer state|Tokenizer state"):
        load_generator_from_checkpoint(str(checkpoint_path), str(vocab_path), device="cpu")


def test_train_initializes_callbacks_before_restoring_callback_state(tmp_path) -> None:
    from src.training.callbacks.base import BaseCallback

    class ResetOnBeginCallback(BaseCallback):
        def __init__(self, value: int) -> None:
            self.value = value

        def on_train_begin(self, trainer) -> None:
            del trainer
            self.value = 0

        def state_dict(self):
            return {"value": self.value}

        def load_state_dict(self, state):
            self.value = int(state["value"])

    cfg = _tiny_config()
    tokenizer = CharTokenizer(vocab=list("abcdef"))
    cfg.model.vocab_size = tokenizer.vocab_size
    provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    source_callback = ResetOnBeginCallback(7)
    source = Trainer(
        model=ModelRegistry.create("minigpt", cfg.model),
        batch_provider=provider,
        config=cfg,
        callbacks=[source_callback],
        tokenizer=tokenizer,
        device="cpu",
    )
    state = source.get_checkpoint_state()
    state["step"] = cfg.training.max_iters
    checkpoint = tmp_path / "callback-state.pt"
    torch.save(state, checkpoint)

    target_callback = ResetOnBeginCallback(999)
    target = Trainer(
        model=ModelRegistry.create("minigpt", cfg.model),
        batch_provider=provider,
        config=cfg,
        callbacks=[target_callback],
        tokenizer=tokenizer,
        device="cpu",
    )

    target.train(resume_checkpoint=str(checkpoint))

    assert target_callback.value == 7


def test_resume_rejects_trajectory_config_drift_before_state_mutation(tmp_path) -> None:
    cfg = _tiny_config()
    model = ModelRegistry.create("minigpt", cfg.model)
    provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    source = Trainer(model=model, batch_provider=provider, config=cfg, device="cpu")
    state = source.get_checkpoint_state()
    state["step"] = 1
    path = tmp_path / "config-drift.pt"
    torch.save(state, path)

    target_cfg = EngineConfig.from_dict(cfg.to_dict())
    target_cfg.training.learning_rate *= 2
    target_model = ModelRegistry.create("minigpt", target_cfg.model)
    before = {key: value.detach().clone() for key, value in target_model.state_dict().items()}
    target = Trainer(model=target_model, batch_provider=provider, config=target_cfg, device="cpu")

    with pytest.raises(ValueError, match="config|cấu hình|learning_rate"):
        target.resume_from_checkpoint(str(path))

    for key, value in target_model.state_dict().items():
        assert torch.equal(value, before[key]), key


def test_resume_allows_max_iters_extension_and_checkpoint_output_changes(tmp_path) -> None:
    cfg = _tiny_config()
    cfg.training.max_iters = 3
    cfg.training.warmup_iters = 1
    model = ModelRegistry.create("minigpt", cfg.model)
    provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    source = Trainer(model=model, batch_provider=provider, config=cfg, device="cpu")
    state = source.get_checkpoint_state()
    state["step"] = 1
    path = tmp_path / "extend.pt"
    torch.save(state, path)

    target_cfg = EngineConfig.from_dict(cfg.to_dict())
    target_cfg.training.max_iters = 5
    target_cfg.training.checkpoint_dir = str(tmp_path / "other")
    target_cfg.training.checkpoint_name = "continued.pt"
    target_cfg.training.run_name = "continued"
    target_cfg.training.save_top_k = 1
    target_cfg.training.save_last = False
    target = Trainer(
        model=ModelRegistry.create("minigpt", target_cfg.model),
        batch_provider=provider,
        config=target_cfg,
        device="cpu",
    )

    resumed_step = target.resume_from_checkpoint(str(path))

    assert resumed_step == 1
    assert target.start_step == 2


def test_resume_rejects_checkpoint_revision_changed_after_start_intent(tmp_path) -> None:
    import os

    tokenizer = CharTokenizer(vocab=list("abcdef"))
    cfg = _tiny_config()
    cfg.model.vocab_size = tokenizer.vocab_size
    provider = get_batch_provider(
        "tensor",
        train_data=torch.randint(0, cfg.model.vocab_size, (32,)),
        val_data=torch.randint(0, cfg.model.vocab_size, (32,)),
    )
    source = Trainer(
        model=ModelRegistry.create("minigpt", cfg.model),
        batch_provider=provider,
        config=cfg,
        tokenizer=tokenizer,
        device="cpu",
    )
    first = tmp_path / "resume.pt"
    replacement = tmp_path / "replacement.pt"
    state = source.get_checkpoint_state()
    state["step"] = 1
    torch.save(state, first)
    first_stat = os.stat(first)
    expected_identity = (
        int(first_stat.st_dev),
        int(first_stat.st_ino),
        int(first_stat.st_size),
        int(first_stat.st_mtime_ns),
    )
    state["step"] = 2
    torch.save(state, replacement)
    os.replace(replacement, first)

    target_model = ModelRegistry.create("minigpt", cfg.model)
    before = {key: value.detach().clone() for key, value in target_model.state_dict().items()}
    target = Trainer(
        model=target_model,
        batch_provider=provider,
        config=cfg,
        tokenizer=tokenizer,
        device="cpu",
    )

    with pytest.raises(ValueError, match="revision|thay đổi|changed"):
        target.resume_from_checkpoint(str(first), expected_identity=expected_identity)

    for key, value in target_model.state_dict().items():
        assert torch.equal(value, before[key]), key
