# Adapter + Application Freeze Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze Adapter + Application as a stable outer communication boundary: graph construction is inert, every adapter action reaches a canonical Application gateway/use case, runtime/capability mechanics stay inward, and architecture tests reject new boundary regressions by default.

**Architecture:** Keep the existing modular-monolith structure and harden it incrementally instead of replacing it. Composition wires concrete implementations only; public outer code sees exactly five gateways; ordering-sensitive training/inference workflows are coordinated in Application; typed Application-owned contracts carry policy/state while capability-specific objects stay behind ports or opaque handles.

**Tech Stack:** Python >=3.10 (project Pyright target 3.11), FastAPI/Starlette, PyYAML, pytest, Ruff/Pyright quality gates, React 19 + TypeScript + Vite frontend compatibility verification.

**Spec:** `docs/superpowers/specs/2026-09-10-adapter-application-freeze-hardening-design-R3.md`

## Global Constraints

- R3 wins over older Adapter/Application design wording when they conflict.
- Preserve HTTP route names, normal response/SSE shapes, CLI command names/options, and normal user-visible behavior.
- Adapter owns transport conversion, rendering, external I/O, and transport-specific security checks only.
- Application owns orchestration and product/use-case policy only.
- Core/capability modules own algorithms, runtime objects, resource mechanics, concrete cleaner/tokenizer/dataset/trainer/model behavior.
- Composition owns wiring only. `build_application_services()` must not read/activate config, inspect checkpoint existence, load tokenizer/model/checkpoint, reserve accelerator resources, or start workers.
- Do not introduce a command bus, service locator, second DI container, or speculative one-method interfaces.
- CLI synchronous training remains synchronous; Web training remains background. They share transaction policy, not execution mechanics.
- A command-specific config semantic snapshot is resolved once inside its Application transaction. A separate read-only logging-settings resolve is allowed only when it does not activate runtime/Application state.
- Managed checkpoint membership/resolution/pinning is shared Application policy behind its checkpoint port. Do not duplicate it in HTTP/CLI.
- Pre-commit training failure rolls back reversible inference handoff/resource reservation. After training ownership commits, failures release training ownership but do not automatically restore inference residency.
- Application may carry an opaque typed prepared-data handle, but must never inspect or expose train/val tensors, tokenizer instances, cleaner instances, or capability-specific fields.
- Application training state/events keep raw metrics and lifecycle facts. UI owns rounding, display timestamps, localized status messages, JSON/SSE framing, and heartbeat frames.
- Per task: write/adjust focused tests first, prove the intended RED failure, implement only the minimum production change, then run focused GREEN tests.
- Do not run broad cleanup or unrelated core refactors while executing this plan.
- Do not begin broad core cleanup until all four wave exit gates and final verification pass.

---

# File/Responsibility Map Before Implementation

The following structure is the target ownership map. Create only the files listed when their task begins; do not pre-scaffold later tasks.

| File                                       | Final responsibility                                                                                        |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `main.py`                                  | Two-line/bootstrap-only executable entry; no parser, command orchestration, composition, or inner imports.  |
| `src/adapters/cli/entrypoint.py`           | CLI parser, command dispatch, terminal input/output loop, Uvicorn launch, process exit mapping.             |
| `src/adapters/cli/diagnostics.py`          | Render already-computed diagnostics/gate report data only.                                                  |
| `src/adapters/cli/runtime.py`              | Process logging I/O only.                                                                                   |
| `src/application/services.py`              | Frozen container containing exactly five public gateways.                                                   |
| `src/application/config/gateway.py`        | Adapter-safe config reads/writes/logging settings without leaking `EngineConfig`.                           |
| `src/application/inference/contracts.py`   | Adapter-safe generation/preparation commands/results and Application-owned inference ports.                 |
| `src/application/inference/service.py`     | Inference use-case orchestration; constructor is inert.                                                     |
| `src/application/inference/gateway.py`     | Adapter-facing inference facade only.                                                                       |
| `src/application/inference/preferences.py` | Canonical config-backed inference preferences only; no hidden device authority.                             |
| `src/application/diagnostics/gateway.py`   | Adapter-facing diagnostics facade.                                                                          |
| `src/application/explorer/gateway.py`      | Adapter-facing explorer facade.                                                                             |
| `src/application/training/transaction.py`  | Shared training planning/pinning/handoff/admission/config-commit transaction for sync/background modes.     |
| `src/application/training/service.py`      | Plan, prepare and execute one already-admitted training run; no cross-use-case handoff policy.              |
| `src/application/training/background.py`   | Background lifecycle/state machine only, using typed raw facts/events.                                      |
| `src/application/training/contracts.py`    | Typed commands/results/state/events/resource/runtime contracts.                                             |
| `src/application/data/contracts.py`        | Pure data-preparation spec, opaque handle base, and preparation port.                                       |
| `src/application/data/policy.py`           | Pure Application policy that selects explicit cleaner fallback intent.                                      |
| `src/composition/root.py`                  | Concrete graph wiring only.                                                                                 |
| `src/composition/training_data.py`         | Bridge pure data-preparation spec to concrete data capability and wrap concrete bundle in an opaque handle. |
| `src/composition/training_runtime.py`      | Unwrap opaque prepared-data handle and delegate concrete trainer preparation/execution.                     |
| `src/data/api.py`                          | Stable capability facade executing cleaner/tokenizer/dataset/export mechanics from pure policy values.      |
| `src/training/events.py`                   | Subscriber buffering/fan-out only; no heartbeat or SSE semantics.                                           |
| `src/ui/app.py`                            | One inert graph per serving worker + explicit best-effort inference startup preparation.                    |
| `src/ui/training_presenter.py`             | Map typed raw training state/events to the existing JSON/SSE payload shape and presentation formatting.     |
| `src/ui/responses.py`                      | SSE framing, heartbeat cadence and close-on-disconnect behavior.                                            |
| `scripts/check_architecture.py`            | Dependency matrix plus positive outer→Application public-surface enforcement.                               |

---

# Execution Setup — Record the exact baseline before Task 1

Before modifying production code in the execution worktree, record the starting commit once:

```bash
git rev-parse HEAD > .git/adapter-application-freeze-baseline
cat .git/adapter-application-freeze-baseline
git status --short
```

Expected: the worktree is clean, and `.git/adapter-application-freeze-baseline` contains the exact commit from which this plan starts. This file is Git metadata/local execution state and must not be committed. Task 21 uses it to produce an exact patch without guessing a baseline.

# Wave 1 — Inert Construction and Process Ownership

### Task 1: Make production composition config-inert

**Files:**

- Modify: `src/application/config/gateway.py:27-32`
- Modify: `src/composition/root.py:36-200`
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_architecture.py`

**Interfaces:**

- Produces: `ConfigGateway.logging_settings(request: ConfigRequest | None = None) -> LoggingSettings`
- Produces: `build_application_services(*, backend: str = "local", max_generation_sessions: int = 2) -> ApplicationServices`
- Removes from production builder: `config_path`, `overrides`
- Constraint: builder may construct `YamlConfigProvider` and `ConfigurationService`, but may not invoke `load_mapping`, `resolve`, `current`, or `activate` as part of graph construction.

- [x] **Step 1: Add RED tests for graph-construction config purity**

Add focused tests that fail if the provider is read or config is activated while building the graph:

```python
def test_build_application_services_does_not_resolve_or_activate_config(monkeypatch):
    from src.adapters.config import YamlConfigProvider
    from src.composition import build_application_services

    def fail_load(*args, **kwargs):
        raise AssertionError("composition must not read config documents")

    monkeypatch.setattr(YamlConfigProvider, "load_mapping", fail_load)
    services = build_application_services()

    assert services.config.default_path.endswith("configs/truyen_kieu.yaml")
```

Add a separate read-only logging test:

```python
def test_config_gateway_logging_settings_resolves_request_without_activation(tmp_path):
    from src.adapters.config import YamlConfigProvider
    from src.application.config import ConfigGateway, ConfigRequest
    from src.application.config.service import ConfigurationService

    path = tmp_path / "engine.yaml"
    path.write_text("system:\n  log_level: WARNING\n  log_file: logs/x.log\n", encoding="utf-8")
    service = ConfigurationService(YamlConfigProvider(default_path=str(path)))
    gateway = ConfigGateway(service)

    settings = gateway.logging_settings(ConfigRequest())

    assert settings.level == "WARNING"
    assert service._active is None
```

Add an API-shape test in `tests/test_architecture.py` so command config cannot creep back into composition:

```python
def test_production_builder_has_no_command_config_parameters():
    signature = inspect.signature(build_application_services)
    assert "config_path" not in signature.parameters
    assert "overrides" not in signature.parameters
```

- [x] **Step 2: Run RED tests**

Run:

```bash
python -m pytest -q \
  tests/test_application_boundaries.py::test_build_application_services_does_not_resolve_or_activate_config \
  tests/test_application_boundaries.py::test_config_gateway_logging_settings_resolves_request_without_activation
```

Expected: at least the composition test fails because `build_application_services()` currently calls `resolve()` + `activate()`.

- [x] **Step 3: Change `ConfigGateway.logging_settings` to explicit read-only resolution**

Implement this shape:

```python
def logging_settings(self, request: Optional[ConfigRequest] = None) -> LoggingSettings:
    system = self._service.resolve(request).system
    return LoggingSettings(level=str(system.log_level), file=str(system.log_file))
```

Do not call `current()` here; logging bootstrap is allowed to resolve, but must not create active runtime state.

- [x] **Step 4: Remove command config from composition**

In `build_application_services()`:

```python
provider = YamlConfigProvider()
configuration = ConfigurationService(provider)
accelerator = AcceleratorCoordinator()
inference_service = _build_inference_service(
    engine_config=EngineConfig(),
    backend=backend,
    max_generation_sessions=max_generation_sessions,
    accelerator_coordinator=accelerator,
    config_service=configuration,
)
```

Delete the `configuration.resolve(...)` / `configuration.activate(...)` boot path. Keep `EngineConfig()` only as an in-memory construction default; it must not become a second active authority.

- [x] **Step 5: Run focused GREEN tests**

Run:

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_config.py
```

Expected: PASS.

- [x] **Step 6: Commit Task 1**

```bash
git add src/application/config/gateway.py src/composition/root.py tests/test_application_boundaries.py tests/test_architecture.py
git commit -m "refactor: make application composition config inert"
```

---

### Task 2: Remove inference constructor bootstrap and add one explicit preparation transaction

**Files:**

- Modify: `src/application/inference/contracts.py`
- Modify: `src/application/inference/service.py:31-87`
- Modify: `src/application/inference/gateway.py`
- Modify: `tests/application_support.py`
- Modify: `tests/test_inference_service.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

- Produces:

```python
@dataclass(frozen=True)
class InferencePreparationCommand:
    config_request: ConfigRequest = ConfigRequest()
    checkpoint_path: Optional[str] = None
    vocab_path: Optional[str] = None
    backend: Optional[str] = None
    requested_device: Optional[str] = None
    require_managed_checkpoint: bool = False
    strict: bool = True

@dataclass(frozen=True)
class InferencePreparationResult:
    ready: bool
    checkpoint_path: Optional[str]
    backend: str
    configured_device: str
    active_device: str
    warning: Optional[str] = None
```

- Produces: `InferenceGateway.prepare(command: InferencePreparationCommand) -> InferencePreparationResult`
- Produces private service operation `load_checkpoint(..., requested_device: Optional[str] = None)` so preparation can pass transient placement explicitly from this task onward.
- Constructor stores `self._config_service = config_service` for explicit preparation, but constructor invariant remains: no runtime calls to `path_exists`, `load_tokenizer_if_present`, `load_checkpoint`, accelerator reservation, or config-provider read.

- [x] **Step 1: Rewrite eager-start tests into constructor-purity tests**

Replace `test_inference_service_loads_existing_configured_vocab_on_startup` with a spy-port test that asserts **zero calls** during construction:

```python
def test_inference_service_constructor_is_inert():
    runtime = SpyInferenceRuntime()
    service = InferenceService(
        runtime=runtime,
        admission=FakeAdmission(),
        synchronization=FakeSynchronization(),
        accelerator=FakeAccelerator(),
        engine_config=EngineConfig(),
    )

    assert service.get_runtime_state()["current_checkpoint"] is None
    assert runtime.calls == []
```

The spy must record path existence, tokenizer load, checkpoint load and admission/resource calls separately so the failure is diagnostic.

- [x] **Step 2: Add RED tests for strict vs best-effort preparation**

Add tests with a fake runtime where `load_checkpoint()` raises `FileNotFoundError`:

```python
def test_inference_prepare_strict_missing_checkpoint_raises():
    with pytest.raises(FileNotFoundError):
        gateway.prepare(InferencePreparationCommand(checkpoint_path="missing.pt", strict=True))


def test_inference_prepare_best_effort_missing_checkpoint_returns_not_ready():
    result = gateway.prepare(
        InferencePreparationCommand(checkpoint_path="missing.pt", strict=False)
    )
    assert result.ready is False
    assert result.warning
```

Also assert one command resolves exactly one config request, activates that resolved/command-adjusted snapshot exactly once through `apply_engine_config(...)`, and only then derives configured vocab/checkpoint/backend. Use a counting `ConfigurationService` fake so a second provider read is visible.

- [x] **Step 3: Run RED tests**

Run:

```bash
python -m pytest -q \
  tests/test_inference_service.py \
  tests/test_application_boundaries.py -k "inference and (constructor or prepare or composition)"
```

Expected: RED because constructor still performs bootstrap and `prepare` does not exist.

- [x] **Step 4: Make `InferenceService.__init__` state wiring only**

Delete the current constructor block that computes `checkpoint`, calls tokenizer bootstrap, checks path existence and calls `load_checkpoint`. Store the injected configuration service reference only:

```python
self._config_service = config_service
```

`from_engine_config()` must become a pure convenience constructor and must not derive a default checkpoint via a runtime path helper solely to trigger loading. Remove the eager-only `default_checkpoint` constructor parameter once no caller needs it.

In this same task, extend the private service method to accept transient placement:

```python
def load_checkpoint(
    self,
    checkpoint_path: str,
    backend: Optional[str] = None,
    *,
    require_managed: bool = False,
    requested_device: Optional[str] = None,
) -> None:
    ...
```

For now this parameter threads through the existing placement logic without changing canonical device authority; Task 17 removes the legacy `_device_override` storage and makes this separation complete.

- [x] **Step 5: Implement explicit preparation**

Implement the transaction in this order:

```python
def prepare(self, command: InferencePreparationCommand) -> InferencePreparationResult:
    config = (
        self._config_service.resolve(command.config_request)
        if self._config_service is not None
        else self.get_engine_config()
    )
    if command.vocab_path:
        config = config.copy(data=config.data.copy(vocab_file=command.vocab_path))
    self.apply_engine_config(config)

    checkpoint = command.checkpoint_path or self.resolve_checkpoint_path(
        self.checkpoint_name,
        filename_only=True,
    )
    backend = command.backend or self.current_backend
    try:
        self.load_checkpoint(
            checkpoint,
            backend=backend,
            require_managed=command.require_managed_checkpoint,
            requested_device=command.requested_device,
        )
    except Exception as exc:
        if command.strict:
            raise
        logger.warning("Default inference preparation failed: %s", exc)
        return InferencePreparationResult(
            ready=False,
            checkpoint_path=self.current_checkpoint_path,
            backend=self.current_backend,
            configured_device=self.configured_device,
            active_device=self.device_str,
            warning=str(exc),
        )
    return InferencePreparationResult(
        ready=True,
        checkpoint_path=self.current_checkpoint_path,
        backend=self.current_backend,
        configured_device=self.configured_device,
        active_device=self.device_str,
    )
```

Use `requested_device` as an operation input; do not persist it as a hidden config override. Task 17 will finish removing the legacy override storage.

- [x] **Step 6: Expose only the preparation command/result through the public inference package/gateway**

Add `InferencePreparationCommand`, `InferencePreparationResult`, and `InferenceGateway.prepare`. Do not expose `prepare_for_training` or any cross-use-case handoff token.

- [x] **Step 7: Run focused GREEN tests**

Run:

```bash
python -m pytest -q tests/test_inference_service.py tests/test_application_boundaries.py
```

Expected: PASS.

- [x] **Step 8: Commit Task 2**

```bash
git add src/application/inference tests/application_support.py tests/test_inference_service.py tests/test_application_boundaries.py
git commit -m "refactor: make inference preparation explicit"
```

---

### Task 3: Make Web startup own best-effort default inference preparation

**Files:**

- Modify: `src/ui/app.py`
- Modify: `tests/test_ui.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

- Consumes: `InferenceGateway.prepare(InferencePreparationCommand(..., strict=False))`
- Produces: one Application graph per `create_app()` instance; one default preparation call per TestClient/server lifespan.

- [ ] **Step 1: Add RED lifespan tests**

Replace the old assertion that `create_app()` immediately bootstraps config with two explicit lifecycle assertions:

```python
def test_create_app_construction_does_not_prepare_inference(monkeypatch):
    calls = []
    app = create_app()
    monkeypatch.setattr(app.state.services.inference, "prepare", lambda command: calls.append(command))
    assert calls == []


def test_web_lifespan_prepares_default_inference_once(monkeypatch):
    app = create_app()
    calls = []
    monkeypatch.setattr(
        app.state.services.inference,
        "prepare",
        lambda command: calls.append(command) or InferencePreparationResult(
            ready=False,
            checkpoint_path=None,
            backend="local",
            configured_device="cpu",
            active_device="cpu",
            warning="missing",
        ),
    )
    with TestClient(app):
        pass
    assert len(calls) == 1
    assert calls[0].strict is False
```

Add a missing-checkpoint test proving the server still starts and `/healthz` returns 200.

- [ ] **Step 2: Run RED tests**

Run:

```bash
python -m pytest -q tests/test_ui.py -k "lifespan or bootstrap or healthz"
```

Expected: RED because current startup work happens during construction rather than lifespan.

- [ ] **Step 3: Add explicit FastAPI lifespan preparation**

Use `asynccontextmanager` and keep the graph built exactly once:

```python
@asynccontextmanager
async def _lifespan(app: FastAPI):
    result = app.state.services.inference.prepare(
        InferencePreparationCommand(strict=False)
    )
    if not result.ready and result.warning:
        logger.warning("Inference not ready after startup preparation: %s", result.warning)
    yield
```

Construct `FastAPI(..., lifespan=_lifespan)`, then assign exactly one inert `app.state.services = build_application_services()`.

Do not create another graph inside the lifespan.

- [ ] **Step 4: Update canonical-config bootstrap test**

The config-backed preference assertions must run **inside** `with TestClient(app)` because default config activation is now a startup use case, not graph construction.

- [ ] **Step 5: Run focused GREEN tests**

Run:

```bash
python -m pytest -q tests/test_ui.py -k "bootstrap or lifespan or healthz or config_save_updates_inference"
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add src/ui/app.py tests/test_ui.py tests/test_application_boundaries.py
git commit -m "refactor: move inference bootstrap to web lifespan"
```

---

### Task 4: Make CLI generation strict and stop launcher pre-composition

**Files:**

- Modify: `main.py` temporarily; Task 8 moves the whole implementation under `src/adapters/cli/entrypoint.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

- Consumes: `InferencePreparationCommand`
- Requirement: Adapter still owns interactive `input()`/render loop; it no longer sequences vocab mutation, checkpoint derivation, and checkpoint loading.
- Requirement: `cmd_ui` launches the Uvicorn factory without `_compose()`/`build_application_services()`. The serving worker owns graph construction.
- Removes from public `InferenceGateway` once CLI migration is green: `set_vocab_path` and `configured_checkpoint_path`; manual checkpoint HTTP operations may keep their explicit checkpoint gateway operations.

- [ ] **Step 1: Add RED command-order and launcher-purity tests**

Use a gateway stub that records calls and assert `cmd_generate` performs one `prepare()` before generation:

```python
assert calls[0][0] == "prepare"
assert calls[0][1].checkpoint_path == "chosen.pt"
assert calls[0][1].vocab_path == "chosen.json"
assert calls[0][1].strict is True
assert all(name not in {"set_vocab_path", "configured_checkpoint_path"} for name, *_ in calls)
```

Add a launcher test in the same task:

```python
def test_cmd_ui_does_not_compose_application_graph(monkeypatch):
    monkeypatch.setattr(
        "src.composition.build_application_services",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("launcher composed graph")),
    )
    calls = []
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: calls.append((args, kwargs)))
    cmd_ui(SimpleNamespace(host="127.0.0.1", port=8000, reload=False))
    assert len(calls) == 1
```

- [ ] **Step 2: Run RED test**

```bash
python -m pytest -q tests/test_application_boundaries.py -k "cli_generate or cmd_ui"
```

Expected: RED because `main.py` still sequences `set_vocab_path -> configured_checkpoint_path -> load_checkpoint`.

- [ ] **Step 3: Replace CLI setup with one command**

Build exactly one command:

```python
prepare = InferencePreparationCommand(
    config_request=ConfigRequest.from_values(args.config, args.override),
    checkpoint_path=args.checkpoint,
    vocab_path=args.vocab,
    backend=args.backend,
    strict=True,
)
result = services.inference.prepare(prepare)
backend = result.backend
```

Then keep `_render_generation(...)` per user prompt.

- [ ] **Step 4: Stop command config from flowing into composition**

Change `_compose(args)` to:

```python
services = build_application_services()
settings = services.config.logging_settings(
    ConfigRequest.from_values(getattr(args, "config", None), getattr(args, "override", None))
)
configure_cli_logging(settings, name="ai-train")
return services
```

This preserves config-based CLI logging without activating the command's semantic runtime state during composition.

- [ ] **Step 5: Stop `cmd_ui` from composing and remove superseded public setup primitives**

Change `cmd_ui` so it invokes Uvicorn with the factory target only. It must not call `_compose()` merely to configure logging. If launcher logging is needed before the worker exists, use process-safe/basic logging that does not build the Application graph.

After the CLI no longer uses the two setup primitives, remove these members from `InferenceGateway`:

```python
# remove public facade members
set_vocab_path(...)
configured_checkpoint_path
```

Do not remove `InferenceService.set_vocab_path` yet if inner tests/use cases still need it; the freeze target here is the adapter-facing public gateway. Add a static assertion that neither `src/adapters` nor `src/ui` references the removed public members.

- [ ] **Step 6: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_inference_service.py tests/test_ui.py -k "cli or preparation or config or launcher"
```

Expected: PASS.

- [ ] **Step 7: Wave 1 self-review**

Search for hidden graph/startup execution:

```bash
rg -n "build_application_services\(|load_tokenizer_if_present|path_exists\(|load_checkpoint\(|\.activate\(|\.resolve\(" \
  main.py src/composition src/ui/app.py src/application/inference
```

Manually confirm:

- builder itself does not resolve/activate config;
- constructor does not load tokenizer/checkpoint;
- Web startup is explicit best-effort preparation;
- CLI generate is explicit strict preparation;
- `ui` launcher does not compose a graph; root-file relocation itself is deferred to Task 8.
- outer code no longer references `InferenceGateway.set_vocab_path` or `configured_checkpoint_path`.

- [ ] **Step 8: Commit Task 4**

```bash
git add main.py src/application/inference/gateway.py tests/test_application_boundaries.py
git commit -m "refactor: route cli generation through preparation use case"
```

---

# Wave 2 — Freeze Public Gateway and Guardian Surface

### Task 5: Add DiagnosticsGateway and ExplorerGateway and make `ApplicationServices` symmetric

**Files:**

- Create: `src/application/diagnostics/gateway.py`
- Create: `src/application/explorer/gateway.py`
- Modify: `src/application/diagnostics/__init__.py`
- Modify: `src/application/explorer/__init__.py`
- Modify: `src/application/services.py`
- Modify: `src/composition/root.py`
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_ui.py` only where tests reach `._service`/concrete diagnostics/explorer internals unnecessarily

**Interfaces:**

- Produces: `DiagnosticsGateway`
    - `system()`
    - `estimate(VramEstimateInput)`
    - `scenarios(VramEstimateInput)`
    - `scenarios_from_config(source, overrides=())`
    - `advisor()`
    - `run_quality_gates()`
    - `inspect(...)`
    - `logs(lines=80)`
    - `report(test_tensor_allocation=True)`
- Produces: `ExplorerGateway`
    - `clean(...)`
    - `tokenize(...)`
    - `dataset_sample(source=None)`
    - `export_binary(source=None)`
    - `compare_tokenizers(...)`
- Produces: `ApplicationServices` fields are exactly `ConfigGateway`, `InferenceGateway`, `TrainingGateway`, `DiagnosticsGateway`, `ExplorerGateway`.

- [ ] **Step 1: Add RED public-surface tests**

```python
def test_application_services_contains_only_public_gateways():
    annotations = ApplicationServices.__annotations__
    assert annotations == {
        "config": ConfigGateway,
        "inference": InferenceGateway,
        "training": TrainingGateway,
        "diagnostics": DiagnosticsGateway,
        "explorer": ExplorerGateway,
    }


def test_diagnostics_and_explorer_packages_do_not_export_concrete_services():
    assert "DiagnosticsApplicationService" not in diagnostics.__all__
    assert "ExplorerApplicationService" not in explorer.__all__
```

- [ ] **Step 2: Run RED tests**

```bash
python -m pytest -q tests/test_application_boundaries.py -k "diagnostics or explorer or services"
```

Expected: RED because concrete services are currently exposed.

- [ ] **Step 3: Implement thin but boundary-protecting gateways**

Pattern:

```python
class DiagnosticsGateway:
    def __init__(self, service: DiagnosticsApplicationService) -> None:
        self._service = service

    def run_quality_gates(self) -> dict[str, object]:
        return self._service.run_quality_gates()
```

Repeat explicit methods rather than `__getattr__`; the gateway is the deliberate public contract.

- [ ] **Step 4: Shrink package exports**

`src.application.diagnostics.__all__` must export only adapter-safe DTOs/ports/gateway, e.g.:

```python
__all__ = ["DiagnosticsGateway", "DiagnosticsRuntimePort", "VramEstimateInput"]
```

`src.application.explorer.__all__` should export only `ExplorerGateway` unless an adapter-safe DTO is later introduced.

- [ ] **Step 5: Wire gateways in composition**

Keep concrete service construction in `src/composition/root.py`, then wrap it before returning `ApplicationServices`.

- [ ] **Step 6: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_ui.py -k "diagnostics or explorer or application_services"
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

```bash
git add src/application/diagnostics src/application/explorer src/application/services.py src/composition/root.py tests/test_application_boundaries.py tests/test_ui.py
git commit -m "refactor: expose diagnostics and explorer gateways"
```

---

### Task 6: Make CLI diagnostics functions pure renderers and route quality gates through DiagnosticsGateway

**Files:**

- Modify: `src/adapters/cli/diagnostics.py`
- Modify: `main.py` temporarily; Task 8 moves it
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_diagnostics.py`

**Interfaces:**

- Produces renderer-only functions:

```python
def print_system_report(report: Mapping[str, object]) -> None: ...
def print_scenarios(report: Mapping[str, object]) -> None: ...
def print_inspect(report: Mapping[str, object]) -> None: ...
def print_quality_gates(report: Mapping[str, object]) -> int: ...
```

- Removes: service-accepting renderer signatures and direct `scripts.check_all.main` import from `src/adapters/cli/diagnostics.py`.

- [ ] **Step 1: Rewrite the stale boundary test that currently requires `DiagnosticsApplicationService`**

Replace the historical assertion around line ~609 with:

```python
def test_cli_diagnostics_adapter_renders_data_and_does_not_invoke_application_or_tooling():
    source = Path("src/adapters/cli/diagnostics.py").read_text(encoding="utf-8")
    assert "DiagnosticsApplicationService" not in source
    assert "scripts.check_all" not in source
    assert "services." not in source
```

- [ ] **Step 2: Add renderer unit tests**

Monkeypatch `_render_*` helpers and pass mappings directly. For quality gates, assert exit status comes from `all_passed` and that result rows are rendered without executing gates.

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_application_boundaries.py -k "cli_diagnostics or quality_gate"
```

Expected: RED because renderers still accept the concrete service and `run_quality_gates_cli()` imports the script.

- [ ] **Step 4: Convert CLI command flow to gateway-call then renderer**

Target command shape:

```python
print_system_report(services.diagnostics.report())
print_scenarios(services.diagnostics.scenarios_from_config(args.config, tuple(args.override)))
print_inspect(services.diagnostics.inspect(source=args.config, overrides=tuple(args.override)))
raise SystemExit(print_quality_gates(services.diagnostics.run_quality_gates()))
```

The diagnostics runtime adapter remains the only production adapter importing individual `scripts.check_all` gate functions.

- [ ] **Step 5: Preserve gate terminal semantics**

`print_quality_gates()` must render the existing report fields (`name`, `tool`, `elapsed`, `passed`, `details`, `error_output`) with Rich when present and a plain fallback otherwise, then return `0 if all_passed else 1`.

- [ ] **Step 6: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_diagnostics.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 6**

```bash
git add src/adapters/cli/diagnostics.py main.py tests/test_application_boundaries.py tests/test_diagnostics.py
git commit -m "refactor: make cli diagnostics renderer only"
```

---

### Task 7: Introduce positive outer→Application public-surface enforcement

**Files:**

- Modify: `scripts/check_architecture.py`
- Modify: `tests/test_architecture.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

- Produces a default-deny public-surface rule for `src.ui` and `src.adapters`.
- Allowed public modules/symbols must be explicit; arbitrary future `src.application.foo.internal` is rejected automatically.
- Adapter port implementations may import deliberate contract modules such as `src.application.config.contracts` and `src.application.training.contracts`.

- [ ] **Step 1: Add RED synthetic-module tests**

Use `_write_package_tree` style fixtures to prove all cases:

```python
"src.adapters.bad_new_internal": "from src.application.foo.internal import FooService\n",
"src.ui.bad_public_reexport": "from src.application.diagnostics import DiagnosticsApplicationService\n",
"src.adapters.good_training_port": "from src.application.training.contracts import ResumeCheckpointPort\n",
"src.ui.good_gateway": "from src.application.diagnostics import DiagnosticsGateway\n",
```

Expected offenders: first two only.

- [ ] **Step 2: Add a public export audit test**

For every Application package exposed to outer layers, assert `__all__` contains only the intentional gateway/DTO/error/port surface. Explicitly reject names ending in `ApplicationService`.

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_architecture.py tests/test_application_boundaries.py -k "guardian or public_surface or reexport"
```

Expected: RED because current checker uses historical deny lists and empty symbol rules.

- [ ] **Step 4: Implement positive allowlist logic**

Add data structures separate from existing inner dependency rules, for example:

```python
OUTER_APPLICATION_PUBLIC_MODULES = {
    "src.ui": {
        "src.application",
        "src.application.errors",
        "src.application.config",
        "src.application.inference",
        "src.application.training",
        "src.application.diagnostics",
        "src.application.explorer",
    },
    "src.adapters": {
        "src.application",
        "src.application.errors",
        "src.application.config",
        "src.application.config.contracts",
        "src.application.inference",
        "src.application.training",
        "src.application.training.contracts",
        "src.application.diagnostics",
        "src.application.explorer",
    },
}
```

Add explicit symbol allowlists for public package imports so `from src.application.diagnostics import DiagnosticsGateway` passes while `DiagnosticsApplicationService` fails even though the package itself is allowed.

**Module matching is exact, not prefix-based.** Allowing `src.application.diagnostics` must not implicitly allow `src.application.diagnostics.service` or `src.application.diagnostics.internal`. Deliberate contract submodules are listed as exact module names.

Do not encode every future forbidden implementation name. Unknown outer imports under `src.application` must fail by default.

- [ ] **Step 5: Keep contract imports intentional**

Do not globally allow every `*.contracts` module. Only list contract modules actually implemented by outer adapters. This prevents a new internal contract package from becoming public accidentally.

- [ ] **Step 6: Run focused GREEN tests and checker**

```bash
python -m pytest -q tests/test_architecture.py tests/test_application_boundaries.py
python scripts/check_architecture.py
```

Expected: all PASS.

- [ ] **Step 7: Commit Task 7**

```bash
git add scripts/check_architecture.py tests/test_architecture.py tests/test_application_boundaries.py
git commit -m "test: default deny outer application internals"
```

---

### Task 8: Move the real CLI under `src/adapters/cli` and make root `main.py` bootstrap-only

**Files:**

- Create: `src/adapters/cli/entrypoint.py`
- Modify: `src/adapters/cli/__init__.py`
- Replace: `main.py`
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_architecture.py`
- Modify tests currently importing `main.build_parser`, `main.cmd_train`, or other command functions

**Interfaces:**

- Produces: `src.adapters.cli.entrypoint.main() -> None`
- Produces: `src.adapters.cli.entrypoint.build_parser() -> argparse.ArgumentParser`
- Root `main.py` must contain only the public entrypoint import and `__main__` guard.

- [ ] **Step 1: Add RED thin-bootstrap test**

```python
def test_root_main_is_bootstrap_only():
    tree = ast.parse(Path("main.py").read_text(encoding="utf-8"))
    imported = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert functions == []
    assert len(imported) == 1
    assert "src.adapters.cli.entrypoint" in Path("main.py").read_text(encoding="utf-8")
```

Also assert root main has no `build_application_services`, `uvicorn`, `argparse`, `src.application`, or inner import tokens.

- [ ] **Step 2: Keep the Wave 1 launcher-purity regression test while moving its import target**

Move the existing `cmd_ui` test import from root `main` to `src.adapters.cli.entrypoint`. The behavior is already GREEN from Task 4; this step ensures relocation does not reopen pre-composition.

- [ ] **Step 3: Run RED tests for root-file relocation**

```bash
python -m pytest -q tests/test_application_boundaries.py -k "root_main or ui_launcher or cli_train"
```

Expected: RED because all CLI logic is still in root `main.py`.

- [ ] **Step 4: Move CLI process mechanics unchanged**

Move Windows stream encoding setup, parser construction, `_compose`, commands, interactive prompt loop, Uvicorn launch, exception→exit handling into `src/adapters/cli/entrypoint.py`.

For `cmd_ui`, do **not** call `_compose()` or `build_application_services()`. Uvicorn's factory process owns graph construction through `src.ui.app:create_app`.

If launcher logging must be configured, use a process-safe default/basic logger only; app-configured logging may be applied inside the serving worker after its explicit config read.

- [ ] **Step 5: Replace root file**

Final file:

```python
from src.adapters.cli.entrypoint import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Migrate tests to the guarded adapter module**

Tests of parser/commands import:

```python
from src.adapters.cli import entrypoint
```

Do not keep compatibility re-exports in root `main.py` solely to satisfy tests; that would reopen the guardian blind spot.

- [ ] **Step 7: Run Wave 2 focused GREEN tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_architecture.py tests/test_ui.py -k "cli or gateway or guardian or main or diagnostics or explorer"
python scripts/check_architecture.py
```

Expected: PASS.

- [ ] **Step 8: Wave 2 self-review**

Run:

```bash
rg -n "ApplicationService|\.service|\.background|\.launch|scripts\.check_all" src/ui src/adapters
rg -n "from src\.application|import src\.application" src/ui src/adapters
```

Review every hit against the explicit public allowlist. Any concrete service/import bypass added during the wave must be fixed before proceeding.

- [ ] **Step 9: Commit Task 8**

```bash
git add main.py src/adapters/cli tests/test_application_boundaries.py tests/test_architecture.py tests/test_ui.py
git commit -m "refactor: move cli behind guarded adapter entrypoint"
```

---

# Wave 3 — Canonical Ordering-Sensitive Transactions

### Task 9: Create one shared training transaction coordinator and centralize plan + resume pinning

**Files:**

- Create: `src/application/training/transaction.py`
- Modify: `src/application/training/gateway.py`
- Modify: `src/application/training/contracts.py`
- Modify: `src/composition/root.py`
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_training_service.py`
- Modify: `tests/test_ui.py` where tests reach the old launch object

**Interfaces:**

- Produces internal `TrainingTransactionApplicationService` with:

```python
def run_command(
    self,
    command: TrainingCommand,
    *,
    observer: Optional[TrainingObserver] = None,
    log_interval: int = 10,
) -> TrainingExecutionResult: ...

def start_command(self, command: TrainingCommand) -> TrainingStartResult: ...
```

- `TrainingGateway.run()` and `.start()` both delegate to this transaction object.
- `TrainingApplicationService` remains planner/preparer/executor and no longer serves as the direct public sync execution path.

- [ ] **Step 1: Add RED gateway delegation tests**

Use stubs:

```python
class TransactionStub:
    def run_command(self, command, **kwargs):
        calls.append(("run", command, kwargs))
        return TrainingExecutionResult(False, "COMPLETED")

    def start_command(self, command):
        calls.append(("start", command))
        return TrainingStartResult(feasibility=feasibility)
```

Assert both public gateway methods hit the same transaction stub and no longer call `planner.run()`.

- [ ] **Step 2: Add RED checkpoint pinning test for both modes**

A fake checkpoint port should record exactly one `resolve()` and one `capture_identity()` for a command with `resume_checkpoint`, whether `run_command` or `start_command` is used.

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_training_service.py -k "transaction or resume or gateway"
```

Expected: RED because sync and background use different coordinators.

- [ ] **Step 4: Extract shared `_plan_and_pin`**

Implement inside the new coordinator:

```python
def _plan_and_pin(self, command: TrainingCommand) -> TrainingPlan:
    plan = self._training_application.plan(command)
    if not command.resume_checkpoint:
        return plan
    path = self._checkpoint_port.resolve(
        command.resume_checkpoint,
        plan.requested_config.training.checkpoint_dir,
    )
    return replace(
        plan,
        resume_checkpoint=path,
        resume_checkpoint_identity=self._checkpoint_port.capture_identity(path),
    )
```

Do not resolve config again after `plan()`.

- [ ] **Step 5: Rewire `TrainingGateway`**

Narrow the planner dependency to feasibility only:

```python
class TrainingPlannerPort(Protocol):
    def check_feasibility(self, command: TrainingCommand) -> TrainingFeasibility: ...

class TrainingTransactionPort(Protocol):
    def run_command(...): ...
    def start_command(...): ...
```

Remove direct `planner.run()` use.

- [ ] **Step 6: Wire composition**

Construct one transaction coordinator with the same `TrainingApplicationService`, inference handoff service, config service, filesystem checkpoint adapter and shared accelerator coordinator.

Do not delete old `launch.py` until Task 11 has migrated background semantics and no production references remain.

- [ ] **Step 7: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_training_service.py -k "transaction or gateway or resume"
```

Expected: PASS for plan/pinning/delegation tests; ownership behavior lands in Tasks 10-11.

- [ ] **Step 8: Commit Task 9**

```bash
git add src/application/training/transaction.py src/application/training/gateway.py src/application/training/contracts.py src/composition/root.py tests/test_application_boundaries.py tests/test_training_service.py tests/test_ui.py
git commit -m "refactor: centralize training transaction planning"
```

---

### Task 10: Route synchronous CLI training through handoff + accelerator admission + config commit

**Files:**

- Modify: `src/application/training/transaction.py`
- Modify: `src/application/training/service.py`
- Modify: `src/application/runtime/contracts.py` only for resource-port methods required by the coordinator
- Modify: `tests/test_training_service.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

- Shared pre-commit ownership helper in transaction coordinator.
- Sync commit point: planning/pinning/handoff and accelerator ownership have all succeeded; canonical config is then activated before prepare/execute.
- Post-commit failure: release training ownership in `finally`, do not call handoff rollback.

- [ ] **Step 1: Add RED sync handoff/admission tests**

Cover four cases:

```python
# 1. same-accelerator inference handoff occurs before prepare
assert calls[:2] == [("handoff", "cuda"), ("prepare", ...)]

# 2. when handoff did not transfer ownership, accelerator.reserve_training("cuda") occurs
# 3. reserve failure invokes handoff.rollback() and prepare is never called
# 4. prepare/execute failure after ownership commit releases training but does not rollback inference
```

- [ ] **Step 2: Add a config-resolution-count test**

Use a counting provider and call `TrainingGateway.run(command)`:

```python
assert provider.load_count == 1
assert config_service.current().training.batch_size == planned_batch_size
```

Do not count a separate CLI logging read in this Application unit test; semantic transaction itself must read once.

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_training_service.py tests/test_application_boundaries.py -k "synchronous or handoff or admission or resolve_once"
```

Expected: RED because `TrainingApplicationService.run()` bypasses cross-use-case ownership.

- [ ] **Step 4: Implement pre-commit ownership acquisition**

Private transaction logic must distinguish whether training ownership came from inference transfer:

```python
handoff = self._inference_service.prepare_for_training(plan.runtime_plan.device)
reserved_by_handoff = handoff.training_admission_reserved
if not reserved_by_handoff:
    try:
        self._accelerator.reserve_training(plan.runtime_plan.device)
    except Exception:
        handoff.rollback()
        raise
```

If later **pre-commit** work fails:

- direct reservation: `release_training(device)` then `handoff.rollback()`;
- transferred reservation: `handoff.rollback()` only, because rollback transfers ownership back to inference.

- [ ] **Step 5: Implement synchronous commit with an explicit activation-failure rollback boundary**

Configuration activation is the final pre-commit action. If it unexpectedly fails after ownership acquisition, ownership is still reversible and must be rolled back. Only after activation succeeds is inference restoration forbidden:

```python
plan = self._plan_and_pin(command)
handoff, reserved_by_handoff = self._acquire_training_ownership(plan)
try:
    self._config_service.activate(plan.requested_config)
except Exception:
    self._rollback_precommit_ownership(
        plan,
        handoff=handoff,
        reserved_by_handoff=reserved_by_handoff,
    )
    raise

# Commit boundary: canonical config is active and training owns the resource.
try:
    prepared = self._training_application.prepare(
        plan,
        observer=observer,
        log_interval=log_interval,
    )
    return self._training_application.execute(prepared, plan)
finally:
    self._accelerator.release_training(plan.runtime_plan.device)
```

Add a dedicated test where `activate()` raises: direct reservations are released, transferred ownership is rolled back through the handoff token, prepare never runs, and no double-release occurs. Do not call `handoff.rollback()` for failures after the commit boundary.

Remove or make private the old `TrainingApplicationService.run()` path so no production code can bypass the transaction coordinator. Tests may exercise `plan/prepare/execute` separately.

- [ ] **Step 6: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_training_service.py tests/test_application_boundaries.py -k "synchronous or handoff or admission or resolve_once or cli_train"
```

Expected: PASS.

- [ ] **Step 7: Commit Task 10**

```bash
git add src/application/training/transaction.py src/application/training/service.py src/application/runtime/contracts.py tests/test_training_service.py tests/test_application_boundaries.py
git commit -m "fix: admit synchronous training through shared transaction"
```

---

### Task 11: Route background start through the same ownership transaction without changing lifecycle semantics

**Files:**

- Modify: `src/application/training/transaction.py`
- Modify: `src/application/training/background.py`
- Delete after migration: `src/application/training/launch.py`
- Modify: `src/composition/root.py`
- Modify: `tests/test_training_service.py`
- Modify: `tests/test_ui.py`
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_config.py`

**Interfaces:**

- Background service consumes an already-owned training admission. It must not independently choose whether to handoff inference.
- Successful `start_training(...)` means the background worker owns cleanup responsibility.
- Failure before successful start returns ownership to the transaction coordinator for rollback.

- [ ] **Step 1: Add RED background ownership tests**

Cover:

1. coordinator handoff before background start;
2. direct reserve when handoff does not already own training;
3. `start_training` failure releases direct reservation + rolls back runtime handoff;
4. transferred inference ownership rolls back through handoff only;
5. after successful worker start, worker `finally` releases training ownership exactly once;
6. config activation happens only after successful start acceptance;
7. stop/clear/status behavior remains unchanged.

- [ ] **Step 2: Add a no-bypass production scan**

```python
def test_background_training_start_is_only_called_by_training_transaction():
    callers = []
    for path in Path("src").rglob("*.py"):
        if path.name == "background.py":
            continue
        if ".start_training(" in path.read_text(encoding="utf-8"):
            callers.append(str(path))
    assert callers == ["src/application/training/transaction.py"]
```

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_training_service.py tests/test_ui.py tests/test_application_boundaries.py -k "background or start_training or handoff or config_commit"
```

Expected: RED until coordinator owns both execution modes.

- [ ] **Step 4: Make transaction coordinator reserve before background start**

Call background with `admission_reserved=True` for every accepted transaction. The background service must no longer decide whether to reserve because the coordinator already established ownership.

Preserve the existing thread-start rollback boundary: if `thread.start()` raises, `start_training()` raises back to the transaction coordinator before the transaction returns success.

- [ ] **Step 5: Preserve worker cleanup semantics**

The background worker `finally` still:

- clears trainer reference;
- normalizes STARTING/STOPPING to STOPPED when required;
- releases training ownership once;
- cleans accelerator cache;
- keeps current post-training inference non-restoration behavior.

Do not add automatic inference reload/restore.

- [ ] **Step 6: Activate config at the existing safe commit point**

After `start_training()` returns successfully:

```python
self._config_service.activate(plan.requested_config)
return TrainingStartResult(feasibility=plan.feasibility)
```

A validated `requested_config` snapshot must already exist, so activation must not re-read the provider or perform external I/O. Add `test_activate_resolved_snapshot_is_in_memory_and_does_not_read_provider` in `tests/test_config.py`. This preserves the existing background commit order without adding a paused-thread protocol solely for theoretical activation I/O. If activation of a valid snapshot can currently fail for purely local validation, move that validation into `resolve()`/`plan()` so `activate()` becomes non-failing for an already-resolved snapshot.

- [ ] **Step 7: Remove the superseded launch service**

Delete `src/application/training/launch.py`, remove imports/references, and update architecture/public-surface tests so no stale launch implementation remains.

- [ ] **Step 8: Run Wave 3 focused GREEN tests**

```bash
python -m pytest -q tests/test_training_service.py tests/test_ui.py tests/test_application_boundaries.py tests/test_config.py -k "training or resume or handoff or admission or config or activate_resolved_snapshot"
```

Expected: PASS.

- [ ] **Step 9: Wave 3 self-review**

Run:

```bash
rg -n "start_training\(|prepare_for_training\(|reserve_training\(|\.activate\(" src/application src/adapters src/ui
rg -n "TrainingApplicationService\.run|planner\.run|training_application\.run" src tests
```

Confirm:

- both `TrainingGateway.run/start` use the transaction coordinator;
- only the transaction coordinator invokes inference handoff;
- no adapter owns accelerator/pinning/config-commit policy;
- no second config resolve occurs after `TrainingPlan` creation;
- post-commit failure never rolls inference back automatically.

- [ ] **Step 10: Commit Task 11**

```bash
git add src/application/training src/composition/root.py tests/test_training_service.py tests/test_ui.py tests/test_application_boundaries.py tests/test_config.py
git commit -m "refactor: unify background training transaction policy"
```

---

# Wave 4 — Typed Semantic Contracts and Presentation Cleanup

### Task 12: Introduce pure data-preparation policy + typed opaque prepared-data handle

**Files:**

- Create: `src/application/data/__init__.py`
- Create: `src/application/data/contracts.py`
- Create: `src/application/data/policy.py`
- Remove after migration: `src/application/data_policy.py`
- Create: `src/composition/training_data.py`
- Modify: `src/composition/training_runtime.py`
- Modify: `src/composition/root.py`
- Modify: `src/application/training/contracts.py`
- Modify: `src/application/training/service.py`
- Modify: `src/data/api.py`
- Modify: `tests/application_support.py`
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_training_service.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class DataPreparationSpec:
    config: DataConfig
    block_size: Optional[int]
    allow_builtin_fallback_corpus: bool
    persist_fallback: bool
    fallback_cleaner_type: Optional[str]

class PreparedDataHandle:
    """Opaque nominal Application-owned token; Application code never inspects subclasses."""

class DataPreparationPort(Protocol):
    def prepare(self, spec: DataPreparationSpec) -> PreparedDataHandle: ...

class TrainingRuntimePort(Protocol):
    def prepare(
        self,
        *,
        config: EngineConfig,
        runtime_plan: ResolvedTrainingPlan,
        data: PreparedDataHandle,
        observer: Optional[TrainingObserver] = None,
        abort_check: Optional[Callable[[], bool]] = None,
        log_interval: int = 10,
    ) -> RuntimePreparedRun: ...
```

- [ ] **Step 1: Add RED contract scan tests**

AST/text assertions must reject stability-critical signatures containing:

- `train_data: Any`
- `val_data: Any`
- `tokenizer: Any`
- Application `create_cleaner`, `create_tokenizer`, concrete fallback wrapper construction;
- Application imports of `FALLBACK_CORPUS` from `src.data`.

Also assert `TrainingApplicationService` accepts an injected `DataPreparationPort`. The Application spec carries only `allow_builtin_fallback_corpus=True/False`; the concrete corpus text remains owned by the data capability.

- [ ] **Step 2: Add RED policy test**

Pure policy test:

```python
def test_data_policy_explicitly_allows_standard_fallback_only_for_gemini():
    gemini = build_data_preparation_spec(gemini_config, block_size=64, ...)
    standard = build_data_preparation_spec(standard_config, block_size=64, ...)
    assert gemini.fallback_cleaner_type == "standard"
    assert standard.fallback_cleaner_type is None
```

No cleaner/tokenizer object may be constructed in this test.

- [ ] **Step 3: Add RED opaque-handle integration test**

A fake `DataPreparationPort` returns a custom `PreparedDataHandle` subclass; the Application service passes the same object to `TrainingRuntimePort.prepare` without attribute inspection.

- [ ] **Step 4: Run RED tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_training_service.py -k "data_policy or opaque or prepared_data or Any"
```

Expected: RED because Application currently constructs cleaner/tokenizer/dataset objects and passes three `Any` values.

- [ ] **Step 5: Move fallback mechanics into the data capability**

Add this stable facade operation:

```python
def prepare_dataset_with_policy(
    config: DataConfig,
    *,
    block_size: Optional[int],
    allow_builtin_fallback_corpus: bool,
    persist_fallback: bool,
    fallback_cleaner_type: Optional[str],
):
    ...
```

Inside `src.data`, construct the primary cleaner/tokenizer and catch the concrete recoverable `DataPipelineError` when the explicit fallback type is present. Application decides **whether** fallback is allowed; data capability decides **how** to instantiate and execute it.

- [ ] **Step 6: Implement private composition handle**

In `src/composition/training_data.py`:

```python
@dataclass(frozen=True)
class _PreparedDataHandle(PreparedDataHandle):
    train_data: object
    val_data: object
    tokenizer: object

class TrainingDataPreparationAdapter:
    def prepare(self, spec: DataPreparationSpec) -> PreparedDataHandle:
        train, val, tokenizer = prepare_dataset_with_policy(...)
        return _PreparedDataHandle(train, val, tokenizer)
```

Capability objects may exist in this private bridge. They must not cross into Application-visible fields/methods.

- [ ] **Step 7: Change `TrainingRuntimeAdapter.prepare` to accept one handle**

Validate the nominal private handle:

```python
if not isinstance(data, _PreparedDataHandle):
    raise TypeError("Prepared data handle does not belong to the training-data bridge")
```

Then unwrap only inside composition and delegate to `TrainingRunFactory.prepare(...)`.

- [ ] **Step 8: Change `TrainingApplicationService.prepare`**

Target flow:

```python
spec = build_data_preparation_spec(
    effective.data,
    block_size=effective.model.block_size,
    allow_builtin_fallback_corpus=True,
    persist_fallback=True,
)
data = self._data_preparation.prepare(spec)
runtime_run = self._runtime.prepare(
    config=effective,
    runtime_plan=plan.runtime_plan,
    data=data,
    observer=observer,
    abort_check=abort_check,
    log_interval=log_interval,
)
```

Application must not inspect `data`.

- [ ] **Step 9: Run focused GREEN tests**

```bash
python -m pytest -q \
  tests/test_training_service.py \
  tests/test_application_boundaries.py \
  tests/test_dataset.py \
  tests/test_preprocessors.py \
  tests/test_tokenizer.py
```

Expected: PASS. These are the repository's concrete data-pipeline test files; these paths are intentionally fixed to the repository files audited for this plan.

- [ ] **Step 10: Commit Task 12**

```bash
git add src/application/data src/application/training src/composition src/data/api.py tests/application_support.py tests/test_application_boundaries.py tests/test_training_service.py
git rm src/application/data_policy.py
git commit -m "refactor: hide prepared data behind typed handle"
```

---

### Task 13: Remove concrete cleaner/dataset objects from Explorer Application flows

**Files:**

- Modify: `src/data/api.py`
- Modify: `src/application/explorer/service.py`
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_ui.py`

**Interfaces:**

- Explorer Application passes pure values/config to `src.data.api` only.
- `export_binary` delegates one capability facade operation that owns prepare + binary export mechanics.

- [ ] **Step 1: Add RED static boundary test**

```python
def test_explorer_application_does_not_construct_or_unpack_capability_objects():
    source = Path("src/application/explorer/service.py").read_text(encoding="utf-8")
    assert "build_application_cleaner" not in source
    assert "prepare_application_dataset" not in source
    assert "train_data, val_data" not in source
```

- [ ] **Step 2: Add RED behavior tests for clean/export compatibility**

Keep the existing `/api/explorer/clean` and `/api/explorer/export-binary` response keys and statuses unchanged while the internal call changes.

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_ui.py -k "explorer and (clean or export or data)"
```

Expected: RED on static boundary assertion.

- [ ] **Step 4: Add pure-value data facade operations**

Refactor `clean_for_explorer` so it accepts cleaner type/options/fallback intent rather than a concrete callable. Add this operation:

```python
def prepare_and_export_binary_dataset(
    config: DataConfig,
    *,
    fallback_cleaner_type: Optional[str],
    allow_builtin_fallback_corpus: bool,
    persist_fallback: bool,
) -> dict[str, object]: ...
```

Data capability owns concrete prepare + save mechanics.

- [ ] **Step 5: Simplify Explorer service**

Use the same pure fallback-policy selector from `src.application.data.policy`; do not import a concrete cleaner/tokenizer/dataset type.

- [ ] **Step 6: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_ui.py -k "explorer"
```

Expected: PASS.

- [ ] **Step 7: Commit Task 13**

```bash
git add src/data/api.py src/application/explorer/service.py tests/test_application_boundaries.py tests/test_ui.py
git commit -m "refactor: keep explorer capability objects inward"
```

---

### Task 14: Introduce typed raw training state and event facts

> **Migration-cluster rule (Tasks 14–16):** this boundary cannot be made fully transport-clean in one tiny edit without either a temporary compatibility DTO in Application or a broken HTTP stream. Tasks 14–16 are therefore an ordered migration cluster. Task 14 makes lifecycle facts raw/typed at their source, Task 15 moves outward presentation, and Task 16 removes the final generator/heartbeat transport leak. Do not introduce a temporary Application presentation shim between them; run the focused gate stated by each task and the full UI compatibility gate at Task 16.

**Files:**

- Modify: `src/application/training/contracts.py`
- Modify: `src/application/training/background.py`
- Modify: `src/application/training/gateway.py`
- Modify: `tests/test_training_service.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

Use explicit Application-owned types:

```python
TrainingStatus = Literal[
    "IDLE", "STARTING", "RUNNING", "STOPPING", "STOPPED", "COMPLETED", "ERROR"
]
TrainingTerminationReason = Optional[
    Literal["COMPLETED", "EARLY_STOPPED", "USER_STOPPED", "ABORTED_STARTUP", "FAILED"]
]
TrainingStatusCode = Literal[
    "PREPARING",
    "RUNNING",
    "FINISHED",
    "CLEARED",
    "STOPPING_STARTUP",
    "STOPPING_RUN",
    "ABORTED_STARTUP",
    "CLEANUP_STOPPED",
    "START_FAILED",
    "ERROR",
]

@dataclass(frozen=True)
class TrainingStepFact:
    run_id: int
    sequence: int
    step: int
    loss: float
    lr: float
    elapsed: float

@dataclass(frozen=True)
class TrainingEvalFact:
    run_id: int
    sequence: int
    step: int
    train_loss: float
    val_loss: float
    lr: float

@dataclass(frozen=True)
class TrainingSampleFact:
    run_id: int
    sequence: int
    step: int
    text: str
    recorded_at: float

@dataclass(frozen=True)
class TrainingState:
    run_id: int
    sequence: int
    status: TrainingStatus
    termination_reason: TrainingTerminationReason
    current_step: int
    max_iters: int
    current_loss: Optional[float]
    current_val_loss: Optional[float]
    current_lr: Optional[float]
    last_sample_text: str
    error_detail: Optional[str]
    history_steps: tuple[TrainingStepFact, ...]
    history_evals: tuple[TrainingEvalFact, ...]
    sample_history: tuple[TrainingSampleFact, ...]

@dataclass(frozen=True)
class TrainingStatusFact:
    code: TrainingStatusCode
    state: TrainingState
    detail: Optional[str] = None

TrainingEvent = TrainingStatusFact | TrainingStepFact | TrainingEvalFact | TrainingSampleFact
```

- [ ] **Step 1: Add RED type-surface tests**

Assert `TrainingGateway.get_state` returns `TrainingState`, `TrainingEventPort.publish` accepts `TrainingEvent`, and raw recorded metrics are floats with no display rounding requirement. Do **not** require the legacy `iter_events` generator/heartbeat surface to disappear in this task; Task 16 owns that final transport removal.

- [ ] **Step 2: Add RED raw-metric test**

```python
service.record_step(step=1, loss=0.123456, lr=0.000123456789, elapsed=1.23456, emit=True)
state = service.get_state()
assert state.current_loss == 0.123456
assert state.current_lr == 0.000123456789
assert state.history_steps[0].elapsed == 1.23456
```

Current implementation should fail due to rounding.

- [ ] **Step 3: Add RED raw timestamp/status-code test**

Assert sample history contains `recorded_at: float`, not a `%H:%M:%S` string, and status events contain a transport-neutral `code` instead of a localized `message`.

- [ ] **Step 4: Run RED tests**

```bash
python -m pytest -q tests/test_training_service.py tests/test_application_boundaries.py -k "raw or state or event or presentation"
```

Expected: RED.

- [ ] **Step 5: Replace lifecycle storage/publishing with typed facts**

Keep the same MAX history bounds and sequence/run-id logic. `TrainingService` may keep mutable lists internally, but list element types are the typed fact dataclasses and `get_state()` returns immutable tuples in `TrainingState`. `TrainingEventPort.publish` becomes typed immediately. The existing streaming iterator may still adapt its stored typed facts until Task 16 replaces that iterator; do not add a new public compatibility DTO or formatting helper inside Application.

- [ ] **Step 6: Remove presentation work from Application**

Delete:

- `round(...)` for step/eval/current display values;
- `time.strftime("%H:%M:%S")`;
- `_WebTrainingObserver` name;
- `REST/SSE/UI/Web` ownership comments;
- localized status message creation.

Rename the observer to `_LifecycleTrainingObserver`.

Use raw `time.time()` only for `TrainingSampleFact.recorded_at`; that is a lifecycle fact, not display formatting.

- [ ] **Step 7: Make status events code-based**

Replace `_status_event_locked(message)` with this signature:

```python
def _status_event_locked(
    self,
    code: TrainingStatusCode,
    *,
    detail: Optional[str] = None,
) -> TrainingStatusFact:
    self._next_sequence_locked()
    return TrainingStatusFact(code=code, state=self._snapshot_locked(), detail=detail)
```

Map each existing lifecycle transition to one explicit code.

- [ ] **Step 8: Run focused GREEN Application tests**

```bash
python -m pytest -q tests/test_training_service.py tests/test_application_boundaries.py
```

UI tests are expected to need Task 15 presenter mapping; do not paper over that by converting DTOs back to dicts inside Application.

- [ ] **Step 9: Commit Task 14**

```bash
git add src/application/training/contracts.py src/application/training/background.py src/application/training/gateway.py tests/test_training_service.py tests/test_application_boundaries.py
git commit -m "refactor: type raw training lifecycle state"
```

---

### Task 15: Add UI training presenter and preserve exact external status/event shapes

**Files:**

- Create: `src/ui/training_presenter.py`
- Modify: `src/ui/routes/training.py`
- Modify: `src/ui/responses.py` only for presenter use; heartbeat mechanics move in Task 16
- Modify: `tests/test_ui.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

- Produces:

```python
def present_training_state(state: TrainingState) -> dict[str, object]: ...
def present_training_event(event: TrainingEvent) -> dict[str, object]: ...
def present_training_init(state: TrainingState) -> dict[str, object]: ...
```

- Presenter owns numeric rounding, display timestamp, localized status message and external legacy key names.

- [ ] **Step 1: Capture compatibility keys in RED tests**

For `/api/training/status`, assert the current keys remain:

```python
{
    "run_id", "sequence", "status", "termination_reason",
    "current_step", "max_iters", "current_loss", "current_val_loss",
    "current_lr", "last_sample_text", "error_message",
    "history_steps", "history_evals", "sample_history",
}
```

For event presenter tests, assert:

- step: `type/run_id/sequence/step/loss/lr/elapsed`;
- eval: `type/run_id/sequence/step/train_loss/val_loss/lr`;
- sample: `type/run_id/sequence/step/text/timestamp`;
- status/init flatten state fields rather than nesting them.

- [ ] **Step 2: Add exact rounding/timestamp tests**

```python
payload = present_training_event(
    TrainingStepFact(..., loss=0.123456, lr=0.000123456789, elapsed=1.23456)
)
assert payload["loss"] == 0.1235
assert payload["lr"] == 0.0001235
assert payload["elapsed"] == 1.2
```

For sample, monkeypatch/localize time formatting and assert `%H:%M:%S` remains the external shape.

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_ui.py tests/test_application_boundaries.py -k "training and (status or presenter or stream)"
```

Expected: RED until typed DTOs are mapped outward.

- [ ] **Step 4: Implement state presenter**

Convert dataclasses to the existing response keys. Map `error_detail -> error_message`; convert immutable tuples to lists; apply display rounding only here.

- [ ] **Step 5: Implement event presenter and localized message table**

Keep all Vietnamese message strings in this adapter file, keyed by `TrainingStatusCode`. For `ERROR`, use `event.detail` as the displayed message. For `FINISHED`, include the final state status exactly as before.

- [ ] **Step 6: Update HTTP routes**

- status endpoint: `return present_training_state(services.training.get_state())`;
- start response `state`: present the typed current state;
- any clear/stop response remains unchanged unless it embeds state.

Do not add presenter calls back into Application.

- [ ] **Step 7: Run focused GREEN UI tests**

```bash
python -m pytest -q tests/test_ui.py tests/test_application_boundaries.py -k "training"
```

Expected: PASS except heartbeat/disconnect tests intentionally introduced in Task 16.

- [ ] **Step 8: Commit Task 15**

```bash
git add src/ui/training_presenter.py src/ui/routes/training.py src/ui/responses.py tests/test_ui.py tests/test_application_boundaries.py
git commit -m "refactor: move training presentation to ui adapter"
```

---

### Task 16: Replace Application heartbeat generators with closeable transport-neutral subscriptions

**Files:**

- Modify: `src/application/training/contracts.py`
- Modify: `src/application/training/background.py`
- Modify: `src/application/training/gateway.py`
- Modify: `src/training/events.py`
- Modify: `src/ui/responses.py`
- Modify: `src/ui/routes/training.py`
- Create: `tests/test_ui_streaming.py`
- Modify: `tests/test_training_event_hub.py`
- Modify: `tests/test_training_service.py`

**Interfaces:**

```python
class TrainingEventSubscription(Protocol):
    @property
    def initial_state(self) -> TrainingState: ...

    def next_event(self, timeout: Optional[float] = None) -> Optional[TrainingEvent]: ...
    def close(self) -> None: ...

class TrainingEventPort(Protocol):
    def publish(self, event: TrainingEvent) -> None: ...
    def open_subscription(
        self,
        snapshot: Callable[[], TrainingState],
    ) -> TrainingEventSubscription: ...
```

`TrainingGateway.subscribe_events() -> TrainingEventSubscription` replaces `iter_events()`.

- [ ] **Step 1: Add RED event-hub tests proving no heartbeat is emitted**

```python
subscription = hub.open_subscription(lambda: state)
assert subscription.initial_state == state
assert subscription.next_event(timeout=0.001) is None
subscription.close()
assert len(hub._subscribers) == 0  # unit test may inspect private storage; do not add test-only production API
```

- [ ] **Step 2: Add RED response-adapter heartbeat test**

A fake subscription returning `None` on timeout must yield an SSE comment from `TrainingStreamingResponse`, e.g. `": heartbeat\n\n"`, without an Application heartbeat event.

- [ ] **Step 3: Add RED disconnect cleanup test**

Use a fake close-counting subscription and invoke `TrainingStreamingResponse.__call__` with a minimal ASGI receive/send sequence that disconnects. Assert `close()` is called exactly once in `finally`.

- [ ] **Step 4: Add the final RED transport-boundary scan and run RED tests**

Add assertions that after this task no Application contract contains `Generator[dict`, heartbeat fields, or `iter_events(...)`; the public method is `subscribe_events() -> TrainingEventSubscription`.

```bash
python -m pytest -q tests/test_training_event_hub.py tests/test_training_service.py tests/test_ui_streaming.py tests/test_application_boundaries.py -k "training or stream or heartbeat or subscription"
```

Expected: RED because current hub emits heartbeat dicts and response does not own a closeable subscription.

- [ ] **Step 5: Refactor `TrainingEventHub` to subscriber mechanics only**

Remove `time` import and heartbeat event construction. Implement a closeable subscription wrapper around the private queue. `next_event(timeout)` returns `None` on `queue.Empty`.

`src/training/events.py` is an inner capability module and **must not import `src.application.training` DTOs**. Keep the hub structurally generic (`object`/TypeVar or an internal generic protocol); the Application-facing `TrainingEventPort` is satisfied structurally by composition. Do not reverse the dependency merely to gain type names.

Open subscription **before** capturing the initial snapshot so events that race after subscribe are queued and version reconciliation remains correct.

- [ ] **Step 6: Change Application service/gateway boundary**

`TrainingService.subscribe_events()` delegates `self._events.open_subscription(self.get_state)`. Gateway returns the subscription. No `Generator[dict[str, Any], ...]` remains in Application contracts.

- [ ] **Step 7: Make `TrainingStreamingResponse` own keepalive**

Implement an internal iterator:

```python
def _iter_training_sse(subscription, heartbeat_seconds: float):
    yield encode_sse(present_training_init(subscription.initial_state))
    while True:
        event = subscription.next_event(timeout=heartbeat_seconds)
        if event is None:
            yield ": heartbeat\n\n"
        else:
            yield encode_sse(present_training_event(event))
```

`TrainingStreamingResponse.__call__` must close the subscription in `finally`, matching the existing generation response cleanup pattern.

- [ ] **Step 8: Update route**

```python
return TrainingStreamingResponse(
    subscription=request.app.state.services.training.subscribe_events(),
    heartbeat_seconds=1.0,
    ...,
)
```

- [ ] **Step 9: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_training_event_hub.py tests/test_training_service.py tests/test_ui_streaming.py tests/test_ui.py -k "training or stream"
```

Expected: PASS.

- [ ] **Step 10: Commit Task 16**

```bash
git add src/application/training src/training/events.py src/ui/responses.py src/ui/routes/training.py tests/test_training_event_hub.py tests/test_training_service.py tests/test_ui_streaming.py tests/test_ui.py
git commit -m "refactor: move training heartbeat to sse adapter"
```

---

### Task 17: Separate canonical inference config from transient runtime placement and remove duplicate accelerator-family logic

**Files:**

- Modify: `src/application/inference/preferences.py`
- Modify: `src/application/inference/service.py`
- Modify: `src/application/inference/contracts.py`
- Modify: `src/application/runtime/contracts.py`
- Modify: `src/core/accelerator.py`
- Modify: `src/composition/root.py`
- Modify: `tests/application_support.py`
- Modify: `tests/test_inference_service.py`
- Modify: `tests/test_generation_hardening.py`
- Modify: `tests/test_accelerator_coordinator.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

- Canonical device = `ConfigurationService`/EngineConfig only.
- Transient placement = `InferencePreparationCommand.requested_device` or private `load_checkpoint(..., requested_device=...)` operation argument.
- `AcceleratorPort` owns `same_family(first: str, second: str) -> bool` as the single Application-consumed classification authority.
- `InferenceService` receives a real `AcceleratorPort` rather than relying on an Application duplicate helper.

- [ ] **Step 1: Add RED canonical-authority test**

```python
assert not hasattr(service._preferences, "_device_override")
assert service.configured_device == config_service.current().system.device
```

Attempting a transient load/preparation to `cuda:0` must not change canonical `configured_device`.

- [ ] **Step 2: Add RED single-authority static test**

Search production code and require only one implementation of `def same_accelerator_family` (or rename the method to `same_family` on the coordinator so no duplicated free helper remains). Application runtime contracts must not contain classification algorithm code.

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_inference_service.py tests/test_generation_hardening.py tests/test_accelerator_coordinator.py tests/test_application_boundaries.py -k "device or accelerator or family or authority"
```

Expected: RED due to `_device_override` and duplicate helper.

- [ ] **Step 4: Remove `_device_override` and setter semantics**

`InferencePreferences.configured_device` becomes read-only canonical config state:

```python
@property
def configured_device(self) -> str:
    return self.snapshot().system.device
```

Remove the setter and override reset logic.

- [ ] **Step 5: Thread operation placement explicitly**

`InferenceService.load_checkpoint` accepts `requested_device: Optional[str] = None` and computes:

```python
target_requested_device = requested_device or self.configured_device
target_device = self._runtime.resolve_device_name(target_requested_device)
```

Pass the same requested device to the runtime load call. Do not mutate canonical config unless the preparation command explicitly activated a changed config snapshot.

- [ ] **Step 6: Make accelerator classification port-owned**

Add:

```python
class AcceleratorPort(Protocol):
    def same_family(self, first: str, second: str) -> bool: ...
    ...
```

Implement in `AcceleratorCoordinator` using its single existing classification helper. Delete the duplicate function from `src/application/runtime/contracts.py`, update exports, and have Application call `self._accelerator.same_family(...)`.

Production composition always supplies the coordinator. Test helpers should also supply a coordinator/fake rather than using `None` as a hidden alternate behavior.

- [ ] **Step 7: Update tests that assigned `service.configured_device`**

Change them to operation-level requested device input. Do not keep a compatibility setter solely for tests.

- [ ] **Step 8: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_inference_service.py tests/test_generation_hardening.py tests/test_accelerator_coordinator.py tests/test_application_boundaries.py
```

Expected: PASS.

- [ ] **Step 9: Commit Task 17**

```bash
git add src/application/inference src/application/runtime/contracts.py src/core/accelerator.py src/composition/root.py tests/application_support.py tests/test_inference_service.py tests/test_generation_hardening.py tests/test_accelerator_coordinator.py tests/test_application_boundaries.py
git commit -m "refactor: separate inference placement from config"
```

---

### Task 18: Narrow inference runtime port after bootstrap removal

**Files:**

- Modify: `src/application/inference/contracts.py`
- Modify: `src/application/inference/service.py`
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_inference_service.py`

**Interfaces:**

- Remove Application-port methods that no Application use case needs after explicit preparation.
- Minimum expected removals from `InferenceRuntimePort`: `path_exists`, `load_tokenizer_if_present`, `join_path` if no remaining Application call uses them.
- Task 4 has already removed adapter-facing `InferenceGateway.set_vocab_path` and `configured_checkpoint_path`; this task must verify they have not reappeared. Keep the explicit manual checkpoint load/list/delete/resolve use cases required by HTTP compatibility.
- Keep checkpoint listing/resolution/load/execution methods together unless current code demonstrates an independently changing checkpoint-catalog boundary worth splitting.

- [ ] **Step 1: Add RED protocol-surface test**

```python
members = InferenceRuntimePort.__dict__
assert "path_exists" not in members
assert "load_tokenizer_if_present" not in members
assert "join_path" not in members
```

Only include `join_path` in the assertion after confirming Task 2/4 now derives configured checkpoint through `resolve_checkpoint_path_for_dir(..., filename_only=True)`.

- [ ] **Step 2: Run RED test**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_inference_service.py -k "runtime_port or bootstrap"
```

Expected: RED on obsolete protocol methods.

- [ ] **Step 3: Remove obsolete methods from the Application protocol and call sites**

Do not delete harmless capability implementation helpers unless they are truly dead inside `src.inference`; the freeze requirement is to narrow the Application contract, not churn inner implementation unnecessarily.

- [ ] **Step 4: Decide whether to split checkpoint catalog port using evidence**

Run:

```bash
rg -n "list_checkpoints|delete_checkpoint|resolve_checkpoint_path_for_dir|load_checkpoint|begin_generation" src/application/inference src/ui src/adapters
```

If catalog and execution are still always consumed by the same `InferenceService`, keep one runtime port. Do **not** create a new interface just for aesthetic symmetry.

- [ ] **Step 5: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_inference_service.py tests/test_application_boundaries.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 18**

```bash
git add src/application/inference tests/test_application_boundaries.py tests/test_inference_service.py
git commit -m "refactor: narrow inference application runtime port"
```

---

### Task 19: Fix Diagnostics Optionality and shrink accidental Application exports

**Files:**

- Modify: `src/application/diagnostics/service.py:26-44`
- Modify: `src/application/training/__init__.py`
- Modify: `tests/test_diagnostics.py`
- Modify: `tests/test_ui.py`
- Modify: `tests/test_application_boundaries.py`

**Interfaces:**

- `VramEstimateInput.device: Optional[str] = None`; `None` means inherit canonical active config.
- `src.application.training.__all__` no longer contains `generate_run_name`.

- [ ] **Step 1: Add RED Optionality test**

```python
def test_vram_estimate_none_device_inherits_active_config(...):
    result = diagnostics.estimate(VramEstimateInput(device=None))
    assert captured_runtime_plan.requested_device == active_config.system.device
```

Add a type-contract assertion that the dataclass default is `None`.

- [ ] **Step 2: Add RED export-minimality test**

```python
from src.application import training
assert "generate_run_name" not in training.__all__
```

Keep the collision-resistance unit test by importing the helper from its internal implementation module, not the public package.

- [ ] **Step 3: Run RED tests**

```bash
python -m pytest -q tests/test_diagnostics.py tests/test_ui.py tests/test_application_boundaries.py -k "device or generate_run_name or export"
```

Expected: RED.

- [ ] **Step 4: Apply minimal production fixes**

Change:

```python
device: Optional[str] = None
```

Remove `generate_run_name` import/export from `src/application/training/__init__.py`; leave the helper internal to `service.py` because training planning still uses it.

- [ ] **Step 5: Run focused GREEN tests**

```bash
python -m pytest -q tests/test_diagnostics.py tests/test_ui.py tests/test_application_boundaries.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 19**

```bash
git add src/application/diagnostics/service.py src/application/training/__init__.py tests/test_diagnostics.py tests/test_ui.py tests/test_application_boundaries.py
git commit -m "refactor: tighten application public contracts"
```

---

# Final Freeze Ratchet

### Task 20: Adversarial boundary review and freeze-certificate tests

**Files:**

- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_architecture.py`

If this adversarial certificate finds a production defect, **do not patch it opportunistically inside Task 20**. Return to the task that owns that invariant, add a focused RED test there, fix it, rerun that task gate, then restart Task 20. This keeps the certificate task review-only.

**Interfaces:**

- Produces a final test matrix that represents every freeze exit criterion, not historical implementation details.

- [ ] **Step 1: Add/confirm constructor/process invariants**

Tests must prove:

- `build_application_services()` does not read/activate config;
- `InferenceService` construction performs zero checkpoint/tokenizer/resource work;
- root `main.py` is bootstrap-only;
- Uvicorn launcher does not create a graph;
- one Web app lifespan prepares default inference once.

- [ ] **Step 2: Add/confirm public-boundary invariants**

Tests must prove:

- `ApplicationServices` has five gateways only;
- Diagnostics/Explorer/Training/Inference concrete services are not outer-public;
- new arbitrary Application implementation modules are denied to `src.ui/src.adapters` by default;
- outer public symbol imports are allowlisted;
- no second app-state service locator exists besides `app.state.services`.

- [ ] **Step 3: Add/confirm transaction invariants**

Tests must prove:

- CLI sync and Web background training share planning/pinning/handoff/admission/config-commit policy;
- command config snapshot cannot drift after planning;
- pre-commit failures rollback correctly;
- committed failures release training resource once and do not restore inference automatically;
- CLI generation owns no setup sequence outside `InferenceGateway.prepare`.

- [ ] **Step 4: Add/confirm semantic contract invariants**

Tests must prove:

- no stability-critical Application port uses `Any` to carry train/val/tokenizer/capability objects;
- Application data policy constructs no cleaners/tokenizers;
- Explorer constructs/unpacks no concrete dataset object;
- training state/events are typed raw facts;
- Application contains no presentation rounding/display timestamp/SSE heartbeat/localized Web status messages;
- canonical inference config and transient placement remain distinguishable;
- accelerator-family classification has one authority.

- [ ] **Step 5: Run the architecture-focused freeze suite**

```bash
python -m pytest -q tests/test_application_boundaries.py tests/test_architecture.py
python scripts/check_architecture.py
```

Expected: PASS with zero architecture violations.

- [ ] **Step 6: Run source scans for known semantic leaks**

```bash
rg -n "DiagnosticsApplicationService|ExplorerApplicationService|TrainingApplicationService|InferenceService" src/ui src/adapters
rg -n "train_data: Any|val_data: Any|tokenizer: Any|heartbeat_seconds|time\.strftime|_WebTrainingObserver" src/application
rg -n "set_vocab_path|configured_checkpoint_path" src/adapters src/ui
rg -n "from scripts\.check_all|import scripts\.check_all" src/adapters src/ui
rg -n "build_application_services\(" main.py src/adapters/cli src/ui
```

Every hit must be explained by the target architecture. Any unexplained hit is a blocker, not a comment-only exception.

- [ ] **Step 7: Commit Task 20**

```bash
git add tests/test_application_boundaries.py tests/test_architecture.py
git commit -m "test: lock adapter application freeze invariants"
```

---

### Task 21: Full verification, frontend compatibility, documentation status and clean patch

**Files:**

- Modify: `docs/superpowers/specs/2026-09-10-adapter-application-freeze-hardening-design-R3.md` only to change status/evidence after all gates pass
- Modify: this plan only to check completed tasks if the executor tracks status in-repo
- No production change is allowed in this task except a fix for a failing freeze requirement discovered by verification; such a fix must get its own focused RED/GREEN test before rerunning final verification.

**Interfaces:**

- Consumes: all four wave exit gates, the Task 20 freeze-certificate suite, and the exact baseline recorded in Execution Setup.
- Produces: verified R3 status/evidence, a clean commit-range patch `adapter-application-freeze-hardening-R3.patch`, and a clean working tree suitable for outer-boundary freeze declaration.
- Failure rule: any production defect discovered here returns to its owning task for focused RED/GREEN correction before Task 21 is rerun from Step 1.

- [ ] **Step 1: Run complete Python suite**

```bash
python -m pytest -q
```

Expected: all tests pass; baseline before this plan was 505 passing tests, but the final count will be larger because this plan adds regression tests.

- [ ] **Step 2: Run architecture guardian**

```bash
python scripts/check_architecture.py
```

Expected: PASS, zero violations.

- [ ] **Step 3: Run format/lint/type gates individually**

```bash
python -m ruff format . --check
python -m ruff check .
python -m pyright
```

Expected: PASS when dev dependencies are installed. If a tool is missing, record the exact missing dependency; do not report the freeze as fully verified until the intended project environment runs it.

- [ ] **Step 4: Run project quality gate**

```bash
python main.py gate
```

Expected: exit code 0 and all six gates pass. This also verifies the new thin root bootstrap still dispatches CLI correctly.

- [ ] **Step 5: Run CLI smoke surface**

Use non-destructive commands:

```bash
python main.py --help
python main.py check
python main.py estimate
python main.py inspect
```

Expected: command names/options remain available and diagnostics render normally through gateways.

Do not start a real training run or require a real model checkpoint solely for this verification.

- [ ] **Step 6: Run frontend verification after training state/event migration**

```bash
cd frontend
npm run test
npm run lint
npm run build
```

Expected: all three commands PASS with unchanged `TrainingStateResponse`/`TrainingStreamEvent` external shape. `build` already runs TypeScript project compilation via `tsc -b`.

- [ ] **Step 7: Re-run HTTP compatibility tests explicitly**

```bash
cd ..
python -m pytest -q tests/test_ui.py tests/test_ui_errors.py tests/test_ui_streaming.py
```

Expected: PASS.

- [ ] **Step 8: Self-review git diff for scope and accidental artifacts**

```bash
git status --short
git diff --stat
git diff --check
git diff -- main.py src/application src/adapters src/composition src/ui scripts/check_architecture.py tests frontend
```

Reject:

- generated checkpoints/runs/logs;
- frontend build artifacts if they are not already versioned by project policy;
- caches/venvs;
- unrelated model/trainer/data algorithm rewrites;
- temporary compatibility exports;
- commented-out old code;
- unfinished placeholder/bypass markers.

- [ ] **Step 9: Mark the R3 spec status only after all required gates are actually green**

Update the spec status from Draft to an implemented/verified status and append concrete verification evidence (commands + outcomes). Do not alter normative requirements to make failures disappear.

- [ ] **Step 10: Produce the clean implementation patch**

From the repository root:

```bash
BASELINE="$(cat .git/adapter-application-freeze-baseline)"
git diff "$BASELINE"...HEAD --binary > adapter-application-freeze-hardening-R3.patch
git diff --name-status "$BASELINE"...HEAD
```

The recorded baseline comes from Execution Setup and removes guesswork. If the executor intentionally keeps the final implementation uncommitted, first commit the implementation tasks as required by this plan; this plan's patch is commit-range based by design. Inspect the patch header/file list before handing it off.

- [ ] **Step 11: Final commit**

```bash
git add docs/superpowers/specs/2026-09-10-adapter-application-freeze-hardening-design-R3.md docs/superpowers/plans/2026-09-10-adapter-application-freeze-hardening.md
git commit -m "docs: close adapter application freeze hardening"
```

---

# Implementation-Plan Self-Review Record

This plan was re-read against every R3 finding/invariant after the first draft. The following defects were found in the plan itself and corrected before handoff:

1. **Wave-order contradiction fixed:** the first draft deferred `cmd_ui` pre-composition cleanup to Task 8 while Wave 1 claimed launcher purity. Task 4 now closes launcher purity; Task 8 only relocates the already-clean behavior.
2. **Task 2 type/order bug fixed:** `prepare()` used `self._config_service` and `requested_device` before defining their service storage/signature. Task 2 now defines both explicitly.
3. **Best-effort state accuracy fixed:** a failed preparation reports the actual current checkpoint rather than blindly returning `None`.
4. **Training rollback gap fixed:** synchronous config activation failure is explicitly pre-commit and rolls resource/handoff ownership back; post-commit failures still do not restore inference.
5. **Background commit ambiguity constrained:** `activate(valid_snapshot)` is required to be in-memory/non-I/O and validation belongs in resolve/plan, avoiding an unnecessary paused-thread protocol.
6. **Guardian allowlist ambiguity fixed:** module allowlisting is exact, never prefix-based, so allowing a package cannot expose its `.service`/`.internal` children.
7. **Public inference primitive leak fixed:** CLI setup primitives are removed from `InferenceGateway` after strict preparation migration; manual checkpoint HTTP use cases remain explicit.
8. **Reverse-dependency risk fixed:** the inner training event hub is forbidden from importing Application DTOs; structural/generic typing preserves dependency direction.
9. **Test-only API smell fixed:** subscription cleanup tests inspect private hub state rather than adding a public `subscriber_count` solely for tests.
10. **Nonexistent test path fixed:** Task 12 names the actual `test_dataset.py`, `test_preprocessors.py`, and `test_tokenizer.py` files.
11. **Patch baseline fixed:** execution records exact starting HEAD and Task 21 builds the patch from that baseline; no guessed commit token remains.
12. **Fallback ownership leak fixed:** Application no longer imports the concrete built-in fallback corpus. Its policy carries only `allow_builtin_fallback_corpus`; the data capability owns the corpus bytes/text.
13. **Typed-event staging contradiction fixed:** Tasks 14–16 are explicitly an ordered migration cluster. Task 14 types raw storage/publishing, Task 15 moves presentation, and Task 16 removes the legacy iterator/heartbeat leak; no temporary Application presentation shim is permitted.
14. **Scope check passed:** no task performs unrelated model/trainer/data algorithm redesign; every inner edit exists only to harden an Adapter/Application contract required by R3.
15. **Compatibility check passed:** HTTP checkpoint operations, training start/stop/clear/status/SSE shape, CLI command names/options, synchronous-vs-background execution modes, and non-restoration of inference after committed training are explicitly retained.
16. **YAGNI check passed:** no command bus, duplicate DI container, speculative checkpoint-catalog interface, or paused background-thread commit protocol is introduced.
17. **Finding traceability passed:** every audited R3 finding F1–F17 maps to at least one repair task and to the final freeze certificate.

## R3 Finding Traceability (17/17)

| R3 finding                                                  | Primary repair task(s) | Final lock |
| ----------------------------------------------------------- | ---------------------- | ---------- |
| F1 — eager inference constructor bootstrap                  | 1–3                    | 20–21      |
| F2 — UI launcher builds two graphs                          | 4, 8                   | 20–21      |
| F3 — sync CLI training bypasses handoff/admission           | 9–11                   | 20–21      |
| F4 — CLI generation owns setup workflow                     | 2, 4                   | 20–21      |
| F5 — command config double resolve/activation               | 1, 2, 9–11             | 20–21      |
| F6 — Diagnostics/Explorer concrete public services          | 5                      | 20–21      |
| F7 — stale tests preserve wrong Diagnostics contract        | 5–6                    | 20–21      |
| F8 — quality gate bypasses Application                      | 6                      | 20–21      |
| F9 — guardian misses root CLI entry point                   | 8                      | 20–21      |
| F10 — guardian deny-list misses future internals            | 7                      | 20–21      |
| F11 — train/val/tokenizer concrete objects cross as `Any`   | 12–13                  | 20–21      |
| F12 — Application state/events contain Web/SSE presentation | 14–16                  | 20–21      |
| F13 — hidden `_device_override` weakens config authority    | 17                     | 20–21      |
| F14 — inference runtime port too broad                      | 18                     | 20–21      |
| F15 — accelerator-family logic duplicated                   | 17                     | 20–21      |
| F16 — Diagnostics device Optionality mismatch               | 19                     | 20–21      |
| F17 — accidental `generate_run_name` public export          | 19                     | 20–21      |

## Spec Coverage Matrix

| R3 requirement / finding family                             | Implemented by | Locked by        |
| ----------------------------------------------------------- | -------------- | ---------------- |
| Inert composition + one graph per worker                    | Tasks 1–4, 8   | Tasks 3, 4, 20   |
| Explicit best-effort Web / strict CLI inference preparation | Tasks 2–4      | Tasks 2–4, 20    |
| Five symmetric public gateways                              | Task 5         | Tasks 5, 20      |
| Diagnostics/gate path through Application                   | Task 6         | Tasks 6, 20      |
| Guardian blind spot/default-deny public surface             | Tasks 7–8      | Tasks 7, 8, 20   |
| One training transaction policy for sync/background         | Tasks 9–11     | Tasks 10, 11, 20 |
| One semantic config snapshot + commit/rollback semantics    | Tasks 1, 9–11  | Tasks 10, 11, 20 |
| Typed opaque data boundary, no train/val/tokenizer `Any`    | Task 12        | Tasks 12, 20     |
| Explorer pure-value boundary                                | Task 13        | Tasks 13, 20     |
| Typed raw training facts                                    | Task 14        | Tasks 14, 20     |
| UI owns rounding/messages/timestamps/SSE/heartbeat          | Tasks 15–16    | Tasks 15, 16, 20 |
| Canonical config device vs transient placement              | Task 17        | Tasks 17, 20     |
| One accelerator-family authority                            | Task 17        | Tasks 17, 20     |
| Narrow inference runtime contract                           | Task 18        | Tasks 18, 20     |
| Diagnostics Optionality/minimal exports                     | Task 19        | Tasks 19, 20     |
| Freeze certificate + full compatibility verification        | Tasks 20–21    | Task 21          |

# Wave Exit Gates

Do not advance merely because a local test happens to pass.

## Wave 1 exit

- [ ] Graph builder performs no config read/activation or inference materialization.
- [ ] `InferenceService` constructor is inert.
- [ ] Default Web preparation is explicit/best-effort in lifespan.
- [ ] CLI generation preparation is explicit/strict.
- [ ] No launcher process constructs a model graph merely for logging.

## Wave 2 exit

- [ ] `ApplicationServices` contains exactly five public gateways.
- [ ] Concrete Application services are internal.
- [ ] CLI diagnostics render data only; quality gate execution goes through DiagnosticsGateway.
- [ ] Root `main.py` is bootstrap-only; real CLI is under the guarded adapter package.
- [ ] Unknown outer imports of Application internals fail by default.

## Wave 3 exit

- [ ] Sync/background training share plan, pin, handoff, admission and config-commit policy.
- [ ] Sync training cannot bypass inference handoff/accelerator ownership.
- [ ] Pre-commit rollback and committed cleanup semantics are explicitly tested.
- [ ] Command-specific config semantic resolution occurs once.
- [ ] No adapter owns resume checkpoint policy or training resource policy.

## Wave 4 exit

- [ ] No concrete train/val/tokenizer/cleaner object crosses Application contracts as `Any`.
- [ ] Explorer does not construct/unpack capability datasets.
- [ ] Training state/event boundary is typed and raw.
- [ ] UI owns rounding, display timestamp, localized lifecycle messages, JSON/SSE and heartbeat.
- [ ] Stream subscription closes on disconnect.
- [ ] Canonical config and transient inference placement are separate.
- [ ] Accelerator-family classification has one authority.
- [ ] Diagnostics device Optionality is type-correct.
- [ ] Application public exports are minimal.

## Final freeze declaration

Only declare Adapter + Application frozen when:

- [ ] full Python suite passes;
- [ ] architecture guardian passes with positive outer-public enforcement;
- [ ] Ruff/Pyright/project quality gates pass in the intended dev environment;
- [ ] frontend build passes after training state/event migration;
- [ ] HTTP/CLI compatibility tests pass;
- [ ] source scans find no unexplained boundary bypass;
- [ ] git diff contains no unrelated core cleanup or generated artifacts;
- [ ] spec contains no unresolved placeholder/bypass in this scope.

At that point, remaining disorder in `src/core`, `src/data`, `src/models`, `src/training`, `src/generation`, and `src/inference` can be treated as inner-module debt without reopening Adapter/Application unless an explicit public contract change is desired.
