# Application Semantic Ownership Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Eliminate the remaining semantic-boundary leaks after the adapter/application/config refactor while preserving external behavior and compatibility paths.

**Architecture:** `ConfigurationService` stays the sole active-config authority; top-level Application use cases own cross-capability policy and transactions; capabilities expose mechanisms/domain algorithms; adapters own transport serialization and external trust-boundary validation.

**Tech Stack:** Python 3, dataclasses/protocols, FastAPI, PyTorch, pytest, React/TypeScript frontend unchanged except regression verification.

**Spec:** `docs/superpowers/specs/2026-09-09-application-semantic-ownership-hardening-design.md`

## Global Constraints

- Preserve public HTTP/CLI payload semantics.
- Do not add reverse imports from capability/core modules to Application/UI/adapters.
- Write a failing regression test before each production behavior change.
- Keep compatibility shims unless their removal is independently proven safe.
- Do not move domain algorithms into Application.

---

### Task 1: Fix canonical config authority corruption

**Files:**
- Modify: `tests/test_inference_service.py`, `tests/test_ui.py`
- Modify: `src/application/inference/service.py`

**Interfaces:**
- Consumes: `InferenceService.from_engine_config(config, config_service=...)`
- Produces: inference initialization that never overwrites an already-active shared config.

- [x] Add a regression test that constructing inference with shared `ConfigurationService` preserves a custom full `EngineConfig` snapshot.
- [x] Run the focused test and confirm RED on unrelated model/training/data fields.
- [x] Make inference initialization retain/pass the full snapshot and stop activating reconstructed config during construction.
- [x] Run focused inference/UI config tests GREEN.

### Task 2: Make streaming transport-neutral

**Files:**
- Modify: `tests/test_generation_hardening.py`, `tests/test_training_service.py`, `tests/test_ui.py`
- Modify: `src/application/inference/session.py`, `src/application/inference/service.py`, `src/application/training/background.py`
- Modify/Create: `src/ui/responses.py`
- Modify: `src/ui/routes/training.py`

**Interfaces:**
- Produces: `GenerationSession.iter_events()` and `TrainingService.iter_events()` structured event iterators; UI SSE serializer.

- [x] Add RED tests forbidding/avoiding Application `iter_sse()` and string-SSE training streams.
- [x] Implement UI-side SSE serialization for generation and training events/heartbeats.
- [x] Remove Application JSON/SSE framing and update compatibility streaming facade to serialize outside Application.
- [x] Run generation/training/UI focused tests GREEN.

### Task 3: Centralize training launch and make handoff reversible

**Files:**
- Modify: `tests/test_application_boundaries.py`, `tests/test_ui.py`, `tests/test_inference_service.py`
- Modify: `src/application/training/launch.py`, `src/application/inference/service.py`
- Modify: `src/ui/routes/training.py`

**Interfaces:**
- Produces: application-owned launch transaction and an inference handoff token/rollback operation.

- [x] Add RED tests that failed background admission restores inference residency and does not activate config.
- [x] Add RED route test that resume checkpoint revision assembly is delegated to Application launch orchestration.
- [x] Implement reversible inference handoff and application-level resume checkpoint pinning.
- [x] Keep adapter path-root validation only; remove orchestration mutation from the route.
- [x] Run focused training/inference/UI tests GREEN.

### Task 4: Pull fallback policy out of capabilities and lock runtime-plan authority

**Files:**
- Modify: `tests/test_dataset.py`, `tests/test_preprocessors.py`, `tests/test_training_service.py`
- Modify: `src/data/pipeline.py`, `src/data/cleaners/gemini.py`
- Modify: `src/application/training/run.py`

**Interfaces:**
- Produces: explicit data fallback controls; Gemini capability raises instead of silently replacing itself; canonical `TrainingRunFactory` requires a resolved plan.

- [x] Add RED data-source test for disabled fallback on remote failure.
- [x] Add RED Gemini test for missing key/SDK/API failure being explicit.
- [x] Add RED `TrainingRunFactory` test requiring `runtime_plan` and proving application-selected fallback cleaner behavior.
- [x] Implement minimal mechanism controls and application policy selection.
- [x] Run dataset/preprocessor/training focused tests GREEN.

### Task 5: Self-review, boundary cleanup and final verification

**Files:**
- Review: `src/application/**`, `src/data/**`, `src/training/**`, `src/ui/**`
- Update: this plan/spec only if implementation contracts differ materially.

- [x] Search for remaining Application SSE/JSON transport rendering, duplicate config activation, Application runtime-plan resolution inside run factory, route-level training-plan mutation, silent capability fallback, and direct capability-to-Application imports.
- [x] Fix any contradictions/regressions found with RED tests first.
- [x] Run focused architecture tests.
- [x] Run full `python -m pytest -q`.
- [x] Run `python scripts/check_architecture.py`.
- [x] Check frontend verification availability: archive has no `frontend/node_modules`, so `npm test`/`npm run build` are not runnable in this environment; no frontend source files are changed by this patch.
- [x] Remove generated caches/artifacts and produce a clean patch against the untouched baseline.
