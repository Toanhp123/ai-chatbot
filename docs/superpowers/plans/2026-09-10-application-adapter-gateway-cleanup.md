# Application and Adapter Gateway Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make Adapters and Application a clean, stable gateway so remaining structural debt is isolated to inner/core capability modules.

**Architecture:** Application owns commands, results, orchestration and ports. Adapters own transport/conversion/I/O. Concrete synchronization/runtime implementations move inward and are wired in one composition root.

**Tech Stack:** Python 3, FastAPI, PyYAML, pytest, TypeScript/Vite frontend verification when dependencies are present.

**Spec:** `docs/superpowers/specs/2026-09-10-application-adapter-gateway-cleanup-design.md`

## Global Constraints

- Preserve HTTP payload shapes and CLI command behavior.
- No deep algorithm optimization or model/trainer redesign.
- Tests first for every boundary/behavior change.
- Application public APIs must not expose capability runtime classes.
- Concrete assembly occurs only in `src/composition`.

---

### Task 1: Architecture ratchet tests for the target boundary

**Files:**
- Modify: `tests/test_application_boundaries.py`
- Modify: `tests/test_architecture.py`

**Produces:** failing tests that enforce adapter purity, Application concrete-runtime isolation, no runtime re-exports, a single composition root, and typed FastAPI gateway state.

- [x] Add tests scanning Adapter imports for all inner module prefixes.
- [x] Add tests scanning Application for forbidden concrete-runtime imports/construction and capability re-exports.
- [x] Add tests requiring `ApplicationServices` and `request.app.state.services` routing.
- [x] Run focused tests and verify RED failures are caused by current architecture.

### Task 2: Configuration port cleanup

**Files:**
- Modify: `src/application/config/contracts.py`
- Modify: `src/application/config/service.py`
- Modify: `src/adapters/config/yaml_provider.py`
- Test: `tests/test_application_boundaries.py`, `tests/test_config.py`, `tests/test_ui.py`

**Interfaces:**
- `ConfigDocumentProvider.load_mapping(source) -> Mapping[str, object]`
- `ConfigDocumentProvider.parse_mapping(content) -> Mapping[str, object]`
- `ConfigDocumentProvider.write_raw(content, source) -> str`

- [x] Write/adjust tests proving YAML adapter has no `src.core` imports and ConfigurationService owns override/default/validation semantics.
- [x] Verify RED.
- [x] Implement mapping/codec/I/O-only YAML provider and move EngineConfig/override policy into ConfigurationService.
- [x] Run focused config/UI tests GREEN.

### Task 3: Application-owned ports and public contracts

**Files:**
- Create: `src/application/runtime/contracts.py`
- Modify: `src/application/inference/contracts.py`
- Modify: `src/application/training/contracts.py`
- Modify: public `__init__.py` files.

**Produces:** structural Protocols for accelerator, admission, inference runtime/stream, background task/event runtime, training runtime/control/observer and checkpoint resolver.

- [x] Add boundary tests asserting no capability type re-exports.
- [x] Verify RED.
- [x] Add Protocol contracts and remove capability imports/re-exports from Application public modules.
- [x] Run focused boundary tests GREEN.

### Task 4: Move accelerator and generation-admission mechanics inward

**Files:**
- Create: `src/core/accelerator.py`
- Create: `src/inference/admission.py`
- Modify: `src/application/runtime/__init__.py`
- Remove production use of: `src/application/runtime/accelerator.py`, `src/application/inference/generation_admission.py`
- Test: `tests/test_accelerator_coordinator.py`, `tests/test_generation_admission.py`

- [x] Migrate tests to capability/core ownership and add Application scan assertions.
- [x] Verify RED before production moves.
- [x] Move implementations inward unchanged where possible.
- [x] Run accelerator/admission tests GREEN.

### Task 5: Inference Application service becomes pure orchestration

**Files:**
- Modify: `src/application/inference/service.py`
- Modify: `src/application/inference/preferences.py` only as needed
- Modify: `src/inference/api.py` / runtime only for structural port compatibility if necessary
- Test: `tests/test_inference_service.py`, `tests/test_application_boundaries.py`

**Interfaces:** `InferenceService(runtime, admission, accelerator, config_service, initial_config)`; returns Application `GenerationStream` protocol.

- [x] Add tests constructing service with fakes and asserting no model/tokenizer/generator/runtime-lock public surface.
- [x] Verify RED.
- [x] Remove concrete runtime construction/import and compatibility artifact properties.
- [x] Keep checkpoint/list/generation/training-handoff behavior by delegating through ports.
- [x] Run inference tests GREEN.

### Task 6: Training Application isolates capability mechanics

**Files:**
- Modify: `src/application/training/service.py`
- Modify: `src/application/training/background.py`
- Modify: `src/application/training/launch.py`
- Test: `tests/test_training_service.py`, `tests/test_application_boundaries.py`

**Interfaces:** injected `TrainingRuntimePort`, `BackgroundExecutionPort`, `TrainingEventPort`, `AcceleratorPort`, `ResumeCheckpointResolver`.

- [x] Add tests proving Application imports no concrete training runtime/execution/event classes and launch accepts no adapter callback.
- [x] Verify RED.
- [x] Inject ports and map capability outputs to Application-owned contracts/private state.
- [x] Remove `resume_path_resolver` argument; use injected resolver.
- [x] Run training tests GREEN.

### Task 7: Single composition root and typed ApplicationServices

**Files:**
- Create: `src/application/services.py`
- Create: `src/composition/__init__.py`
- Create: `src/composition/root.py`
- Create: filesystem resume adapter if needed under `src/adapters/filesystem/`
- Modify: `src/ui/app.py`
- Modify: `main.py`

- [x] Add tests for one composition root and one app-state gateway.
- [x] Verify RED.
- [x] Build all concrete dependencies in composition root.
- [x] Replace service construction in UI/CLI with composed `ApplicationServices`.
- [x] Run CLI/UI/application tests GREEN.

### Task 8: HTTP adapter simplification

**Files:**
- Modify: `src/ui/routes/inference.py`
- Modify: `src/ui/routes/training.py`
- Modify: diagnostics/explorer routes as required.
- Test: `tests/test_ui.py`, `tests/test_ui_errors.py`

- [x] Add/adjust tests to use single gateway state.
- [x] Verify RED.
- [x] Route all use cases through `request.app.state.services` and remove callback/service-locator leakage.
- [x] Run UI tests GREEN.

### Task 9: Adversarial self-review and architecture ratchet

**Files:**
- Modify: `scripts/check_architecture.py`
- Modify: `tests/test_architecture.py`, `tests/test_application_boundaries.py`

- [x] Scan imports, signatures, `__all__`, constructors, locks/threads/events, and `app.state` usage for loopholes.
- [x] Add failing regression tests for every discovered loophole.
- [x] Fix each violation without moving use-case policy outward.
- [x] Run focused architecture tests GREEN.

### Self-review addendum: semantic gateway leakage

- [x] Add `ConfigGateway` and `LoggingSettings` so outer layers never receive `EngineConfig`.
- [x] Hide `ConfigurationService` from the public config package surface.
- [x] Ratchet Architecture Guardian against direct UI/Adapter imports of Application implementation modules while preserving `*.contracts` for port implementations.
- [x] Verify baseline and modified frontend builds fail identically only because the provided workspace lacks `vite/client` and `node` type definitions.

### Task 10: Final verification and clean patch

- [x] Run `python -m pytest -q` and require all tests pass.
- [x] Run project architecture/quality gate commands available in the repository.
- [x] Run frontend build if dependencies are installed; otherwise record the unchanged baseline dependency blocker.
- [x] Generate a unified patch from pristine uploaded source to final tree.
- [x] Inspect patch for unrelated files, generated artifacts, caches, or accidental core-algorithm changes.
