# Core Runtime Contract Hardening Design

## Goal

Make `src/core` the single semantic source of truth for configuration validity, effective training runtime, memory estimation, diagnostics state, logging context, and structured errors so backend and frontend cannot observe a different runtime than the trainer executes.

## Scope

### Wave 1

1. Make config construction/copy/update paths validate invariants and normalize malformed YAML/config input to `ConfigurationError`.
2. Introduce one `ResolvedTrainingPlan` describing effective device, precision, optimizer, micro/effective batch sizes, gradient checkpointing, and fallback reasons.
3. Make VRAM estimation architecture-aware and consume the same resolved runtime plan as the trainer.
4. Represent diagnostic probes as explicit `OK` / `UNSUPPORTED` / `FAILED` states instead of silently turning failures into zero/false values.
5. Validate raw YAML semantically before save and persist it atomically.

### Wave 2

1. Remove eager package barrel imports and import-time filesystem/logging side effects from `src.core`.
2. Make logging context task/thread-safe and ensure handlers actually receive context fields.
3. Wire `SystemConfig.log_level` and `SystemConfig.log_file` into runtime logger configuration.
4. Preserve `AIEngineError` structure across FastAPI and the frontend API client.
5. Add architecture guards for pure config/exception imports and import-time side effects.
6. Surface metric persistence failures instead of silently pretending they succeeded.

## Architecture

### Validated configuration

Configuration dataclasses remain mutable for compatibility, but every public construction boundary validates. `BaseConfig.copy()` validates the replacement before returning it. `EngineConfig.from_dict()` rejects non-mapping domains and translates type/value failures to `ConfigurationError`. Code that mutates an existing config for a temporary derived request must validate before execution.

### Effective runtime plan

`src/core/runtime.py` owns:

- `RuntimeCapabilities`
- `ResolvedTrainingPlan`
- `detect_runtime_capabilities()`
- `resolve_training_plan()`

The plan records requested and effective device/precision/optimizer plus fallbacks. Gradient accumulation does not shrink the configured `batch_size`; `micro_batch_size == training.batch_size` and `effective_batch_size == batch_size * gradient_accumulation_steps`.

Trainer and diagnostics both consume this plan. Optimizer creation receives the resolved optimizer instead of performing an independent hidden fallback.

### Model memory profile

`src/core/diagnostics/estimator.py` calculates parameter counts by architecture contract:

- MiniGPT: learned positional embedding + GELU MLP.
- LLaMA: no learned positional embedding + RMSNorm + SwiGLU, including `intermediate_size`, `multiple_of`, and bias/tied-weight settings.

The estimator accepts a `ResolvedTrainingPlan`; when only configs are supplied it resolves one using current runtime capabilities. The returned payload exposes requested/effective runtime fields and fallback reasons.

### Probe result contract

`src/core/diagnostics/probe.py` defines a generic serializable `ProbeResult` with `status`, `value`, and optional `error`. Hardware/storage functions keep their existing top-level payload keys where possible, but include probe metadata and use `None` when a value is unknown. Diagnostics runner only emits capacity warnings for successful probes.

### Logging and imports

`src/core/__init__.py` becomes lazy via module `__getattr__`; importing `src.core.config` or `src.core.exceptions` must not import Torch/Rich or create log files. `LogContext` uses `contextvars.ContextVar`. The context filter is attached to every managed handler, not only the root logger.

### HTTP error contract

FastAPI registers one `AIEngineError` exception handler that returns the full `to_dict()` payload with an appropriate status code. Routes should allow `AIEngineError` to reach that handler instead of stringifying it. Frontend `ApiErrorPayload` mirrors structured fields while retaining `detail`/`message` compatibility.

### Config persistence

Raw config save performs YAML parse, `EngineConfig.from_dict()` semantic validation, then writes through a temporary file in the destination directory and `os.replace()`.

## Compatibility

- Existing public config class names and core diagnostic functions remain available.
- Existing consumers of numeric diagnostic values continue to work for successful probes.
- Existing `setup_logger`, `get_logger`, and optimizer factory entry points remain available.
- Existing API error clients may still read `message`; new clients gain structured fields.
- No model/training package is imported by `src.core.config` or `src.core.exceptions`.

## Verification

1. Focused TDD tests for config validation, runtime resolution, architecture-aware parameter counts, gradient accumulation semantics, probe failures, logging propagation, semantic/atomic config saves, and structured API errors.
2. Full Python test suite.
3. Ruff/pyright where available.
4. Frontend TypeScript build.
5. Import purity subprocess test proving config import does not load `torch`/`rich` or create a log file.
