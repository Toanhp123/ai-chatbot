# Adapter / Application / Config Boundary Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate external adapters from capability modules, establish application-owned use-case flows for training/inference/diagnostics/explorer, and make all canonical configuration enter through one shared config contract.

**Architecture:** CLI/FastAPI/YAML are adapters. `src.application` owns orchestration and may call capability modules. Core/capability modules cannot depend upward. `ConfigurationService` is the active/resolved config authority; modules receive snapshots rather than config-source interfaces.

**Tech Stack:** Python 3, dataclasses/protocols, FastAPI, PyTorch, pytest, React 19, TypeScript, Node test runner, Vite.

**Spec:** `docs/superpowers/specs/2026-09-09-adapter-application-config-boundary-design.md`

## Global Constraints

- Preserve existing user-visible HTTP/CLI behavior unless unifying duplicated policy requires one canonical interpretation.
- Core/capability modules must not import application, adapters, or UI.
- Application must not import UI or adapters.
- `EngineConfig.from_yaml()` remains a low-level parser but production external loading goes through the YAML adapter.
- Runtime/effective config transformations use copied snapshots; no nested in-place config mutation.
- Web filesystem trust-boundary validation remains in the HTTP adapter where appropriate.
- Transport-specific rendering must not leak into application services.

---

### Task 1: Establish shared config port and YAML adapter

**Files:**
- `src/application/config/contracts.py`
- `src/application/config/service.py`
- `src/adapters/config/yaml_provider.py`
- `tests/test_application_boundaries.py`
- `tests/test_config.py`

**Produces:** `ConfigRequest`, `ConfigProvider`, `ConfigurationService`, `YamlConfigProvider`, one `DEFAULT_CONFIG_PATH`.

- [x] Write RED tests for provider-default resolution, overrides, active config, and detached snapshot behavior.
- [x] Implement `ConfigurationService.resolve/activate/current/snapshot`.
- [x] Move production `EngineConfig.from_yaml()` usage into `YamlConfigProvider`.
- [x] Make missing adapter config path mean provider default instead of duplicating the literal.
- [x] Verify focused config tests.

### Task 2: Create training application contracts and one run factory

**Files:**
- `src/application/training/contracts.py`
- `src/application/training/service.py`
- `src/application/training/run.py`
- `src/adapters/cli/training_observer.py`
- `tests/test_training_service.py`
- `tests/test_application_boundaries.py`

**Produces:** `TrainingCommand`, `TrainingPlan`, `TrainingObserver`, `PreparedTrainingRun`, `TrainingApplicationService`, `TrainingRunFactory`.

- [x] Write RED tests that adapters can observe training through primitive application events without callback-base imports.
- [x] Move cleaner/data/batch/tokenizer-vocab/model/generator/callback/trainer assembly into `TrainingRunFactory`.
- [x] Make `TrainingApplicationService.plan()` own canonical config resolution, snapshot, runtime resolution, and memory preflight.
- [x] Make `prepare()` return a prepared-run handle instead of exposing concrete `Trainer` to adapters.
- [x] Verify focused training application/service tests.

### Task 3: Separate Web background lifecycle from training assembly

**Files:**
- `src/application/training/background.py`
- `src/application/training/launch.py`
- legacy `src/ui/services/training_service.py` compatibility facade if retained
- `src/ui/routes/training.py`
- `src/ui/app.py`
- `tests/test_training_service.py`
- `tests/test_ui.py`

**Produces:** `TrainingService` for background state/pub-sub and `TrainingLaunchApplicationService` for interactive start coordination.

- [x] Preserve abort/stop/state/metrics/sample/accelerator behavior while removing capability assembly from the background service.
- [x] Keep accelerator admission ordering compatible when a runtime plan is already supplied.
- [x] Pass the already-preflighted `TrainingPlan` from route/application launch into the worker; do not resolve the run twice.
- [x] Commit active canonical config only after the background lifecycle accepts the run.
- [x] Verify Web training focused tests.

### Task 4: Move Inference/checkpoint/generation ownership into application

**Files:**
- `src/application/inference/contracts.py`
- `src/application/inference/service.py`
- `src/application/inference/session.py`
- compatibility modules under `src/ui/services/`
- `src/ui/routes/inference.py`
- `tests/test_inference_service.py`
- `tests/test_checkpoint_contract.py`
- `tests/test_generation*.py`

**Produces:** one checkpoint loader/format interpreter and transport-neutral generation event stream.

- [x] Move inference service implementation out of UI ownership.
- [x] Preserve legacy module imports through delegation/aliasing rather than duplicate implementation.
- [x] Introduce `GenerationCommand`/`GenerationOverrides` and `GenerationSession.iter_events()`.
- [x] Make Web SSE serialize application events instead of application producing SSE.
- [x] Make CLI checkpoint compatibility calls delegate to the same application loader.
- [x] Keep loaded artifact state separate from canonical config preference state.
- [x] Verify inference/checkpoint/generation focused tests.

### Task 5: Remove inference config shadow copies

**Files:**
- `src/application/inference/service.py`
- `tests/test_inference_service.py`
- `tests/test_application_boundaries.py`

**Produces:** compatibility properties derived from canonical config plus explicit transient runtime device override.

- [x] Write RED coverage proving external `ConfigurationService.activate()` is reflected by inference preferences.
- [x] Remove independent mutable storage for checkpoint dir/name, vocab path, and default generation config.
- [x] Keep explicit placement like `cuda:0` as transient `_device_override`, not persisted `SystemConfig.device`.
- [x] Remove route-level manual `apply_engine_config()` synchronization.
- [x] Verify inference/config regression tests.

### Task 6: Move diagnostics and Explorer orchestration into application

**Files:**
- `src/application/diagnostics/service.py`
- `src/application/explorer/service.py`
- `src/ui/routes/diagnostics.py`
- `src/ui/routes/explorer.py`
- `tests/test_diagnostics.py`
- `tests/test_ui.py`

**Produces:** `DiagnosticsApplicationService`, `ExplorerApplicationService`.

- [x] Replace diagnostics DTO-default `EngineConfig` reconstruction with overrides on canonical config.
- [x] Move VRAM/system/model inspection orchestration out of routes.
- [x] Move cleaner/tokenizer/dataset preview/export/comparison orchestration out of Explorer route.
- [x] Make both services read the same `ConfigurationService` lifecycle.
- [x] Verify diagnostics/Explorer focused tests.

### Task 7: Make `create_app()` the single Web composition root

**Files:**
- `src/ui/app.py`
- Web routes under `src/ui/routes/`
- `tests/test_ui.py`
- `tests/test_application_boundaries.py`

**Produces:** one shared application graph stored on `app.state`.

- [x] Construct `YamlConfigProvider -> ConfigurationService` once.
- [x] Construct accelerator, inference, training, launch, diagnostics, and Explorer application services once.
- [x] Change routes to obtain services from `app.state` rather than recreating capability/config objects.
- [x] Keep external path/trust validation in adapters.
- [x] Verify route/application focused tests.

### Task 8: Convert all CLI commands to application use cases

**Files:**
- `main.py`
- `src/adapters/cli/training_observer.py`
- `src/application/runtime/service.py`
- `src/application/diagnostics/service.py`
- `src/application/inference/service.py`
- `tests/test_application_boundaries.py`
- `tests/test_checkpoint_contract.py`

**Produces:** an adapter-only `main.py`.

- [x] Add RED structural coverage forbidding CLI imports/assembly of inner capability modules.
- [x] Route `check/estimate/inspect/gate` through diagnostics application service.
- [x] Route `train` through `TrainingApplicationService` and application observer port.
- [x] Route `generate` through `InferenceService` and `GenerationSession.iter_events()`.
- [x] Make CLI generation/checkpoint/sampling arguments optional overrides of canonical config.
- [x] Make `--config` default `None` so the adapter does not own the default YAML path.
- [x] Route application logging bootstrap through `ApplicationRuntimeService`.
- [x] Verify CLI boundary and checkpoint compatibility tests.

### Task 9: Centralize frontend config semantics

**Files:**
- `frontend/src/**` config/training/playground model code
- `frontend/tests/trainingConfig.test.ts`
- `frontend/tests/generationConfig.test.ts`
- `frontend/tests/vramConfig.test.ts`
- `frontend/tests/checkpointState.test.ts`
- `frontend/tests/explorerConfig.test.ts`

**Produces:** canonical-hydration-first frontend state.

- [x] Remove production frontend copies of the default YAML path.
- [x] Treat omitted/empty config path as provider default.
- [x] Make raw config response provide the authoritative resolved path for the editor.
- [x] Remove fabricated training form defaults before hydration.
- [x] Remove fabricated playground sampling/backend defaults before hydration.
- [x] Preserve dirty-field-only dotted override submission.
- [x] Verify Node frontend unit tests.

### Task 10: Enforce new boundaries in Architecture Guardian

**Files:**
- `scripts/check_architecture.py`
- `tests/test_architecture.py`
- `tests/test_application_boundaries.py`

**Produces:** automated regression protection for layer direction and adapter thinness.

- [x] Add RED synthetic dependency tests for inner-module upward imports and application-to-adapter/UI imports.
- [x] Make dependency rule lookup choose the most-specific source prefix.
- [x] Add source-level assertions for CLI/Web adapter direct capability imports, default config path duplication, and direct YAML config parsing.
- [x] Verify `python -m pytest -q tests/test_architecture.py tests/test_application_boundaries.py`.
- [x] Verify `python scripts/check_architecture.py` reports PASS.

### Task 11: Final regression, documentation, cleanup, and package

**Files:**
- `docs/superpowers/specs/2026-09-09-adapter-application-config-boundary-design.md`
- `docs/superpowers/plans/2026-09-09-adapter-application-config-boundary.md`
- generated/runtime artifacts only for cleanup

**Produces:** verified clean source archive for the completed refactor wave.

- [x] Update the design/spec from the original training-only slice to the actual completed cross-cutting scope.
- [x] Update this plan to record the implemented tasks and final contracts.
- [x] Remove `.cache`, `.pytest_cache`, `__pycache__`, partial `frontend/node_modules`, generated logs/checkpoints, and generated processed training data from the distributable tree without deleting source/sample inputs.
- [x] Run fresh `python -m pytest -q` — 442 passed.
- [x] Run fresh `python scripts/check_architecture.py` — PASS.
- [x] Run fresh frontend `npm test` — 26 passed.
- [x] Attempt `npm run build`; build is environment-blocked because installed dependencies are absent (`vite/client` and `@types/node` cannot be resolved). No build-success claim is made.
- [x] Run final structural scans: no UI/CLI capability imports, no upward application/inner-module imports, production `EngineConfig.from_yaml()` only in `YamlConfigProvider`, one default config literal owner, no route-level `apply_engine_config()`, and no adapter-owned training/checkpoint construction.
- [x] Create the clean ZIP archive and verify its contents do not contain runtime/cache artifacts.
