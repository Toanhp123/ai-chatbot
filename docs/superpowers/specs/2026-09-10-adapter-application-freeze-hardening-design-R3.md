# Adapter + Application Freeze Hardening Design — R3 Red-Team Revised

## Status

Draft produced from a second red-team audit of `ai-chatbot-main(10)` on 2026-09-10.

This document is a **follow-up and correction layer** over:

- `2026-09-09-application-semantic-ownership-hardening-design.md`
- `2026-09-10-application-adapter-gateway-cleanup-design.md`

Where this document explicitly contradicts either older design, **this document wins for the Adapter/Application freeze scope**. It does not reopen unrelated core/model/training algorithm work.

## Goal

Freeze Adapter + Application as the stable outer communication boundary before deeper core/module cleanup.

The target is stronger than “imports point inward”:

1. **Adapter owns transport, conversion and external I/O only.**
2. **Application owns use-case orchestration and product/use-case policy only.**
3. **Core/capability modules own mechanics, algorithms, runtime objects and resource implementation.**
4. **Composition owns concrete wiring only; construction itself must not secretly execute use cases.**
5. **Every outer entry point reaches a canonical Application use case/gateway.**
6. **Changing an inner capability implementation must not require Adapter changes unless the declared Application contract changes.**
7. **Architecture tests must reject future regressions by default rather than only known historical imports.**

The freeze is complete only when these semantic invariants are true at runtime, not merely when `scripts/check_architecture.py` prints PASS.

## Non-goals

This hardening pass must not:

- optimize model, training, generation or data algorithms;
- redesign model architecture, tokenizer algorithms or trainer internals;
- rewrite the application into a command bus/framework;
- redesign public HTTP routes, response payloads, SSE payload shape, CLI command names or normal user-visible behavior;
- redesign the frontend;
- perform a broad core cleanup unrelated to a boundary leak;
- introduce a second DI container/service locator;
- force synchronous CLI training to become background/threaded simply to share code;
- add speculative abstractions where an existing stable facade/port is sufficient.

Minimal core/capability changes are allowed only when required to remove a proven Adapter/Application boundary leak or duplicated mechanic.

---

# 1. Audit baseline

The audited archive currently has a strong structural baseline:

- full Python suite: **505 passed**;
- architecture guardian: **PASS**;
- no observed Application import cycle;
- Adapters no longer directly import `src.core`, `src.data`, `src.models`, `src.training`, `src.generation` or `src.inference` for normal use-case execution;
- `ConfigGateway`, `InferenceGateway` and `TrainingGateway` already establish a useful public-facade pattern;
- concrete runtime construction is concentrated under `src.composition`.

However, the current guardian mostly proves **module import direction**. It does not prove:

- constructor purity;
- one graph per process;
- canonical workflow ownership;
- resource handoff correctness across different entry points;
- absence of hidden state authorities;
- transport neutrality of Application state/events;
- absence of capability objects hidden behind `Any`;
- that all outer entry points are actually scanned;
- that a newly added Application implementation module will be forbidden automatically.

Therefore the current PASS is a useful baseline, not a freeze certificate.

---

# 2. Red-team findings

## P0 — F1. Composition is not inert: inference bootstrap runs in `InferenceService.__init__`

Evidence:

- `src/application/inference/service.py:53-63`
  - derives the configured checkpoint;
  - calls `runtime.load_tokenizer_if_present(...)`;
  - checks `runtime.path_exists(...)`;
  - may call `self.load_checkpoint(...)`.

Impact:

- constructing Application services performs filesystem/runtime work;
- model/tokenizer materialization can happen for commands that do not request inference;
- composition failures are swallowed into warning logs, so construction has hidden best-effort execution semantics;
- tests that construct services are not testing a pure graph build;
- future composition changes can accidentally execute expensive GPU work.

The audited zip contains `data/vocab.json` but no `.pt/.pth` checkpoint, so the expensive checkpoint branch is latent in this archive. A normal trained installation with `checkpoints/best_model.pt` exercises it.

Required invariant:

> Building the object graph must not load tokenizer/model/checkpoint, reserve accelerators, start workers, read checkpoint existence, or execute a use case.

---

## P0 — F2. `ui` launcher builds two complete Application graphs

Evidence:

- `main.py:163-165` calls `build_application_services()` only to obtain logging settings;
- `main.py:193` starts Uvicorn with `src.ui.app:create_app`, `factory=True`;
- `src/ui/app.py:38-39` builds `ApplicationServices` again.

Impact with current eager inference construction:

- the launcher graph can load tokenizer/checkpoint/model;
- the serving graph can load the same model again;
- the first graph remains reachable while `uvicorn.run(...)` blocks;
- on CUDA/MPS this can become duplicate model residency / VRAM pressure or OOM;
- reload mode makes the process-boundary behavior even less predictable because the launcher/reloader must never own model residency.

Required invariant:

> One serving worker owns one Application graph. The CLI launcher/reloader process must never construct or materialize the inference graph just to configure logging.

---

## P0 — F3. Synchronous CLI training bypasses the resource-handoff transaction

Evidence:

- `TrainingGateway.start()` delegates to `TrainingLaunchApplicationService.start_command()`;
- `TrainingLaunchApplicationService` performs checkpoint pinning, inference handoff, background admission and config commit;
- `TrainingGateway.run()` delegates directly to `TrainingApplicationService.run()`;
- `TrainingApplicationService.run()` only performs plan → prepare → execute.

Compound failure mode:

1. `_compose(train)` may eagerly load configured inference checkpoint onto CUDA/MPS;
2. CLI `training.run(...)` does not call `prepare_for_training(...)`;
3. it does not participate in the same accelerator admission transaction as Web start;
4. training can therefore compete with already-resident inference weights.

Even after eager constructor bootstrap is removed, this remains a correctness hole because another explicit inference preparation may precede a synchronous training run in the same process in the future.

Required invariant:

> Synchronous and background training may use different execution mechanics, but they must share the same planning, resume pinning, inference handoff, accelerator-admission and config-commit policy.

---

## P1 — F4. CLI generation owns an ordering-sensitive use-case workflow

Evidence in `main.py:120-129`:

1. choose backend;
2. mutate vocab path;
3. derive checkpoint path;
4. load checkpoint;
5. then begin generation.

Impact:

- Adapter owns state-transition order rather than only argument conversion/rendering;
- `InferenceGateway` exposes setup primitives (`set_vocab_path`, `configured_checkpoint_path`) primarily so the outer adapter can compose policy itself;
- current eager constructor can load the configured checkpoint once and CLI can load it again explicitly;
- future checkpoint/backend/config policy changes must be mirrored in CLI.

Required invariant:

> An adapter may repeat transport-driven generation calls in an interactive loop, but inference preparation/config/checkpoint selection is one explicit Application transaction.

---

## P1 — F5. Command-specific config can be resolved/activated once during composition and resolved again during the use case

Evidence:

- `src/composition/root.py:159-161` resolves + activates a config document during every graph construction, including the default document when no CLI override is supplied;
- for CLI commands, the same `config_path/overrides` can therefore be consumed during composition;
- `main.py:70-75` then puts that same source/overrides into `TrainingCommand`;
- `TrainingApplicationService.plan()` resolves that request again at `src/application/training/service.py:65-67`.

Impact:

- runtime/inference state may be assembled from snapshot A while training plan uses snapshot B if the file changes between reads;
- composition becomes command-aware rather than graph-only;
- config activation is a hidden side effect of graph construction;
- the authority model is harder to reason about.

Required invariant:

> A command-specific config must be resolved exactly once for the semantics of that use-case transaction. Production composition itself must not resolve or activate config documents. Default or command config becomes active only through an explicit startup/use-case transaction.

Read-only logging settings may resolve the same external document separately **only if that read does not activate or mutate runtime/Application state**. This is an explicit compatibility exception, not a second runtime authority.

---

## P1 — F6. Public gateway surface is asymmetric: Diagnostics and Explorer expose concrete services

Evidence:

`src/application/services.py` currently contains:

- `config: ConfigGateway`
- `inference: InferenceGateway`
- `training: TrainingGateway`
- `diagnostics: DiagnosticsApplicationService`
- `explorer: ExplorerApplicationService`

`src/application/diagnostics/__init__.py` and `src/application/explorer/__init__.py` re-export the concrete service classes.

Impact:

- public boundary has two competing conventions;
- outer code can couple to Application implementation classes;
- later internal service decomposition can propagate outward;
- the typed `ApplicationServices` claim is weaker than its name suggests.

Required invariant:

> Every capability in `ApplicationServices` is an adapter-facing Gateway/facade; concrete Application services are internal implementation details.

A gateway may be a thin wrapper when it protects this real architectural boundary. Thinness alone is not a reason to remove it.

---

## P1 — F7. Existing tests actively preserve the wrong Diagnostics public contract

Evidence:

`tests/test_application_boundaries.py:609-615` asserts that the CLI diagnostics adapter contains `DiagnosticsApplicationService`.

Impact:

- the suite is green while ratcheting two different public-boundary standards;
- simply adding `DiagnosticsGateway` without changing the tests would make the desired architecture fail its own guard.

Required invariant:

> Boundary tests must encode the target architecture, not historical implementation names.

---

## P1 — F8. CLI quality-gate execution bypasses Application

Evidence:

- `main.py:158-160` calls `run_quality_gates_cli()` directly;
- `src/adapters/cli/diagnostics.py:194-197` imports `scripts.check_all.main`;
- HTTP quality gates already go `Application -> DiagnosticsRuntimePort -> DiagnosticsRuntimeAdapter`.

Impact:

- one use case has two execution paths;
- CLI adapter knows developer-tool process implementation;
- Application is not the canonical entry point.

Required invariant:

> CLI and HTTP quality-gate actions go through `DiagnosticsGateway`; only the diagnostics runtime adapter knows `scripts.check_all`.

---

## P1 — F9. Architecture Guardian has an outer-entry-point blind spot

Evidence:

- `scripts/check_architecture.py:354-356` invokes `check_architecture_boundaries("src")`;
- root `main.py` is the primary CLI adapter but is outside `src/`;
- therefore `main.py` is not covered by the dependency matrix.

Impact:

- root CLI could import core/training/inference implementations tomorrow and the guardian would still report PASS;
- current cleanliness of `main.py` is convention, not enforced architecture.

Required invariant:

> All real CLI orchestration lives under `src/adapters/cli/**`, where guardian rules apply. Root `main.py` is a minimal bootstrap that imports and invokes that adapter entry point only.

A focused test must lock the root bootstrap shape.

---

## P1 — F10. Architecture Guardian is deny-list based and misses new Application implementation modules

Evidence:

- current `src.ui` / `src.adapters` forbidden lists enumerate known modules such as `config.service`, `inference.service`, `training.service/background/launch`;
- diagnostics/explorer implementation modules are absent;
- `FORBIDDEN_IMPORTED_SYMBOLS = {}`.

Impact:

- creating `src.application.foo.internal` or re-exporting a concrete `FooService` can silently create a new outer dependency;
- the guard is historical rather than default-safe.

Required invariant:

> Outer code may import only an explicit Application **public surface**. New Application implementation modules are inaccessible to outer layers by default.

Prefer a public-module/symbol allowlist for outer → Application dependencies over indefinitely extending a list of known bad modules.

---

## P1 — F11. Concrete data/tokenizer objects cross Application through `Any`

Evidence:

`TrainingRuntimePort.prepare()` currently declares:

- `train_data: Any`
- `val_data: Any`
- `tokenizer: Any`

`TrainingApplicationService.prepare()` constructs/receives those objects through `prepare_application_dataset()` and passes them onward.

`src/application/data_policy.py` also constructs `primary`/`fallback` cleaner objects and tokenizer objects as `Any`.

Impact:

- imports look clean while runtime shapes remain semantically coupled;
- changing Data concrete return types can break Training/Application without changing any declared contract;
- Application is holding capability mechanics, not only selecting policy;
- type checking cannot protect the boundary.

Required invariant:

> Application expresses data-selection/fallback policy as pure values/specs. Concrete cleaner/tokenizer/tensor/dataset shapes must never appear in Application. When orchestration needs to carry prepared data between ports, it may carry only an Application-owned **opaque typed handle/protocol** that Application never inspects.

Application still owns the product decision “Gemini may explicitly fall back to standard for the allowed recoverable failure”; the Data capability owns construction and execution of that fallback strategy.

---

## P1 — F12. Training Application state mixes lifecycle policy with Web/SSE presentation projection

Evidence in `src/application/training/background.py`:

- `_WebTrainingObserver`;
- docs/comments explicitly mention HTTP/SSE/Web/UI/REST;
- metric rounding occurs in Application (`round(...)`);
- sample timestamp is presentation-formatted with `time.strftime("%H:%M:%S")`;
- localized user-facing messages are embedded in status events;
- state/event contracts are `dict[str, Any]`.

Additionally, `TrainingEventPort` exposes `heartbeat_seconds`, while the concrete `TrainingEventHub` emits `{"type": "heartbeat"}` specifically for streaming keepalive.

Impact:

- Application knows presentation/transport vocabulary;
- REST/SSE shapes influence internal state representation;
- UI formatting changes can force Application edits;
- a future non-HTTP adapter inherits Web-specific messages/timestamps.

Required invariant:

> Application owns lifecycle state, sequence/reconciliation rules, bounded history policy and raw metrics. Adapter owns JSON/SSE framing, keepalive heartbeat, localized presentation strings, numeric formatting and display timestamps.

---

## P2 — F13. Config authority claim is weakened by hidden `_device_override`

Evidence:

`InferencePreferences` says shared `ConfigurationService` is the only active-config authority, but also stores `_device_override` and makes `configured_device` prefer that shadow value.

Impact:

- “configured preference” and “transient runtime placement” are conflated;
- callers cannot tell whether a value belongs to canonical config or runtime state;
- config activation clears the override implicitly.

Required invariant:

> Persistent/requested inference preferences come from canonical config. A transient placement override, if still required, is explicitly modeled as runtime state/request input and is never presented as a second config authority.

---

## P2 — F14. `InferenceRuntimePort` combines too many mechanics

The port currently combines:

- filesystem/path operations;
- checkpoint catalog operations;
- tokenizer bootstrap;
- backend catalog/selection;
- device resolution;
- model checkpoint loading;
- runtime residency handoff;
- generation execution.

Impact:

- large fake burden;
- changes to checkpoint catalog mechanics can touch execution fakes;
- constructor bootstrap encouraged path/filesystem methods to leak into inference orchestration.

Required invariant:

> Remove methods that exist only because construction was eager. Split the port only where there are independently changing responsibilities; do not fragment it into one-method interfaces without evidence.

This is a hardening target, not permission for a broad inference rewrite.

---

## P2 — F15. Accelerator-family logic is duplicated between Application and core

Evidence:

- `src/application/runtime/contracts.py` defines `same_accelerator_family(...)`;
- `src/core/accelerator.py` defines the same mechanic independently.

Impact:

- one resource-classification mechanic has two authorities;
- future device-family support can drift between admission policy and coordinator mechanics;
- the architecture rule currently encourages duplication by forbidding the concrete core module rather than providing a stable capability contract/facade.

Required invariant:

> There is exactly one authority for accelerator-family classification. Application consumes that classification through a stable inner facade or injected port; it must not duplicate the mechanic.

---

## P2 — F16. Diagnostics DTO has a real Optionality mismatch

Evidence:

- HTTP `VRAMEstimateRequest.device` is `Optional[str] = None`;
- `to_application()` forwards `None` directly;
- `VramEstimateInput.device` is annotated `str = "auto"`;
- service implementation already treats it as optional via `(request.device or base.system.device)`.

Impact:

- runtime behavior and type contract disagree;
- a stricter type checker/consumer can make different assumptions than the code.

Required invariant:

> `None` explicitly means “inherit canonical active config”; the Application DTO must type that semantics as `Optional[str]`.

---

## P2 — F17. Public Application exports still contain implementation utility `generate_run_name`

`src/application/training/__init__.py` exports `generate_run_name`, although production outer adapters do not need it.

Impact:

- public surface is broader than required;
- tests/consumers can accidentally couple to an implementation helper.

Required invariant:

> Public Application packages export only gateways, adapter-safe command/result DTOs, errors and ports that outer implementations genuinely need.

---

# 3. Chosen strategy

Three approaches were considered.

## Approach A — Patch only visible leaks

Add `DiagnosticsGateway` / `ExplorerGateway`, update guardian rules, leave workflow and constructor behavior intact.

Rejected because it would make import graphs look cleaner while leaving the two P0 runtime hazards and `Any` semantic coupling untouched.

## Approach B — Replace Application with a command bus/use-case framework

Put every action behind generic `CommandHandler` / mediator infrastructure.

Rejected as unnecessary abstraction. The repository already has useful typed gateways and services; replacing them would increase migration risk and obscure existing behavior.

## Approach C — Freeze by invariants, incrementally harden existing services **(selected)**

Keep the current architecture and repair only proven boundary failures:

1. make graph construction inert and process ownership explicit;
2. make every public capability symmetric behind gateways and close guardian blind spots;
3. unify ordering-sensitive use-case transactions without forcing identical execution mechanics;
4. remove semantic `Any`/presentation leaks from the stability-critical contracts;
5. ratchet each invariant with adversarial tests.

This produces a stable outer gate without rewriting the core.

---

# 4. Target architecture

```text
root main.py
    -> src.adapters.cli.entrypoint
        -> ApplicationServices
            -> ConfigGateway
            -> InferenceGateway
            -> TrainingGateway
            -> DiagnosticsGateway
            -> ExplorerGateway

FastAPI routes / response adapters
    -> ApplicationServices
        -> same five public gateways

Application gateways
    -> internal Application services/use-case coordinators
        -> Application-owned ports / stable core-capability facades

Composition
    -> constructs concrete port implementations
    -> wires graph only
    -> does not execute checkpoint/model/training/generation use cases

Inner capabilities/core
    -> data/model/training/inference/generation/resource mechanics
```

## Public-boundary rule

Outer code may know:

- `ApplicationServices`;
- public gateways;
- adapter-facing commands/results/DTOs;
- Application-owned port contracts required by an adapter implementation;
- public Application error facade.

Outer code must not know:

- `*ApplicationService` implementation classes;
- `TrainingPlan`, prepared runtime handles or concrete runtime objects;
- `ConfigurationService`;
- service/background/launch implementation modules;
- `EngineConfig` or other inner runtime objects through public gateways.

---

# 5. Wave 1 — Make construction and process ownership inert

## 5.1 Remove inference bootstrap from constructors

`InferenceService.__init__` and `from_engine_config` become state wiring only.

For this spec, **inert construction** means no config-document read/activation, checkpoint/tokenizer/model materialization, filesystem existence decision for bootstrap, accelerator lease, generation admission, or worker start merely because the graph was built. Cheap inner-runtime parameter validation/device capability probing that acquires no persistent resource is not a freeze blocker; deeper constructor purity inside core capabilities is deferred to core cleanup.

Forbidden during constructor execution:

- `path_exists`;
- tokenizer loading;
- checkpoint/model loading;
- accelerator reservation;
- generation admission;
- background worker start;
- best-effort catch-and-log startup execution.

Introduce one explicit Application inference-preparation use case. Exact class naming is secondary, but the contract must carry adapter-safe intent such as:

- optional config request;
- optional checkpoint path;
- optional vocab path;
- optional backend;
- whether the checkpoint must be managed;
- strict vs best-effort default bootstrap semantics.

### CLI generation

The CLI performs:

1. convert arguments to one preparation command;
2. call `InferenceGateway.prepare(...)` once;
3. render one or many `begin_generation_command(...)` streams for interactive prompts.

The CLI no longer:

- mutates vocab preference directly as setup policy;
- derives the configured checkpoint itself;
- sequences checkpoint load before generation itself.

### Web startup

Preserve current effective product behavior: default inference bootstrap remains best-effort, but becomes explicit.

The FastAPI application lifespan/startup path:

1. builds one inert `ApplicationServices` graph without reading/activating config;
2. invokes best-effort default inference preparation once per serving worker; that explicit transaction resolves + activates the default config before deriving vocab/checkpoint/backend;
3. records/logs a not-ready result on missing/invalid checkpoint instead of failing graph construction, matching current tolerance;
4. only then enters normal serving lifespan.

No model must be materialized in the Uvicorn launcher/reloader parent.

## 5.2 Eliminate `cmd_ui` pre-composition

Move actual CLI command orchestration under `src/adapters/cli/entrypoint.py`.

Root `main.py` becomes a minimal executable bootstrap. It must not build `ApplicationServices` directly.

`ui` launcher starts Uvicorn without building the graph first. Logging bootstrap must not require graph materialization. If app-configured logging is needed, it may be configured/reconfigured inside the serving process after the inert graph/config gateway exists.

## Wave 1 acceptance tests

1. Constructing `InferenceService` with a spy runtime causes **zero** calls to:
   - path existence;
   - tokenizer load;
   - checkpoint load;
   - accelerator reservation.
2. `build_application_services()` does not materialize inference.
3. `build_application_services()` does not call the config provider's load/read path and does not activate a config snapshot.
4. `check`, `estimate`, `inspect` and `train` composition do not load inference.
5. `ui` launcher does not call `build_application_services()` before Uvicorn factory startup.
6. one `create_app()`/lifespan worker performs at most one default preparation transaction.
7. missing default checkpoint preserves current best-effort Web startup behavior.
8. CLI generation preparation is strict enough to report a missing requested checkpoint rather than hiding it.

## Wave 1 exit gate

No expensive/use-case side effect occurs as a consequence of constructing the object graph.

---

# 6. Wave 2 — Freeze the public gateway and guardian surface

## 6.1 Add `DiagnosticsGateway` and `ExplorerGateway`

`ApplicationServices` becomes:

```text
config       -> ConfigGateway
inference    -> InferenceGateway
training     -> TrainingGateway
diagnostics  -> DiagnosticsGateway
explorer     -> ExplorerGateway
```

Concrete `DiagnosticsApplicationService` and `ExplorerApplicationService` stay internal.

Diagnostics/Explorer public packages may export adapter-safe DTOs and required ports, but not concrete services.

## 6.2 Make CLI renderers render data, not invoke services

`src.adapters.cli.diagnostics` should own terminal formatting only.

Preferred flow:

```text
CLI arguments
 -> DiagnosticsGateway use case
 -> result DTO/mapping
 -> CLI renderer
 -> stdout/exit code
```

Renderer functions must not accept `DiagnosticsApplicationService`.

## 6.3 Route quality gates through DiagnosticsGateway

Only `DiagnosticsRuntimeAdapter` may import developer-tool implementation such as `scripts.check_all`.

The CLI uses the same Application quality-gate use case as HTTP, then maps the result to terminal rendering/process exit status.

## 6.4 Close the root CLI blind spot

All real CLI orchestration goes under `src/adapters/cli/**`.

Root `main.py` may only:

- import the public CLI adapter entrypoint;
- call it under the normal `if __name__ == "__main__"` guard.

Add a regression test for that shape.

## 6.5 Replace historical deny-list behavior with a default-safe public-surface rule

For `src.ui` and `src.adapters`, architecture enforcement must distinguish:

- **allowed public Application modules/symbols**;
- all other Application implementation modules, denied by default.

A new `src.application.foo.internal` must not become outer-importable merely because nobody added it to a forbidden list yet.

Adapter implementations of Application-owned ports should import their contracts from a deliberate public package/facade rather than reaching into arbitrary internal modules.

`src.application.errors` remains an explicit stable exception facade.

## 6.6 Shrink accidental public exports

Remove `generate_run_name` from `src.application.training.__all__`.

Apply the same test to other Application `__all__` declarations: every exported item needs a real outer consumer or adapter-port implementation reason.

## Wave 2 acceptance tests

1. `ApplicationServices` type annotations contain gateways only.
2. `src.application.diagnostics` and `src.application.explorer` do not export concrete services.
3. no production file under `src.ui` or `src.adapters` imports `*.service`, `*.background`, `*.launch` or arbitrary internal Application modules.
4. a synthetic/new Application internal module import from outer code is rejected without adding another forbidden string first.
5. importing a concrete `*ApplicationService` symbol through a public package from outer code is rejected.
6. existing test `test_cli_diagnostics_adapter...` is rewritten to assert the new gateway/data-renderer contract rather than `DiagnosticsApplicationService` presence.
7. root `main.py` is locked as thin bootstrap.
8. CLI quality gates contain no direct `scripts.check_all` import.

## Wave 2 exit gate

The public outer contract has one convention and future implementation modules are closed by default.

---

# 7. Wave 3 — Canonicalize ordering-sensitive use-case transactions

## 7.1 One training policy transaction, two execution modes

Do **not** force CLI synchronous execution through the background worker.

Instead, centralize the shared policy sequence used by both `run` and `start`:

1. resolve and snapshot `TrainingCommand` config once;
2. derive `TrainingPlan` once;
3. pin optional resume checkpoint + capture identity once;
4. prepare reversible inference handoff for the resolved training device;
5. secure training accelerator ownership;
6. commit run acceptance;
7. activate the requested canonical config at the defined commit point;
8. branch into:
   - synchronous prepare/execute for CLI;
   - background prepare/execute for Web;
9. release training accelerator ownership in `finally` after committed execution.

`TrainingGateway.run()` must no longer call `TrainingApplicationService.run()` directly. It must go through the same launch/transaction coordinator policy used by `start()`.

### Commit and rollback semantics

To preserve current behavior and avoid inventing new lifecycle semantics:

- **pre-commit failure** (resume pinning, handoff, admission/start failure) rolls back reversible inference handoff;
- once training ownership is successfully committed, later preparation/execution failure releases training resources but does **not** automatically restore inference to its previous accelerator residency;
- successful completion also preserves current post-training inference behavior; automatic reload/restore of the newly trained checkpoint is outside this spec.

This matches the existing background path more closely than an eager “always rollback on any exception” design.

## 7.2 Command-specific config is not a composition concern

`build_application_services()` is wiring-only: it constructs `YamlConfigProvider`, `ConfigurationService`, gateways and runtime adapters, but it does **not** call `resolve()`/`activate()` and does not read a config document as part of graph construction.

Default activation is explicit. The Web startup inference-preparation transaction resolves + activates the default request before default checkpoint preparation. CLI use cases resolve their own request as needed.

Each command use case receives its own `ConfigRequest`/command fields and resolves its semantic snapshot inside Application exactly once.

Examples:

- Training resolves inside training planning/transaction.
- Diagnostics scenarios/inspect resolve inside the diagnostics use case.
- Inference preparation resolves/activates inside the preparation transaction.

A separate read-only `ConfigGateway.logging_settings(request)`-style operation may resolve logging settings for CLI presentation/bootstrap, provided it does not activate config or create runtime state.

## 7.3 Canonical CLI generation preparation

Introduce an adapter-safe preparation command/result.

The Application transaction owns:

- effective config resolution/activation when requested;
- effective vocab/checkpoint/backend selection;
- checkpoint path policy;
- device/backend validation;
- tokenizer/checkpoint loading;
- inference residency/admission bookkeeping.

After this migration, remove public setup primitives from `InferenceGateway` if no outer route genuinely needs them. In particular, `set_vocab_path` and `configured_checkpoint_path` should not remain public solely to support CLI orchestration.

Existing explicit HTTP user actions such as `POST /checkpoints/load` and generator backend selection remain separate valid use cases.

## 7.4 Checkpoint trust ownership clarification

This R3 spec supersedes the stale wording in the 2026-09-09 design that said HTTP must own resume-checkpoint root validation.

Final rule:

- HTTP/CLI adapter owns transport syntax and generic external path-input normalization where required for its transport security boundary;
- **managed checkpoint membership/resolution/pinning is use-case policy** shared across transports and remains behind the Application-owned checkpoint port;
- adapters must not duplicate the managed-checkpoint policy.

## Wave 3 acceptance tests

1. CLI `training.run()` invokes the shared handoff/admission transaction.
2. with fake inference residency on the same accelerator, synchronous training cannot begin without handoff/ownership transfer.
3. failed pre-commit synchronous admission rolls inference handoff back.
4. committed synchronous run always releases training ownership in `finally`.
5. background behavior remains compatible with existing start/stop/clear/status semantics.
6. command-specific Training config provider is resolved once by the training semantic transaction.
7. mutating the backing config source after planning cannot mutate the frozen run plan.
8. composition does not activate CLI command-specific config.
9. CLI generation calls one preparation transaction and does not sequence `set_vocab_path -> derive checkpoint -> load_checkpoint` itself.
10. explicit HTTP checkpoint load and backend-selection behavior remains compatible.

## Wave 3 exit gate

All entry points share use-case policy; only their transport and execution-mode mechanics differ.

---

# 8. Wave 4 — Harden semantic contracts and remove presentation leaks

## 8.1 Remove concrete training data objects from Application contracts

Replace this boundary:

```text
Application
 -> prepare_application_dataset()
 -> train_data: Any / val_data: Any / tokenizer: Any
 -> TrainingRuntimePort.prepare(...)
```

with two explicit Application-owned contracts:

```text
DataPreparationSpec (pure policy/value input)
DataPreparationPort.prepare(spec) -> PreparedDataHandle
TrainingRuntimePort.prepare(..., data=PreparedDataHandle, ...)
```

`PreparedDataHandle` is an opaque structural protocol/token. Application may store it and pass it to another port, but it must not expose train/val tensors, tokenizer instances or capability-specific fields. Concrete adapters/bridges outside Application may wrap/unwrap the capability-owned bundle. This mirrors the existing prepared-training handle pattern without using `Any`.

The pure preparation specification may contain stable values such as:

- canonical `DataConfig` snapshot or equivalent policy values;
- model block size;
- explicit cleaner selection;
- explicit allowed fallback cleaner policy;
- whether built-in fallback corpus is allowed;
- whether fallback may be persisted.

The concrete data capability still owns:

1. cleaner/tokenizer construction;
2. execution of the explicitly requested fallback strategy;
3. dataset/tensor preparation.

The concrete training runtime still owns trainer/run construction. An infrastructure/composition bridge may only **adapt/unwrap declared handles and delegate** between these capability APIs; it must not choose fallback policy, alter config or implement data/training algorithms. The composition root itself remains wiring-only.

No `train_data`, `val_data`, concrete tokenizer or concrete cleaner type appears in an Application-owned port signature.

### Fallback ownership rule

Application owns the decision:

> “For this use case, cleaner A may fall back to cleaner B on the capability's declared recoverable cleaner failure.”

Data capability owns:

- cleaner construction;
- invoking A/B;
- detecting its concrete recoverable failure;
- tokenization/dataset mechanics.

Thus fallback is explicit policy, not a silent capability substitution, while mechanics remain out of Application.

## 8.2 Clean Explorer data calls without inventing capability objects in Application

Explorer may continue to call the stable `src.data.api` facade if that facade accepts pure values/policy and returns transport-neutral result mappings/DTOs.

It must not construct or hold concrete cleaner/tokenizer/dataset objects itself.

`export_binary` should delegate one facade/port operation that performs data preparation + export mechanics internally instead of unpacking concrete train/val data in Application.

## 8.3 Separate lifecycle state from Web presentation

Keep in Application:

- run status state machine;
- run id / sequence;
- termination reason;
- cancellation policy;
- bounded history/reconciliation semantics;
- raw step/eval/sample facts;
- training resource lifecycle.

Move to Adapter/UI:

- `Web` / `UI` / `REST` / `SSE` naming and comments;
- localized status presentation strings;
- metric rounding for display;
- `%H:%M:%S` display timestamp formatting;
- JSON mapping;
- SSE framing;
- heartbeat/keepalive frames.

Rename `_WebTrainingObserver` to a transport-neutral Application name or remove it in favor of an internal lifecycle observer.

## 8.4 Stabilize training state/event contract

`TrainingGateway.get_state()` and stream boundary are stability-critical and must not remain unbounded `dict[str, Any]` contracts.

Use typed Application-owned DTOs/protocols for state and events. Exact implementation can be dataclasses/TypedDict-style contracts, but the following must be explicit:

- status;
- run id;
- sequence;
- termination reason;
- optional error fact/code/detail;
- current raw metrics;
- bounded history entries;
- event kinds.

The UI adapter maps those DTOs back to the **existing external JSON/SSE shape**.

### Heartbeat design

Application must not emit an SSE heartbeat event.

Preferred boundary:

- gateway returns a closeable/subscribable transport-neutral event stream/subscription;
- adapter chooses its own wait timeout;
- timeout/no event becomes an SSE comment heartbeat in `TrainingStreamingResponse`;
- disconnect/finally closes the subscription and unregisters the consumer.

If the concrete event hub needs queue timeouts internally, that timeout remains subscriber mechanics and must not surface as an SSE-named Application contract.

## 8.5 Resolve transient inference placement explicitly

Remove the ambiguous `_device_override` “config but not config” semantics.

Choose one explicit model:

- canonical requested device remains in `ConfigurationService`;
- a per-operation/runtime placement override is passed in an inference preparation/load command and reported as runtime state;
- it does not mutate or shadow canonical config unless the use case explicitly activates a new config.

`configured_device` must not silently mean two different authorities.

## 8.6 Remove duplicate accelerator-family mechanic

There must be one classification authority for CUDA/MPS/CPU ownership families.

Acceptable implementation options:

1. expose the pure classification through a stable inner/core runtime facade consumed by Application; or
2. expose it through the injected accelerator/resource port.

Do not retain independent copies in both Application and core.

## 8.7 Narrow `InferenceRuntimePort` after bootstrap migration

After constructor bootstrap is removed, reassess each method.

At minimum, methods present only to support hidden construction (`path_exists`, standalone tokenizer bootstrap, path joining if no longer required) should leave the broad execution port.

If checkpoint catalog and execution evolve independently in current code, split into a small checkpoint-catalog port and execution/runtime port. Do not split merely to maximize interface count.

## 8.8 Fix Diagnostics Optionality contract

Change `VramEstimateInput.device` to `Optional[str] = None` with the explicit meaning “inherit active config”.

Keep HTTP omission semantics unchanged.

## Wave 4 acceptance tests

1. no `train_data: Any`, `val_data: Any` or `tokenizer: Any` in Application training runtime contracts.
2. Application data policy contains no concrete cleaner/tokenizer wrapper object.
3. Explorer Application does not unpack capability train/val dataset objects.
4. Training Application production files contain no Web/REST/SSE/UI ownership assumptions.
5. raw Application metrics are not rounded for presentation.
6. display timestamp formatting lives outside Application.
7. SSE heartbeat is generated by the UI response adapter, not Application.
8. stream disconnect closes/unsubscribes without leaking subscriber queues.
9. external `/api/training/status` and `/api/training/stream` shapes remain compatible.
10. canonical config and transient runtime placement are distinguishable in tests.
11. only one accelerator-family classification implementation remains.
12. `VramEstimateInput(device=None)` is type-correct and inherits active config.

## Wave 4 exit gate

Application contracts express use-case intent/state, not concrete capability objects or presentation transport.

---

# 9. Compatibility contract

The hardening must preserve externally observable behavior unless a current behavior is itself the proven architecture bug.

## HTTP

Preserve routes and normal response shapes for:

- inference state/generation;
- checkpoint list/load/delete/download;
- model list;
- raw config read/save;
- training feasibility/start/stop/clear/status/stream;
- diagnostics system/estimate/scenarios/advisor/gates/inspect/logs;
- explorer endpoints.

Adapter-only formatting may move locations without changing the payload expected by the frontend.

## CLI

Preserve command names/options and normal terminal behavior:

- `check`
- `estimate`
- `inspect`
- `train`
- `generate`
- `gate`
- `ui`

Interactive generation remains an Adapter-owned read/render loop. Only its setup transaction moves inward.

## Training lifecycle

Preserve:

- quick-check semantics;
- feasibility remains advisory unless existing product policy says otherwise;
- resume checkpoint pinning/revision protection;
- background stop/clear behavior;
- bounded histories;
- current post-success inference behavior (no new automatic restore/reload in this spec).

---

# 10. Architecture and verification ratchet

## Structural checks

Add/strengthen tests for:

- outer public Application import allowlist;
- no concrete Application service import from adapters/UI;
- root `main.py` thinness;
- `ApplicationServices` gateways only;
- no inner runtime object exported publicly;
- no capability object typed as `Any` in stability-critical Application ports;
- no new outer service-locator entries besides `app.state.services`.

## Behavioral boundary checks

Structural AST checks are insufficient. Add behavior tests proving:

- service construction is inert;
- one Web worker creates/prepares one graph;
- CLI train uses handoff/admission;
- rollback/release semantics are correct;
- command config snapshot cannot drift after planning;
- generation setup is Application-owned;
- stream subscription closes on disconnect.

## External compatibility checks

Keep/extend route tests for exact response/event keys relied upon by the frontend.

Run available frontend type/build verification after any state/event mapping migration.

## Final verification sequence

At the end of the implementation pass:

1. focused tests for the changed wave;
2. full `python -m pytest -q`;
3. `python scripts/check_architecture.py`;
4. project quality gate where available;
5. type/lint/format gates where dependencies are installed;
6. frontend tests/typecheck/build where dependencies are available.

Do not claim a freeze solely because unit tests are green if an architecture/adversarial check is skipped.

---

# 11. Self-review — conflicts and holes resolved in this R3 spec

This section is normative. It records contradictions found while red-teaming both the code and the prior designs.

## C1. “Composition must be inert” vs “Web should auto-load default checkpoint”

Resolution:

- object-graph construction is inert;
- Web default bootstrap remains, but is an explicit lifespan/startup Application use case;
- therefore auto-load behavior is preserved without constructor side effects.

## C2. “One Application use case per adapter action” vs interactive CLI generation

Literal one-call-per-process would be wrong because every prompt is a new user action.

Resolution:

- one explicit Application **preparation transaction** owns ordering-sensitive setup;
- each subsequent user prompt invokes the generation use case;
- Adapter keeps input/render loop only.

## C3. “CLI and Web training must use the same flow” vs sync/background execution

Forcing CLI into a thread would couple policy to transport/execution style.

Resolution:

- share planning/pinning/handoff/admission/config-commit transaction policy;
- branch only after admission into synchronous or background execution mechanics.

## C4. “Application owns fallback policy” vs “Application must not own cleaner mechanics”

Resolution:

- Application expresses explicit fallback intent as pure policy/spec;
- Data capability executes concrete cleaner construction/fallback mechanics;
- no silent capability fallback and no concrete cleaner object in Application.

## C5. “Everything should be typed” vs flexible Diagnostics/Explorer reports

Making every diagnostic map a large rigid DTO would create unnecessary churn.

Resolution:

- require strong typed contracts on stability-critical live boundaries: training state/events, commands/results, resource transactions;
- Diagnostics/Explorer may return documented `Mapping[str, object]` where their report schema is intentionally extensible;
- do not use `Any` to shuttle capability objects; use an explicit opaque Application-owned handle only where orchestration genuinely needs to carry one.

## C6. “Adapter owns path validation” vs shared managed checkpoint policy

Prior spec wording placed resume root validation at HTTP edge, while current architecture correctly has an Application-owned checkpoint port.

Resolution:

- adapter owns transport/security syntax checks specific to its transport;
- Application owns shared managed checkpoint resolution/pinning policy through its port;
- no duplicate HTTP-only checkpoint policy.

## C7. “ConfigurationService is sole authority” vs transient `cuda:0` override

Resolution:

- canonical preference stays in ConfigurationService;
- transient runtime placement is explicit operation/runtime state, not a hidden preference shadow.

## C8. “Move heartbeat outward” vs stream liveness/disconnect cleanup

Removing timeout behavior naively could make a disconnected subscriber block forever.

Resolution:

- retain timeout/subscriber mechanics behind a closeable stream/subscription;
- Adapter chooses keepalive cadence and emits SSE heartbeat;
- add disconnect/unsubscribe regression tests before deleting old behavior.

## C9. “No behavior change” vs moving Web bootstrap timing

Resolution:

- preserve best-effort default bootstrap before normal serving lifespan;
- missing checkpoint remains non-fatal/not-ready rather than making app construction fail;
- only the ownership/timing boundary changes.

## C10. “One config resolution” vs config-based CLI logging

Forcing logger bootstrap and use-case execution to share an inner `EngineConfig` object would leak the config type outward or require an unnecessary session-token system.

Resolution:

- command **semantic runtime state** resolves once inside the use case;
- optional read-only logging-settings resolution may happen separately but cannot activate Application/runtime state;
- composition never consumes command-specific config as runtime state.

## C11. Removing eager inference load alone appears to fix CLI train VRAM conflict

That would be fragile: another explicit inference preparation could reintroduce the conflict.

Resolution:

- Wave 1 removes the current trigger;
- Wave 3 independently makes synchronous training participate in canonical handoff/admission;
- both defenses are required before freeze.

## C12. “Rollback inference on failure” vs existing committed-run semantics

Always restoring inference after any training exception would change current background lifecycle behavior and can conflict with released/partially initialized resources.

Resolution:

- rollback only pre-commit admission/start failures;
- after training ownership commits, always release resource ownership but preserve current non-restoration semantics;
- post-training restore/reload is a separate future product decision.

## C13. “Architecture Guardian PASS means outer boundary is locked”

False because root `main.py` is outside the scanned `src` tree and new internal Application modules are not denied by default.

Resolution:

- move real CLI orchestration under guarded adapter package;
- make root main thin;
- enforce a positive public Application surface for outer imports.

## C14. “Application uses only facades, therefore no semantic coupling exists”

False because concrete dataset/tokenizer shapes cross through `Any` even though imports use `src.data.api`.

Resolution:

- freeze requires contract-level purity in addition to import-level purity;
- Application may carry only an opaque typed handle that exposes no capability shape; concrete dataset/tokenizer objects are wrapped/unwrapped outside Application.

## C15. “TrainingEventHub is transport-neutral because it emits dicts”

False: a `heartbeat` marker and heartbeat interval are still transport keepalive semantics even without literal SSE strings.

Resolution:

- state/event facts remain transport-neutral;
- keepalive cadence/frame generation moves to the UI streaming adapter.

## C16. “Duplicating a tiny pure helper is harmless”

The duplicated accelerator-family helper classifies resource ownership and therefore can alter admission correctness if the copies diverge.

Resolution:

- one classification authority only; consume it through a stable facade/port.

---

# 12. Freeze exit criteria

Adapter + Application may be declared **frozen/clean enough for deep core cleanup** only when all conditions below are true.

## Adapter

- [ ] Root `main.py` is bootstrap-only.
- [ ] Real CLI implementation is under guarded `src/adapters/cli/**`.
- [ ] Adapters perform transport conversion, rendering, external I/O and adapter-specific security checks only.
- [ ] No Adapter calls concrete Application services.
- [ ] No Adapter sequences ordering-sensitive core/use-case state transitions.
- [ ] Quality gates route through DiagnosticsGateway.
- [ ] UI owns JSON/SSE/heartbeat/presentation formatting.

## Application public surface

- [ ] `ApplicationServices` contains five gateways only.
- [ ] Concrete Application services are not publicly exported to outer layers.
- [ ] Public exports are minimal and intentional.
- [ ] Training state/event boundary is typed.
- [ ] No concrete dataset/tokenizer/cleaner/runtime shape crosses the public/runtime contract as `Any`; any necessary carried capability value is an opaque typed handle.

## Application semantics

- [ ] Constructors are inert.
- [ ] No config document is resolved or activated during production composition; default/command activation is explicit.
- [ ] CLI/Web training share canonical transaction policy.
- [ ] CLI generation setup is an Application transaction.
- [ ] Canonical config and transient runtime placement are distinct.
- [ ] Application training state contains no Web/REST/SSE/UI presentation policy.
- [ ] Accelerator-family classification has one authority.

## Composition/runtime

- [ ] One serving worker owns one graph.
- [ ] Launcher/reloader does not materialize model/runtime state.
- [ ] Concrete construction remains composition-owned.
- [ ] Composition bridges adapt contracts but do not choose product policy.

## Guard/testing

- [ ] Full Python suite green.
- [ ] Architecture guardian green with default-safe outer public-surface enforcement.
- [ ] Adversarial constructor/process/resource/config tests green.
- [ ] Existing HTTP/CLI compatibility tests green.
- [ ] Frontend type/build verification green where available after event/state boundary migration.
- [ ] No TODO/TBD/temporary compatibility bypass remains in this freeze scope.

Once these gates pass, remaining disorder inside core/data/models/training/generation/inference can be treated as **inner-module debt** without reopening the Adapter/Application boundary unless an explicit public contract change is desired.

---

# 13. Recommended implementation order

The order is intentional and must not be rearranged casually:

1. **Wave 1 — inert construction/process ownership** removes the current P0 runtime hazards first.
2. **Wave 2 — gateway/guardian freeze** prevents new outer coupling while later work changes internals.
3. **Wave 3 — canonical transactions** repairs semantic workflow ownership behind the now-stable public surface.
4. **Wave 4 — typed semantic contracts/presentation cleanup** removes the deepest hidden coupling after execution paths are canonical.

Each wave must end with focused tests plus a self-review for:

- new bypass paths;
- duplicated policy;
- changed error/rollback semantics;
- public API expansion;
- hidden transport assumptions;
- resource leaks;
- stale tests that encode old architecture.

Do not begin broad core cleanup until all four wave exit gates pass.
