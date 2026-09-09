import json
import threading
import time
from typing import Any, List, cast

import pytest
import torch
import torch.nn as nn

from src.core.config import GenerationConfig
from src.core.exceptions import GenerationBusyError, SamplingError
from src.generation import (
    GenerationCancellation,
    GenerationOutput,
    TextGenerator,
    TextIteratorStreamer,
    sample_next_token,
)
from src.ui.services.inference_service import InferenceService


class RecordingTokenizer:
    eos_token_id = None

    def encode(self, text: str) -> List[int]:
        return list(range(len(text)))

    def decode(self, tokens: List[int]) -> str:
        return "".join(chr(ord("a") + (token % 26)) for token in tokens)


class RecordingModel(nn.Module):
    def __init__(self, block_size: int = 4, next_token: int = 1) -> None:
        super().__init__()
        self.block_size = block_size
        self.next_token = next_token
        self.inputs: List[List[int]] = []

    def forward(self, x: torch.Tensor, use_cache: bool = False):
        self.inputs.append(x[0].detach().cpu().tolist())
        vocab_size = max(32, self.next_token + 1)
        logits = torch.full((x.size(0), x.size(1), vocab_size), -100.0)
        logits[:, -1, self.next_token] = 100.0
        return logits, None


def _service_without_assets(tmp_path, *, max_generation_sessions: int = 2) -> InferenceService:
    return InferenceService(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cpu",
        max_generation_sessions=max_generation_sessions,
    )


def test_generation_config_zero_top_p_disables_filter_and_validates() -> None:
    config = GenerationConfig(top_k=0, top_p=0.0)
    config.validate()

    assert config.top_k == 0
    assert config.top_p == 0.0


def test_text_generator_truncates_prompt_before_device_and_reports_context_metadata() -> None:
    tokenizer = RecordingTokenizer()
    model = RecordingModel(block_size=4, next_token=1)
    generator = TextGenerator(model, tokenizer, device="cpu")

    output = generator.generate(
        "abcdefghij",
        config=GenerationConfig(max_new_tokens=1, temperature=0.0),
        return_output=True,
    )

    assert isinstance(output, GenerationOutput)
    assert model.inputs[0] == [6, 7, 8, 9]
    assert output.prompt_tokens_input == 10
    assert output.prompt_tokens_used == 4
    assert output.prompt_truncated is True


def test_text_generator_uses_tokenizer_eos_when_config_does_not_override_it() -> None:
    class EosTokenizer(RecordingTokenizer):
        eos_token_id = 5

    output = TextGenerator(
        RecordingModel(block_size=8, next_token=5), EosTokenizer(), device="cpu"
    ).generate(
        "abcd",
        config=GenerationConfig(max_new_tokens=4, temperature=0.0),
        return_output=True,
    )

    assert isinstance(output, GenerationOutput)
    assert output.finish_reason == "eos_token"
    assert output.tokens_generated == 0


def test_text_generator_cancellation_stops_before_next_model_step() -> None:
    cancellation = GenerationCancellation()
    cancellation.cancel()
    model = RecordingModel(block_size=8, next_token=1)

    output = TextGenerator(model, RecordingTokenizer(), device="cpu").generate(
        "abcd",
        config=GenerationConfig(max_new_tokens=20, temperature=0.0),
        cancellation=cancellation,
        return_output=True,
    )

    assert isinstance(output, GenerationOutput)
    assert output.finish_reason == "cancelled"
    assert model.inputs == []


def test_generation_hot_loop_does_not_rebuild_full_history_with_torch_cat(monkeypatch) -> None:
    model = RecordingModel(block_size=16, next_token=1)
    generator = TextGenerator(model, RecordingTokenizer(), device="cpu")

    def forbidden_cat(*args, **kwargs):
        raise AssertionError("generation hot loop must not torch.cat the full token history")

    monkeypatch.setattr(torch, "cat", forbidden_cat)
    output = generator.generate(
        "abcd",
        config=GenerationConfig(
            max_new_tokens=3,
            temperature=0.0,
            repetition_penalty=1.1,
        ),
        return_output=True,
    )

    assert isinstance(output, GenerationOutput)
    assert output.tokens_generated == 3


def test_sampling_nan_is_reported_as_typed_sampling_error() -> None:
    with pytest.raises(SamplingError):
        sample_next_token(torch.tensor([[float("nan"), float("nan")]]))


def test_text_iterator_streamer_timeout_is_polling_not_queue_empty_leak() -> None:
    streamer = TextIteratorStreamer(timeout=0.01)

    def finish_later() -> None:
        time.sleep(0.04)
        streamer.on_finish()

    thread = threading.Thread(target=finish_later)
    thread.start()
    assert list(streamer) == []
    thread.join(timeout=1.0)
    assert not thread.is_alive()


def test_stream_close_cancels_worker_and_releases_admission(tmp_path) -> None:
    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    class CancellableGenerator:
        def __init__(self) -> None:
            self.started = threading.Event()
            self.finished = threading.Event()

        def generate(
            self,
            prompt,
            config,
            streamer,
            return_output=False,
            cancellation=None,
        ):
            self.started.set()
            try:
                while cancellation is None or not cancellation.is_cancelled():
                    time.sleep(0.005)
            finally:
                streamer.on_finish()
                self.finished.set()
            return GenerationOutput(
                text=prompt,
                prompt=prompt,
                generated_text="",
                token_ids=[],
                tokens_generated=0,
                tokens_per_second=0.0,
                elapsed_time_sec=0.0,
                finish_reason="cancelled",
            )

    service = _service_without_assets(tmp_path, max_generation_sessions=1)
    generator = CancellableGenerator()
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = generator  # type: ignore[assignment]

    stream = service.stream_generate("A", GenerationConfig(max_new_tokens=100))
    first = next(stream)
    assert json.loads(first.removeprefix("data: ").strip())["type"] == "start"
    assert generator.started.wait(timeout=1.0)

    stream.close()
    assert generator.finished.wait(timeout=1.0)

    replacement = service.begin_generation("B", GenerationConfig(max_new_tokens=1))
    replacement.close()


def test_generation_admission_is_bounded_before_worker_creation(tmp_path) -> None:
    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    class NoopGenerator:
        def generate(self, *args, **kwargs):
            raise AssertionError("sessions are intentionally not started in this test")

    service = _service_without_assets(tmp_path, max_generation_sessions=2)
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = NoopGenerator()  # type: ignore[assignment]

    first = service.begin_generation("A", GenerationConfig(max_new_tokens=1))
    second = service.begin_generation("B", GenerationConfig(max_new_tokens=1))
    try:
        with pytest.raises(GenerationBusyError):
            service.begin_generation("C", GenerationConfig(max_new_tokens=1))
    finally:
        first.close()
        second.close()


def test_request_backend_snapshot_does_not_mutate_global_backend(tmp_path) -> None:
    tokenizer = RecordingTokenizer()
    model = RecordingModel(block_size=8, next_token=1)
    service = _service_without_assets(tmp_path)
    service.tokenizer = tokenizer  # type: ignore[assignment]
    service.model = model  # type: ignore[assignment]
    service.generator = TextGenerator(model, tokenizer, device="cpu")
    service.current_backend = "local"

    events = [
        json.loads(item.removeprefix("data: ").strip())
        for item in service.stream_generate(
            "A", GenerationConfig(max_new_tokens=1, temperature=0.0), backend="pytorch"
        )
    ]

    assert service.current_backend == "local"
    assert next(event for event in events if event["type"] == "done")["type"] == "done"


def test_alternate_backend_factory_waits_for_execution_slot(tmp_path) -> None:
    from src.generation import BaseGenerator, GeneratorRegistry

    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    factory_called = threading.Event()

    class DeferredFactoryGenerator(BaseGenerator):
        @classmethod
        def from_inference_context(cls, *, model, tokenizer, device):
            factory_called.set()
            return cls()

        def generate(
            self,
            prompt,
            config=None,
            sampler=None,
            streamer=None,
            cancellation=None,
            return_output=False,
            **kwargs,
        ) -> Any:
            assert streamer is not None
            streamer.on_finish()
            output = GenerationOutput(
                text=prompt,
                prompt=prompt,
                generated_text="",
                token_ids=[],
                tokens_generated=0,
                tokens_per_second=0.0,
                elapsed_time_sec=0.0,
                finish_reason="length",
            )
            return output if return_output else output.text

    name = "deferred-factory-test"
    original = dict(GeneratorRegistry._registry)
    service = _service_without_assets(tmp_path)
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.model = object()  # type: ignore[assignment]
    service.generator = DeferredFactoryGenerator()
    service.current_backend = "local"

    GeneratorRegistry.register(name)(DeferredFactoryGenerator)
    service._generation_lock.acquire()
    session = None
    consumer = None
    try:
        session = service.begin_generation("A", GenerationConfig(max_new_tokens=1), backend=name)
        assert not factory_called.is_set()

        consumer = threading.Thread(target=lambda: list(session.iter_sse()))
        consumer.start()
        time.sleep(0.08)
        assert not factory_called.is_set()

        service._generation_lock.release()
        consumer.join(timeout=1.0)
        assert not consumer.is_alive()
        assert factory_called.is_set()
    finally:
        if service._generation_lock.locked():
            service._generation_lock.release()
        if session is not None:
            session.close()
        if consumer is not None:
            consumer.join(timeout=1.0)
        GeneratorRegistry._registry.clear()
        GeneratorRegistry._registry.update(original)


def test_stop_words_are_encoded_from_the_session_tokenizer_snapshot(tmp_path) -> None:
    class TokenizerA:
        eos_token_id = None

        def encode(self, text):
            return [1, 2] if text == "ab" else [1]

    class TokenizerB:
        eos_token_id = None

        def encode(self, text):
            return [9, 9]

    captured = {}

    class CapturingGenerator:
        def generate(self, prompt, config, streamer, return_output=False, cancellation=None):
            captured["stop_sequences"] = config.stop_sequences
            streamer.on_finish()
            return GenerationOutput(
                text=prompt,
                prompt=prompt,
                generated_text="",
                token_ids=[],
                tokens_generated=0,
                tokens_per_second=0.0,
                elapsed_time_sec=0.0,
                finish_reason="length",
            )

    service = _service_without_assets(tmp_path)
    service.tokenizer = TokenizerA()  # type: ignore[assignment]
    service.generator = CapturingGenerator()  # type: ignore[assignment]
    session = service.begin_generation("A", GenerationConfig(max_new_tokens=1), stop_words=["ab"])
    service.tokenizer = TokenizerB()  # type: ignore[assignment]

    list(session.iter_sse())

    assert captured["stop_sequences"] == [[1, 2]]


def test_checkpoint_and_global_backend_mutation_are_rejected_while_session_is_live(
    tmp_path,
) -> None:
    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    class NoopGenerator:
        pass

    service = _service_without_assets(tmp_path)
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = NoopGenerator()  # type: ignore[assignment]
    session = service.begin_generation("A", GenerationConfig(max_new_tokens=1))
    try:
        with pytest.raises(GenerationBusyError):
            service.set_backend("local")
        with pytest.raises(GenerationBusyError):
            service.load_checkpoint(str(tmp_path / "missing.pt"))
    finally:
        session.close()


def test_done_payload_uses_authoritative_generation_output(tmp_path) -> None:
    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    class DivergentGenerator:
        def generate(self, prompt, config, streamer, return_output=False, cancellation=None):
            streamer.on_token("stream")
            streamer.on_finish()
            return GenerationOutput(
                text=prompt + "canonical",
                prompt=prompt,
                generated_text="canonical",
                token_ids=[1, 2],
                tokens_generated=2,
                tokens_per_second=2.0,
                elapsed_time_sec=1.0,
                finish_reason="length",
                prompt_tokens_input=10,
                prompt_tokens_used=4,
                prompt_truncated=True,
            )

    service = _service_without_assets(tmp_path)
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = DivergentGenerator()  # type: ignore[assignment]

    events = [
        json.loads(item.removeprefix("data: ").strip())
        for item in service.stream_generate("A", GenerationConfig(max_new_tokens=1))
    ]
    done = next(event for event in events if event["type"] == "done")

    assert done["full_text"] == "Acanonical"
    assert done["generated_text"] == "canonical"
    assert done["finish_reason"] == "length"
    assert done["prompt_truncated"] is True
    assert done["prompt_tokens_input"] == 10
    assert done["prompt_tokens_used"] == 4


def test_generator_registry_does_not_hide_builtin_import_failures(monkeypatch) -> None:
    from src.generation.registry import GeneratorRegistry

    original = dict(GeneratorRegistry._registry)
    try:
        GeneratorRegistry._registry.clear()

        def explode(name: str):
            raise RuntimeError("broken builtin import")

        monkeypatch.setattr("src.generation.registry.importlib.import_module", explode)
        with pytest.raises(RuntimeError, match="broken builtin import"):
            GeneratorRegistry.list_generators()
    finally:
        GeneratorRegistry._registry.clear()
        GeneratorRegistry._registry.update(original)


def test_text_generator_rejects_empty_prompt_with_typed_generation_error() -> None:
    from src.core.exceptions import EmptyPromptError

    generator = TextGenerator(RecordingModel(), RecordingTokenizer(), device="cpu")
    with pytest.raises(EmptyPromptError):
        generator.generate("   ", config=GenerationConfig(max_new_tokens=1))


def test_request_backend_uses_backend_inference_factory_hook(tmp_path) -> None:
    from src.generation import BaseGenerator, GeneratorRegistry

    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    class FactoryGenerator(BaseGenerator):
        def __init__(self, marker: str) -> None:
            self.marker = marker

        @classmethod
        def from_inference_context(cls, *, model, tokenizer, device):
            return cls(marker=f"{device}:{type(model).__name__}")

        def generate(
            self,
            prompt,
            config=None,
            sampler=None,
            streamer=None,
            cancellation=None,
            return_output=False,
            **kwargs,
        ) -> Any:
            assert streamer is not None
            streamer.on_token(self.marker)
            streamer.on_finish()
            output = GenerationOutput(
                text=prompt + self.marker,
                prompt=prompt,
                generated_text=self.marker,
                token_ids=[1],
                tokens_generated=1,
                tokens_per_second=1.0,
                elapsed_time_sec=1.0,
                finish_reason="length",
            )
            return output if return_output else output.text

    name = "factory-hook-test"
    original = dict(GeneratorRegistry._registry)
    try:
        GeneratorRegistry.register(name)(FactoryGenerator)
        service = _service_without_assets(tmp_path)
        service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
        service.model = object()  # type: ignore[assignment]
        service.generator = FactoryGenerator("current")
        service.current_backend = "local"

        events = [
            json.loads(item.removeprefix("data: ").strip())
            for item in service.stream_generate(
                "A", GenerationConfig(max_new_tokens=1), backend=name
            )
        ]

        done = next(event for event in events if event["type"] == "done")
        assert done["generated_text"] == "cpu:object"
        assert service.current_backend == "local"
    finally:
        GeneratorRegistry._registry.clear()
        GeneratorRegistry._registry.update(original)


def test_generator_registry_rejects_backend_without_cancellation_contract() -> None:
    from src.core.exceptions import SignatureMismatchError
    from src.generation import BaseGenerator, GeneratorRegistry

    class NonCancellableGenerator(BaseGenerator):
        def generate(  # pyright: ignore[reportIncompatibleMethodOverride]
            self,
            prompt,
            config=None,
            sampler=None,
            streamer=None,
            return_output=False,
        ):
            return prompt

    original = dict(GeneratorRegistry._registry)
    try:
        with pytest.raises(SignatureMismatchError, match="cancellation"):
            GeneratorRegistry.register("non-cancellable-test")(NonCancellableGenerator)
    finally:
        GeneratorRegistry._registry.clear()
        GeneratorRegistry._registry.update(original)


def test_generation_streaming_response_closes_session_on_asgi_send_disconnect() -> None:
    import asyncio

    from starlette.requests import ClientDisconnect

    from src.ui.responses import GenerationStreamingResponse
    from src.ui.services.generation_session import GenerationSession

    class FakeSession:
        def __init__(self) -> None:
            self.close_count = 0

        def iter_sse(self):
            yield 'data: {"type":"start"}\n\n'

        def close(self) -> None:
            self.close_count += 1

    fake_session = FakeSession()
    session = cast(GenerationSession, fake_session)
    response = GenerationStreamingResponse(session=session)

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.body":
            raise OSError("client disconnected")

    scope = {
        "type": "http",
        "asgi": {"spec_version": "2.4"},
        "method": "GET",
        "path": "/api/generate/stream",
        "headers": [],
    }

    with pytest.raises(ClientDisconnect):
        asyncio.run(response(scope, receive, send))

    assert fake_session.close_count == 1


def test_text_generator_does_not_use_incremental_cache_when_forward_lacks_use_cache() -> None:
    class ResetOnlyModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.block_size = 8
            self.inputs: List[List[int]] = []

        def reset_kv_cache(self) -> None:
            pass

        def forward(self, x: torch.Tensor):
            self.inputs.append(x[0].detach().cpu().tolist())
            logits = torch.full((x.size(0), x.size(1), 32), -100.0)
            logits[:, -1, 1] = 100.0
            return logits, None

    model = ResetOnlyModel()
    generator = TextGenerator(model, RecordingTokenizer(), device="cpu")

    generator.generate(
        "abcd",
        config=GenerationConfig(max_new_tokens=2, temperature=0.0, use_cache=True),
    )

    assert model.inputs == [[0, 1, 2, 3], [0, 1, 2, 3, 1]]


def test_repetition_penalty_only_receives_last_step_logits(monkeypatch) -> None:
    import src.generation.generator as generator_module

    seen_shapes = []

    def recording_penalty(logits, generated_tokens, penalty=1.0):
        seen_shapes.append(tuple(logits.shape))
        return logits

    monkeypatch.setattr(generator_module, "apply_repetition_penalty", recording_penalty)
    generator = TextGenerator(RecordingModel(block_size=8), RecordingTokenizer(), device="cpu")

    generator.generate(
        "abcd",
        config=GenerationConfig(
            max_new_tokens=1,
            temperature=0.0,
            repetition_penalty=1.1,
        ),
    )

    assert seen_shapes == [(1, 32)]


def test_checkpoint_load_stages_checkpoint_on_cpu_before_device_commit(
    tmp_path, monkeypatch
) -> None:
    from src.data.tokenizers import CharTokenizer
    from src.data.tokenizers.base import get_tokenizer_identity
    from src.generation import GeneratorRegistry
    from src.models.registry import ModelRegistry

    tokenizer = CharTokenizer(vocab=list("abcd"))
    vocab_path = tmp_path / "vocab.json"
    tokenizer.save_vocab(str(vocab_path))
    checkpoint_path = tmp_path / "model.pt"
    torch.save(
        {
            "checkpoint_version": 2,
            "model_state_dict": {},
            "config": {"model": {"name": "minigpt", "vocab_size": tokenizer.vocab_size}},
            "tokenizer_identity": get_tokenizer_identity(tokenizer),
        },
        checkpoint_path,
    )

    class FakeModel(nn.Module):
        def to(self, *args, **kwargs):
            return self

        def eval(self):
            return self

    class FakeGenerator:
        pass

    service = InferenceService(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(vocab_path),
        device="cpu",
    )
    service.device_str = "cuda:0"

    real_load = torch.load
    load_calls = []

    def recording_load(*args, **kwargs):
        load_calls.append(kwargs.copy())
        safe_kwargs = dict(kwargs)
        safe_kwargs["map_location"] = "cpu"
        return real_load(*args, **safe_kwargs)

    monkeypatch.setattr("src.ui.services.inference_service.torch.load", recording_load)
    monkeypatch.setattr(ModelRegistry, "create", lambda *args, **kwargs: FakeModel())
    monkeypatch.setattr(
        GeneratorRegistry,
        "create_for_inference",
        lambda *args, **kwargs: FakeGenerator(),
    )

    service.load_checkpoint(str(checkpoint_path))

    assert load_calls
    assert load_calls[0].get("map_location") == "cpu"


def test_checkpoint_swap_offloads_previous_model_before_new_device_move(
    tmp_path, monkeypatch
) -> None:
    from src.data.tokenizers import CharTokenizer
    from src.data.tokenizers.base import get_tokenizer_identity
    from src.generation import GeneratorRegistry
    from src.models.registry import ModelRegistry

    tokenizer = CharTokenizer(vocab=list("abcd"))
    vocab_path = tmp_path / "vocab.json"
    tokenizer.save_vocab(str(vocab_path))
    checkpoint_path = tmp_path / "model.pt"
    torch.save(
        {
            "checkpoint_version": 2,
            "model_state_dict": {},
            "config": {"model": {"name": "minigpt", "vocab_size": tokenizer.vocab_size}},
            "tokenizer_identity": get_tokenizer_identity(tokenizer),
        },
        checkpoint_path,
    )

    moves = []

    class TrackingModel(nn.Module):
        def __init__(self, name: str) -> None:
            super().__init__()
            self.name = name

        def to(self, device, *args, **kwargs):
            moves.append((self.name, str(device)))
            return self

        def eval(self):
            return self

    class FakeGenerator:
        pass

    old_model = TrackingModel("old")
    new_model = TrackingModel("new")
    service = InferenceService(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(vocab_path),
        device="cpu",
    )
    service.configured_device = "cuda:0"
    service.device_str = "cuda:0"
    monkeypatch.setattr(
        "src.ui.services.inference_service.resolve_device", lambda requested: requested
    )
    service.model = old_model  # type: ignore[assignment]
    service.tokenizer = tokenizer
    service.generator = FakeGenerator()  # type: ignore[assignment]

    monkeypatch.setattr(ModelRegistry, "create", lambda *args, **kwargs: new_model)
    monkeypatch.setattr(
        GeneratorRegistry,
        "create_for_inference",
        lambda *args, **kwargs: FakeGenerator(),
    )

    service.load_checkpoint(str(checkpoint_path))

    assert moves.index(("old", "cpu")) < moves.index(("new", "cuda:0"))
    assert service.model is new_model


def test_checkpoint_swap_restores_previous_model_if_new_device_move_fails(
    tmp_path, monkeypatch
) -> None:
    from src.data.tokenizers import CharTokenizer
    from src.data.tokenizers.base import get_tokenizer_identity
    from src.models.registry import ModelRegistry

    tokenizer = CharTokenizer(vocab=list("abcd"))
    vocab_path = tmp_path / "vocab.json"
    tokenizer.save_vocab(str(vocab_path))
    checkpoint_path = tmp_path / "model.pt"
    torch.save(
        {
            "checkpoint_version": 2,
            "model_state_dict": {},
            "config": {"model": {"name": "minigpt", "vocab_size": tokenizer.vocab_size}},
            "tokenizer_identity": get_tokenizer_identity(tokenizer),
        },
        checkpoint_path,
    )

    moves = []

    class OldModel(nn.Module):
        def to(self, device, *args, **kwargs):
            moves.append(("old", str(device)))
            return self

    class FailingNewModel(nn.Module):
        def to(self, device, *args, **kwargs):
            moves.append(("new", str(device)))
            if str(device) == "cuda:0":
                raise RuntimeError("simulated device OOM")
            return self

        def eval(self):
            return self

    class OldGenerator:
        pass

    old_model = OldModel()
    old_generator = OldGenerator()
    service = InferenceService(
        checkpoint_dir=str(tmp_path),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(vocab_path),
        device="cpu",
    )
    service.configured_device = "cuda:0"
    service.device_str = "cuda:0"
    monkeypatch.setattr(
        "src.ui.services.inference_service.resolve_device", lambda requested: requested
    )
    service.model = old_model  # type: ignore[assignment]
    service.tokenizer = tokenizer
    service.generator = old_generator  # type: ignore[assignment]
    service.current_checkpoint_path = "old.pt"

    monkeypatch.setattr(ModelRegistry, "create", lambda *args, **kwargs: FailingNewModel())

    with pytest.raises(RuntimeError, match="simulated device OOM"):
        service.load_checkpoint(str(checkpoint_path))

    assert moves == [("old", "cpu"), ("new", "cuda:0"), ("new", "cpu"), ("old", "cuda:0")]
    assert service.model is old_model
    assert service.generator is old_generator
    assert service.current_checkpoint_path == "old.pt"


def test_repetition_penalty_ignores_prompt_tokens_outside_effective_context() -> None:
    class PrefixSensitiveModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.block_size = 4

        def forward(self, x: torch.Tensor, use_cache: bool = False):
            logits = torch.full((x.size(0), x.size(1), 16), -100.0)
            logits[:, -1, 0] = 10.0
            logits[:, -1, 12] = 9.0
            return logits, None

    output = TextGenerator(PrefixSensitiveModel(), RecordingTokenizer(), device="cpu").generate(
        "abcdefghij",
        config=GenerationConfig(
            max_new_tokens=1,
            temperature=0.0,
            repetition_penalty=2.0,
        ),
        return_output=True,
    )

    assert isinstance(output, GenerationOutput)
    assert output.prompt_truncated is True
    assert output.token_ids == [0]


def test_begin_generation_rejects_empty_prompt_before_admission(tmp_path) -> None:
    from src.core.exceptions import EmptyPromptError

    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    class NoopGenerator:
        def generate(self, *args, **kwargs):
            raise AssertionError("empty prompt must be rejected before worker creation")

    service = _service_without_assets(tmp_path, max_generation_sessions=1)
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = NoopGenerator()  # type: ignore[assignment]

    with pytest.raises(EmptyPromptError):
        service.begin_generation("   ", GenerationConfig(max_new_tokens=1))

    replacement = service.begin_generation("ok", GenerationConfig(max_new_tokens=1))
    replacement.close()


def test_inference_generation_reservation_blocks_training_and_releases_on_close(tmp_path) -> None:
    from src.core.exceptions import AcceleratorBusyError
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator

    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    class NoopGenerator:
        def generate(self, *args, **kwargs):
            raise AssertionError("session is intentionally never started")

    coordinator = AcceleratorCoordinator()
    service = InferenceService(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cuda",
        accelerator_coordinator=coordinator,
    )
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = NoopGenerator()  # type: ignore[assignment]

    session = service.begin_generation("A", GenerationConfig(max_new_tokens=1))
    try:
        with pytest.raises(AcceleratorBusyError):
            coordinator.reserve_training("cuda")
    finally:
        session.close()

    coordinator.reserve_training("cuda")
    coordinator.release_training("cuda")


def test_inference_generation_is_rejected_while_training_owns_accelerator(tmp_path) -> None:
    from src.core.exceptions import AcceleratorBusyError
    from src.ui.services.accelerator_coordinator import AcceleratorCoordinator

    class DummyTokenizer:
        eos_token_id = None

        def encode(self, text):
            return [1]

    coordinator = AcceleratorCoordinator()
    service = InferenceService(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        default_checkpoint=str(tmp_path / "missing.pt"),
        vocab_path=str(tmp_path / "missing_vocab.json"),
        device="cuda",
        accelerator_coordinator=coordinator,
    )
    service.tokenizer = DummyTokenizer()  # type: ignore[assignment]
    service.generator = object()  # type: ignore[assignment]
    coordinator.reserve_training("cuda")
    try:
        with pytest.raises(AcceleratorBusyError):
            service.begin_generation("A", GenerationConfig(max_new_tokens=1))
    finally:
        coordinator.release_training("cuda")
