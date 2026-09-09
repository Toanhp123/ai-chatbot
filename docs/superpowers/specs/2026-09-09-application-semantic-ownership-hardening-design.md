# Application Semantic Ownership Hardening Design

## Status

Approved follow-up to the 2026-09-09 adapter/application/config boundary refactor.

## Goal

Finish the semantic boundary work that import-direction tests cannot prove: one canonical config authority, one owner for training launch policy, transport-neutral application events, capability modules that expose mechanisms rather than silently selecting fallback policy, and no second runtime-plan authority inside the training engine.

## Invariants

1. `ConfigurationService` is the only canonical active-config authority. Constructing `InferenceService` from an existing `EngineConfig` must never overwrite unrelated config domains.
2. A Web training start is one application use case. The adapter may validate external path trust boundaries, but resume checkpoint pinning, inference-to-training handoff, background admission and config activation belong to application orchestration.
3. Inference residency handoff is reversible. If training admission fails after inference is offloaded, inference runtime is restored when possible.
4. Application emits transport-neutral events. SSE framing/JSON serialization live in `src.ui`.
5. `DataPipeline` performs data mechanics only. Callers must inject cleaner/tokenizer selection and any fallback corpus explicitly; the canonical Application path owns those policy decisions.
6. Gemini capability never silently substitutes a different cleaner. It reports unavailability/failure; application may select an explicit fallback cleaner before invoking the pipeline.
7. `TrainingRunFactory` is the canonical production builder and requires a pre-resolved `ResolvedTrainingPlan`. `Trainer` keeps its legacy standalone fallback for direct capability callers, but application code cannot rely on it.
8. Thin facades are retained only when they protect a real boundary or compatibility surface. Transport/rendering wrappers are moved outward rather than replaced with more application wrappers.
9. Developer-tool process execution and log-file reads are outer adapter I/O; `DiagnosticsApplicationService` must not import `scripts.check_all` or own log-file traversal.

## Design

### Canonical inference preferences

`InferenceService.from_engine_config(config, config_service=...)` passes the full snapshot to the constructor. When a shared `ConfigurationService` exists, inference reads that authority but does not activate or reconstruct it. Standalone inference keeps a private full `EngineConfig` snapshot for compatibility.

### Training launch transaction

`TrainingLaunchApplicationService` accepts a `TrainingCommand` plus an application-level resume checkpoint resolver. It performs:

1. `TrainingApplicationService.plan(command)`.
2. Optional managed resume checkpoint resolution + revision capture.
3. Reversible inference handoff for the resolved device.
4. `TrainingService.start_training(plan=plan, admission_reserved=handoff.training_admission_reserved)`.
5. Active-config commit only after admission succeeds.
6. Handoff rollback on admission failure.

The HTTP adapter only validates that a supplied checkpoint path is inside the configured checkpoint root before handing the path to the application resolver.

### Event transport boundary

`GenerationSession.iter_events()` remains canonical. UI owns an SSE serializer used by `GenerationStreamingResponse`. `TrainingEventHub` owns transport-neutral subscriber buffering and emits structured dict events/heartbeat markers; `TrainingService` owns lifecycle/state and delegates event fan-out to the hub. The route/UI response adapter renders those events as SSE comments/data frames.

### Data source and cleaner policy

Application data-preparation helpers used by `TrainingRunFactory` and Explorer own:

- cleaner selection plus the explicit Gemini-to-standard-cleaner fallback policy;
- tokenizer selection from canonical `DataConfig`;
- optional fallback corpus and whether that fallback may be persisted.

`DataPipeline.setup_data()` requires an injected cleaner plus either a tokenizer or tokenizer factory. `fetch_or_load_text()` accepts only explicit `fallback_text`/`persist_fallback` mechanism inputs and raises `DataPipelineError` when no usable source is available. Cleaning/tokenization failures are never reclassified as source failures.

### Diagnostics outer I/O

`DiagnosticsApplicationService` retains system/model/VRAM diagnostic use cases only. Quality-gate process execution and log-file discovery/tailing live in `src.adapters.diagnostics.DiagnosticsRuntimeAdapter`; the FastAPI composition root wires that adapter for the corresponding developer endpoints. CLI rendering/exit-code behavior remains in `src.adapters.cli`.

### Runtime-plan authority

`TrainingRunFactory.prepare()` requires `ResolvedTrainingPlan` and validates it. This removes the second policy-resolution path inside Application. `Trainer` remains backwards compatible for standalone tests/tools.

### Thin-wrapper cleanup

The one-method `ApplicationRuntimeService` is removed rather than retained as a false Application boundary. CLI/process logging bootstrap calls the outer CLI runtime adapter directly; compatibility shims are kept only where callers still depend on them. A boundary regression test guards against reintroducing the dead runtime wrapper module.

## Verification

- Regression test that `create_app()` preserves the complete YAML config after inference construction.
- Custom `EngineConfig` regression covering model/training/data fields.
- Training launch rollback tests and route delegation tests.
- Generation/training streaming tests proving Application no longer emits SSE strings.
- Data/Gemini policy tests proving failures are explicit and fallback is chosen by Application.
- Focused tests, full pytest suite, architecture guardian, and frontend tests/build where dependencies permit.
