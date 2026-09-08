# Core Runtime Contract Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make core configuration, effective runtime, memory estimation, diagnostics, logging, and error propagation agree end-to-end from backend to frontend.

**Architecture:** Add a single resolved runtime plan consumed by trainer and estimator, make model memory estimation architecture-aware, and replace ambiguous diagnostic fallbacks with explicit probe states. Then harden package import purity, logging propagation, semantic config persistence, and structured API errors without changing the modular-monolith dependency direction.

**Tech Stack:** Python 3.10+, dataclasses, PyTorch, FastAPI/Pydantic, pytest, React 19 + TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-08-core-runtime-contract-hardening-design.md`

## Global Constraints

- `src.core.config` and `src.core.exceptions` must stay independent of `src.models`, `src.training`, `src.ui`, and import-time Torch/Rich/filesystem effects.
- Configured `training.batch_size` is the runtime micro-batch size; effective batch is `batch_size * gradient_accumulation_steps`.
- Effective runtime fallbacks must be explicit and shared by trainer and estimator.
- Existing public entry points remain backward compatible unless an old behavior is demonstrably unsafe.
- All new failure boundaries normalize domain failures to existing `AIEngineError` subclasses.

---

### Task 1: Validated configuration boundaries and safe persistence

**Files:**
- Modify: `src/core/config/base.py`
- Modify: `src/core/config/engine.py`
- Modify: `src/ui/routes/inference.py`
- Test: `tests/test_config.py`
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: `ConfigurationError`, `EngineConfig.from_dict()`.
- Produces: validated `BaseConfig.copy()`, robust `EngineConfig.from_dict()`, semantic atomic config save.

- [ ] **Step 1: Write failing tests** covering `copy()` validation, non-mapping domains, malformed scalar field types, semantic raw-config rejection, and successful atomic replacement.
- [ ] **Step 2: Run focused tests and verify they fail for the intended contract gaps.**
- [ ] **Step 3: Implement validation normalization** so `copy()` validates replacements and `EngineConfig.from_dict()` converts malformed mapping/type failures into `ConfigurationError` with domain/field context.
- [ ] **Step 4: Implement semantic atomic save** using `yaml.safe_load()`, `EngineConfig.from_dict()`, `tempfile.NamedTemporaryFile(delete=False, dir=destination)`, `flush()`, `os.fsync()`, and `os.replace()` with cleanup on failure.
- [ ] **Step 5: Run focused config/UI tests and verify green.**

### Task 2: Single effective runtime plan

**Files:**
- Create: `src/core/runtime.py`
- Modify: `src/training/trainer.py`
- Modify: `src/training/optimizers.py`
- Test: `tests/test_diagnostics.py`
- Test: `tests/test_optimizers.py`
- Test: `tests/test_smoke_train.py`

**Interfaces:**
- Produces: `RuntimeCapabilities`, `ResolvedTrainingPlan`, `detect_runtime_capabilities()`, `resolve_training_plan(engine_config, capabilities=None, device_override=None)`.
- `ResolvedTrainingPlan.micro_batch_size` equals configured batch size.
- `ResolvedTrainingPlan.effective_batch_size` equals `micro_batch_size * gradient_accumulation_steps`.
- Optimizer factory accepts optional `optimizer_type` override selected by the plan.

- [ ] **Step 1: Write failing resolver tests** for CPU/CUDA/MPS selection, unsupported precision fallback, unavailable `bitsandbytes` fallback, and accumulation semantics.
- [ ] **Step 2: Run focused tests and confirm failures.**
- [ ] **Step 3: Implement pure plan dataclasses plus capability detection** and deterministic fallback rules.
- [ ] **Step 4: Integrate Trainer and optimizer factory** so the trainer uses plan device/precision/optimizer instead of independently resolving/falling back.
- [ ] **Step 5: Run optimizer/trainer tests and verify green.**

### Task 3: Architecture-aware memory estimation

**Files:**
- Modify: `src/core/diagnostics/estimator.py`
- Modify: `src/ui/routes/diagnostics.py`
- Test: `tests/test_diagnostics.py`
- Test: `tests/test_ui.py`

**Interfaces:**
- Produces: `calculate_model_params(model_config)`, plan-aware `estimate_vram_budget(..., runtime_plan=None)`.
- Keeps `calculate_approx_transformer_params()` for MiniGPT/backward compatibility.

- [ ] **Step 1: Write failing tests** comparing estimator parameter counts to instantiated MiniGPT/LLaMA models including custom LLaMA `intermediate_size`, and assert accumulation no longer divides micro-batch.
- [ ] **Step 2: Run focused tests and verify failures.**
- [ ] **Step 3: Implement MiniGPT/LLaMA parameter profiles** including biases, tying, RMSNorm, SwiGLU rounding, and no LLaMA positional embedding.
- [ ] **Step 4: Make estimator consume the runtime plan** and expose requested/effective runtime metadata/fallback reasons; update diagnostics route to validate configs then use the plan once.
- [ ] **Step 5: Run diagnostics/UI tests and verify green.**

### Task 4: Explicit diagnostic probe states

**Files:**
- Create: `src/core/diagnostics/probe.py`
- Modify: `src/core/diagnostics/hardware.py`
- Modify: `src/core/diagnostics/storage.py`
- Modify: `src/core/diagnostics/runner.py`
- Modify: `src/core/diagnostics/__init__.py`
- Modify: `frontend/src/entities/hardware/model/types.ts`
- Test: `tests/test_diagnostics.py`

**Interfaces:**
- Produces: `ProbeStatus`, `ProbeResult[T]` and `probe` metadata on diagnostic payloads.
- Failed numeric probes use `None`, not fake zero.

- [ ] **Step 1: Write failing tests** that monkeypatch psutil/shutil/backend probes to fail and assert `FAILED` status, nullable values, and no false low-disk/low-RAM warning.
- [ ] **Step 2: Run focused tests and confirm failures.**
- [ ] **Step 3: Implement probe contract and collector changes** while preserving successful payload shapes.
- [ ] **Step 4: Make runner status logic probe-aware** and update frontend hardware types for nullable measurements/probe metadata.
- [ ] **Step 5: Run diagnostics tests and frontend type build.**

### Task 5: Core import purity and logging correctness

**Files:**
- Modify: `src/core/__init__.py`
- Modify: `src/core/logging.py`
- Modify: `main.py`
- Modify: `src/ui/services/training_service.py`
- Test: `tests/test_logging.py`
- Test: `tests/test_architecture.py`

**Interfaces:**
- `src.core` uses lazy exports.
- `LogContext` is context-local.
- Managed handlers carry `LogContextFilter`.
- `setup_logger()` can be configured from `EngineConfig.system` before runtime work starts.
- Metric persistence errors become observable via logging/exception instead of being silently swallowed.

- [ ] **Step 1: Write failing tests** for subprocess import purity, child logger JSON context propagation, context isolation, configured log path/level, and metric persistence failure visibility.
- [ ] **Step 2: Run focused tests and confirm failures.**
- [ ] **Step 3: Replace eager core barrel with lazy exports** and remove module-level diagnostics logger initialization.
- [ ] **Step 4: Replace global dict context with `ContextVar` and attach filters to handlers.**
- [ ] **Step 5: Wire system logging config into CLI/UI training composition roots and make metric persistence failures explicit.**
- [ ] **Step 6: Run logging/architecture tests and verify green.**

### Task 6: Structured HTTP errors and frontend contract

**Files:**
- Modify: `src/ui/app.py`
- Modify: affected routes under `src/ui/routes/`
- Modify: `frontend/src/shared/api/base.ts`
- Test: `tests/test_ui.py`
- Test: `tests/test_exceptions.py`

**Interfaces:**
- FastAPI returns `AIEngineError.to_dict()` JSON for domain failures.
- Frontend `ApiErrorPayload` exposes `error_code`, `severity`, `is_recoverable`, `details`, `suggestion`, and `cause` while retaining legacy `detail/message/status`.

- [ ] **Step 1: Write failing API tests** proving `ConfigurationError` and another domain error retain structured fields through FastAPI.
- [ ] **Step 2: Run focused tests and confirm failures.**
- [ ] **Step 3: Register central `AIEngineError` handler** with deterministic status mapping and stop stringifying domain errors in touched routes.
- [ ] **Step 4: Extend frontend API error type/message selection** without breaking legacy payloads.
- [ ] **Step 5: Run UI/exception tests and frontend build.**

### Task 7: Cross-wave self-review and verification

**Files:**
- Modify only files required by findings discovered during review.
- Test: full `tests/` suite and frontend build.

**Interfaces:**
- Produces: no new public API unless required to close a confirmed contradiction.

- [ ] **Step 1: Audit dependency direction, duplicated runtime resolution, mutable invalid config paths, silent exception swallowing, import-time side effects, and stale frontend types.**
- [ ] **Step 2: Add a regression test for every confirmed gap before fixing it.**
- [ ] **Step 3: Fix confirmed gaps with the smallest architecture-consistent change.**
- [ ] **Step 4: Run `python -m pytest -q`, `python -m ruff check .`, `python -m pyright`, and `npm run build` in `frontend/` where tools are installed.**
- [ ] **Step 5: Generate a clean unified patch against the untouched extracted baseline and verify the patch applies cleanly to a fresh extraction.**
