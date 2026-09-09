# Cross-Boundary Integrity Repair Design

## Goal

Repair only faults that can break end-to-end state/config propagation across frontend, API, services, runtime, artifacts, and persistence. Localized performance/logic issues remain out of scope unless they can block the control plane or destroy user data.

## Invariants

1. A training run executes the exact `EngineConfig` snapshot that was preflighted by `/api/training/start`; the worker never re-reads a mutable YAML file for that run.
2. `training.run_name` is auto-generated only when the resolved effective config has no run name.
3. Inference boots and reconfigures from the canonical `EngineConfig` fields for checkpoint directory/name, vocab, device, and generation defaults.
4. Checkpoint active identity includes immutable file identity captured when the model was loaded. Replacing the same pathname on disk must make the new file non-active until explicitly loaded.
5. Frontend checkpoint success state commits only after the backend load request succeeds, and initial UI state is reconciled from backend checkpoint metadata.
6. Explorer and diagnostics resolve the same canonical config/data paths as training; request labels must describe the tokenizer/model actually executed.
7. YAML `generation` values hydrate Playground defaults and are used by backend generation when request fields are omitted.
8. Applying a VRAM scenario updates Training form overrides, rather than only local Diagnostics state.
9. Training and generation share one accelerator admission coordinator so GPU/MPS training cannot overlap accelerator generation.
10. Model Inspector returns effective override metadata.
11. Heavy synchronous diagnostics/export work is offloaded from the event loop where it can block lifecycle endpoints.
12. An existing input corpus is never overwritten merely because it is small; empty files are read and then rejected by normal dataset validation rather than replaced silently.

## Architecture

Introduce a small UI-layer `AcceleratorCoordinator` shared by `TrainingService` and `InferenceService`. Keep `EngineConfig` as the canonical config type and pass immutable per-run copies into training. `InferenceService` owns canonical runtime preferences plus a loaded checkpoint fingerprint based on stable file metadata/hash; disk listings compare that identity rather than pathname alone.

Config-save validates first, atomically persists, then updates runtime preferences that are safe to change without mutating an already loaded model. UI pages consume resolved config endpoints instead of hard-coded paths/defaults. Cross-page frontend changes flow through `App` state so Diagnostics VRAM choices become dirty training overrides.

## Error handling

Admission conflicts fail before launching work. Failed checkpoint loads leave both backend and frontend active state unchanged. Runtime reconfiguration never silently changes an already loaded model/device; changed preferences apply to future loads/runs and are observable through API state.

## Verification

Add regression tests for each invariant, verify red before implementation, then run focused suites, full Python tests, frontend tests/build/lint, architecture checks, and a final diff/self-review for duplicate state sources and hard-coded canonical names.
