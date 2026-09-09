# Cross-Boundary Integrity Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate confirmed cross-boundary configuration, checkpoint, lifecycle, race, and state-propagation faults without broad unrelated refactoring.

**Architecture:** Pass resolved config snapshots across request/worker boundaries, centralize inference runtime preferences and checkpoint identity, and add a shared accelerator admission coordinator. Frontend state commits only after authoritative backend success and cross-page scenario/config state is propagated through App-owned state.

**Tech Stack:** Python 3.10+, FastAPI, PyTorch, pytest, React 19, TypeScript, Node test runner.

**Spec:** `docs/superpowers/specs/2026-09-09-cross-boundary-integrity-repair-design.md`

## Global Constraints

- Preserve existing API compatibility where practical.
- No broad performance refactors unrelated to control-plane blocking.
- Every production change must be preceded by a failing regression test.
- Existing canonical path traversal and checkpoint atomic-write protections must remain intact.

---

### Task 1: Freeze training effective config

**Files:** `src/ui/routes/training.py`, `src/ui/services/training_service.py`, `tests/test_ui.py`, `tests/test_training_service.py`

**Interfaces:** Route resolves one `EngineConfig`; `TrainingService.start_training(..., config_snapshot=EngineConfig)` executes a defensive copy. Auto run name is applied after resolution only when `config.training.run_name is None`.

- [ ] Add failing tests proving a worker does not re-read YAML and YAML run_name survives Web Start.
- [ ] Implement snapshot handoff and resolved-config run-name generation.
- [ ] Run focused training/UI tests.

### Task 2: Canonical inference config and immutable checkpoint identity

**Files:** `src/ui/app.py`, `src/ui/services/inference_service.py`, `src/ui/routes/inference.py`, `tests/test_inference_service.py`, `tests/test_ui.py`

**Interfaces:** `InferenceService.from_engine_config(config)`, `apply_engine_config(config)`, active checkpoint revision captured at load, `/api/inference/state`/checkpoint list expose authoritative state and canonical checkpoint filename.

- [ ] Add failing tests for custom checkpoint_name boot/listing and same-path replacement becoming stale/non-active.
- [ ] Implement canonical initialization/reconfiguration and artifact identity.
- [ ] Add config-save runtime preference update and state endpoint.
- [ ] Run focused inference/UI tests.

### Task 3: Canonical generation defaults

**Files:** `src/ui/routes/inference.py`, `src/ui/services/inference_service.py`, frontend Playground config mapping/API, Python/frontend tests.

**Interfaces:** Generation request sampling fields are optional; omitted values inherit canonical `EngineConfig.generation`. Playground hydrates controls from resolved generation config.

- [ ] Add failing Python/frontend tests for YAML generation defaults.
- [ ] Implement backend merge and frontend hydration.
- [ ] Run focused tests.

### Task 4: Explorer/Diagnostics boundary consistency

**Files:** `src/ui/routes/explorer.py`, `src/ui/routes/diagnostics.py`, frontend Explorer/Diagnostics inputs as needed, `tests/test_ui.py`, `tests/test_diagnostics.py`.

**Interfaces:** endpoints accept/resolve the canonical config path and use `EngineConfig.data/model`; Model Inspector returns `model_config` effective values.

- [ ] Add failing tests for custom data/vocab paths, tokenizer identity labeling, and inspector overrides.
- [ ] Implement canonical path/config resolution and metadata fixes.
- [ ] Offload heavy diagnostics/export work with `asyncio.to_thread` where it can block control endpoints.
- [ ] Run focused tests.

### Task 5: Cross-service accelerator admission

**Files:** create `src/ui/services/accelerator_coordinator.py`; modify app/inference/training services and tests.

**Interfaces:** `reserve_training(device)`, `release_training(device)`, `reserve_generation(device)`, `release_generation(device)`. CPU is uncoordinated; same accelerator family is exclusive between training and inference generation.

- [ ] Add failing coordinator and service integration tests.
- [ ] Implement coordinator and wire release paths including generation cancellation/training failure.
- [ ] Run focused lifecycle tests.

### Task 6: Frontend checkpoint authority and VRAM propagation

**Files:** checkpoint hook/widget/types/API, `App.tsx`, `DiagnosticsPage.tsx`, `TrainingPage.tsx`, `useTrainingDashboard.ts`, config mapping/tests.

**Interfaces:** `onCheckpointLoaded` fires only after successful load response; app reconciles active checkpoint from server; VRAM scenario becomes a typed training override payload applied/marked dirty in Training.

- [ ] Add failing pure TypeScript tests for checkpoint success commit helper and scenario-to-form merge.
- [ ] Implement async load ordering/state reconciliation and external training overrides.
- [ ] Run frontend tests/build/lint.

### Task 7: Protect small existing corpora

**Files:** `src/data/pipeline.py`, `tests/test_dataset.py`.

**Interfaces:** any existing regular input file is authoritative regardless of byte size; fallback/download is used only when the file does not exist.

- [ ] Add failing regression test proving a small corpus is not overwritten.
- [ ] Implement existence-first load behavior.
- [ ] Run dataset tests.

### Task 8: Final self-review and closure

- [ ] Search again for canonical hardcodes (`best_model.pt`, fixed data paths, fixed generation defaults) and classify remaining legitimate defaults.
- [ ] Run full Python tests, frontend tests/build/lint, ruff/pyright/architecture gates where available.
- [ ] Review diff for duplicate state, lock ordering, release leaks, compatibility breaks, and config-write partial commits; fix any issues found with regression tests.
- [ ] Produce a clean unified patch against the uploaded baseline.
