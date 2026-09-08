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
