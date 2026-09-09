# Adapter / Application / Config Boundary Refactor Design

## Status

Implemented architecture baseline for the 2026-09-09 structural-flow refactor wave.

## Goal

Make external adapters thin and stable, centralize use-case orchestration in an application layer, keep core/capability modules focused on their own implementations, and make canonical configuration enter all application flows through one shared configuration contract.

This is a structural refactor. Runtime behavior and HTTP/CLI contracts are preserved except where duplicated behavior had to be unified under one authoritative implementation.

## Final dependency direction

```text
External world
    |
    v
Adapters / composition roots
  - CLI parsing + terminal I/O
  - FastAPI routes + HTTP/SSE mapping
  - YAML/file config I/O
    |
    v
Application
  - configuration lifecycle
  - training plan/run/launch/background lifecycle
  - inference/checkpoint/generation sessions
  - diagnostics/explorer use cases
  - runtime/accelerator coordination
    |
    v
Core + capability modules
  core / data / models / training / generation / utils
```

Reverse imports are forbidden:

- `src.core`, `src.data`, `src.models`, `src.training`, `src.generation`, and `src.utils` must not import `src.application`, `src.adapters`, or `src.ui`.
- `src.application` must not import `src.ui` or `src.adapters`.
- FastAPI routes and CLI entry points must call application services instead of assembling capability modules directly.

## Adapter rule

Adapters may:

- parse CLI/HTTP input,
- enforce transport and external filesystem trust-boundary checks,
- translate application results into console/HTTP/SSE output,
- construct concrete application ports at a composition root,
- own transport-specific lifecycle objects such as FastAPI request/response types.

Adapters may not:

- call `EngineConfig.from_yaml()` directly,
- resolve training runtime policy,
- build cleaner/tokenizer/data/model/generator/trainer graphs,
- interpret checkpoint formats,
- reconstruct domain config from diagnostics DTO defaults,
- own generation-sampling policy,
- maintain a second default config path.

`src.ui.app.create_app()` is the Web composition root. `main.py` is the CLI adapter/composition root. `src.adapters.config.YamlConfigProvider` is the external config-source adapter.

## Application rule

Application owns complete use-case orchestration. It may depend on core and concrete capability modules in this modular-monolith phase, but it must not depend on FastAPI, React, CLI parsing, `src.ui`, or `src.adapters`.

Application services introduced by this wave:

```text
src/application/
  config/
    contracts.py
    service.py
  training/
    contracts.py
    service.py
    run.py
    background.py
    launch.py
  inference/
    contracts.py
    service.py
    session.py
  diagnostics/
    service.py
  explorer/
    service.py
  runtime/
    accelerator.py
    service.py
  errors.py
```

Each service has one semantic owner. Adapters may translate inputs/outputs, but must not reproduce the use-case rules inside those services.

## Shared configuration authority

`EngineConfig` remains the canonical domain schema. External acquisition and active-config lifecycle are owned by the application config port.

```text
ConfigRequest(path?, dotted overrides)
        |
        v
ConfigProvider                 application port
        |
        +-- YamlConfigProvider external adapter
        +-- in-memory/static provider in tests
        |
        v
ConfigurationService
  - resolve()
  - activate()
  - current()
  - snapshot()
        |
        v
EngineConfig snapshot
```

### Config invariants

- `src.application.config.contracts.DEFAULT_CONFIG_PATH` is the one production owner of the default config path.
- `EngineConfig.from_yaml()` is called by production code only inside `YamlConfigProvider`.
- `None`/empty config source at adapter boundaries means "use the provider default"; adapters do not duplicate the path string.
- Application services receive a `ConfigurationService` or an already-resolved `EngineConfig` snapshot.
- Low-level capability modules do not receive `ConfigProvider` and do not know YAML paths.
- Requested/effective transformations create copied config objects rather than mutating nested config in place.
- A started training run uses the `TrainingPlan` snapshot that was already preflighted.

## Web composition root

`src.ui.app.create_app()` constructs one shared graph:

```text
YamlConfigProvider
      |
ConfigurationService
      |
      +--> InferenceService
      +--> TrainingApplicationService
      |      |
      |      +--> TrainingService (background lifecycle)
      |              |
      |              +--> TrainingLaunchApplicationService
      +--> DiagnosticsApplicationService
      +--> ExplorerApplicationService
      +--> AcceleratorCoordinator
```

Routes obtain these services from `app.state`; routes do not recreate the graph.

## Training flow

Training has one authoritative assembly path for CLI and Web.

```text
CLI / HTTP
   |
TrainingCommand
   |
TrainingApplicationService.plan()
   - resolve canonical config
   - snapshot requested config
   - run-name policy
   - runtime-plan resolution
   - memory preflight
   |
TrainingPlan
   |
TrainingApplicationService.prepare()
   |
TrainingRunFactory
   - quick-check copy
   - seed
   - cleaner
   - DataPipeline
   - BatchProvider
   - tokenizer vocab propagation through config copy
   - ModelRegistry
   - runtime validation
   - GeneratorRegistry
   - callback bridge/common callbacks
   - Trainer
   |
PreparedTrainingRun
   |
execute()
```

### Web-specific training lifecycle

`TrainingService` owns background thread/state/pub-sub/abort behavior. It does not own training graph construction.

`TrainingLaunchApplicationService` coordinates the interactive/Web start transaction:

```text
prepare inference for target device
        -> background service accepts run
        -> canonical config becomes active
```

The active config is not committed before the background lifecycle accepts the run.

## Inference and checkpoint flow

`InferenceService` is an application service and is the canonical owner of checkpoint interpretation/loading for both Web and CLI.

CLI checkpoint compatibility entry points delegate to this application implementation rather than maintaining a second loader.

Generation is transport neutral:

```text
GenerationCommand + GenerationOverrides
        |
InferenceService.begin_generation_command()
        |
GenerationSession.iter_events()
        |
        +--> CLI terminal renderer
        +--> Web SSE serializer
```

Sampling defaults come from canonical `EngineConfig.generation`. CLI flags and Web request values are optional overrides; omission means inherit canonical config.

### Inference preference state

Checkpoint directory/name, vocab path, system device preference, and default generation config derive from the shared canonical config snapshot rather than independent mutable shadow fields.

Explicit runtime placement such as `cuda:0` is treated as transient runtime state because it is not a persisted `SystemConfig.device` value.

Loaded model/tokenizer/checkpoint identity/device residency remain runtime state and are intentionally separate from configuration preference state.

## Diagnostics flow

Diagnostics no longer reconstructs a separate `EngineConfig` from transport DTO defaults.

```text
HTTP/CLI request
   -> optional canonical dotted/domain overrides
   -> DiagnosticsApplicationService
   -> ConfigurationService current/resolved snapshot
   -> VRAM/system/model inspection capability
   -> application result
   -> adapter rendering
```

VRAM scenario responses carry canonical override semantics back to the UI, avoiding a second interpretation of training configuration in React.

## Explorer flow

`ExplorerApplicationService` owns cleaner/tokenizer/dataset-preview/export/comparison orchestration. The HTTP route only validates request transport values and maps application results.

Explorer reads the same canonical active configuration lifecycle as the other application services.

## CLI flow

`main.py` is an adapter. Its responsibilities are argparse, terminal I/O, process exit behavior, and construction of the YAML config adapter/application services.

Commands delegate as follows:

```text
check/estimate/inspect/gate -> DiagnosticsApplicationService
train                       -> TrainingApplicationService
                              + ConsoleTrainingObserver adapter
generate                    -> InferenceService + GenerationSession.iter_events
ui                          -> application runtime logging + uvicorn launch
```

`main.py` must not import or instantiate `Trainer`, `DataPipeline`, model/generator registries, core runtime resolvers, or use `torch.load` to interpret checkpoints.

## Frontend config contract

React is not a config authority.

- No production frontend literal for the backend default YAML path.
- Training and generation forms begin unhydrated (`null`/loading), not with fabricated Python/YAML-like defaults.
- Canonical backend config hydrates visible form state.
- Only explicitly dirty fields become canonical dotted overrides.
- The config editor requests the default source without guessing its path and displays the authoritative path returned by the backend.
- Playground generation controls inherit canonical generation config unless the user changes them.

## Compatibility shims

Legacy import paths under `src.ui.services` may remain temporarily as module aliases/facades so existing external imports/tests can transition without restoring upward dependencies.

Compatibility facades must delegate to application owners; they may not reintroduce duplicated implementation logic.

## Architecture enforcement

`scripts/check_architecture.py` and `tests/test_architecture.py` enforce:

- inner modules cannot import application/adapters/UI,
- application cannot import UI/adapters,
- source rules use the most-specific matching prefix,
- Web adapter routes/services cannot import capability-module assembly details,
- CLI does not assemble capability modules directly,
- production config loading is centralized behind the YAML config adapter.

`tests/test_application_boundaries.py` additionally protects the structural rules that are easier to express as source assertions.

## Deliberate non-goals

This wave does not:

- redesign the internal algorithms of `Trainer`, models, tokenizers, generators, or VRAM estimators,
- introduce separate deployable services or dependency-injection frameworks,
- move capability algorithms into application merely to satisfy layering,
- eliminate all compatibility facades immediately,
- require every physical code change to touch only one file.

The target is one authoritative implementation per semantic decision, not a single giant file.

## Success criteria

1. CLI and Web training use one training application assembly path.
2. HTTP/CLI adapters do not construct training/data/model/generation capability graphs.
3. Web routes obtain use-case services from one composition root.
4. Checkpoint interpretation/loading has one application owner used by CLI and Web.
5. Generation events are transport neutral and adapters only render them.
6. Diagnostics and Explorer orchestration live in application services.
7. Production config acquisition goes through `ConfigProvider -> ConfigurationService`.
8. The default config path has one production owner.
9. Frontend contains no fabricated canonical defaults before hydration.
10. Inference config preferences do not require mutable shadow copies or route-level synchronization.
11. Architecture tests/guardian prevent upward dependency regression.
12. Full backend tests, architecture guardian, and frontend unit tests pass before packaging.
