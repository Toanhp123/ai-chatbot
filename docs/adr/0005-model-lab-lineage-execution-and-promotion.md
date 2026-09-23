# ADR-0005 — Model Lab lineage, execution, and promotion contract

- Status: accepted
- Date: 2026-09-24
- Class: FROZEN change / cross-cutting security and lifecycle
- Supersedes: none
- Superseded by: none

## Context

D-011 already isolates Model Lab from Electron, but the previous contract still allowed materially different implementations of dataset identity, retry/resume, checkpoint semantics, external tracking and model registration. Those differences affect privacy, reproducibility, storage, recovery and user expectations.

Current training frameworks also separate adapter artifacts from full trainer-state checkpoints, can apply backend/template defaults during preprocessing, and may integrate external experiment trackers. A stable product needs its own normalized lifecycle above those backend behaviors.

## Decision

1. **Immutable lineage.** DatasetRevision, TrainingPlan, TrainingAttempt, TrainingCheckpoint, ModelArtifactRevision and EvaluationSuiteRevision/EvaluationRun are distinct identities. Mutable paths/names/process IDs are never the only identity.
2. **Plan before execute.** Dataset split/preparation, base model revision, tokenizer/template, backend/environment revision, training semantics, device selection, checkpoint policy and network/tracking policy are resolved into an immutable TrainingPlan before compute.
3. **Attempt safety.** Retry/resume always creates a new TrainingAttempt. Backends do not silently mutate semantic parameters after launch to recover from OOM/failure.
4. **Resume is explicit.** A checkpoint is resumable only when required trainer state and a compatibility manifest are present; an adapter artifact alone is not advertised as full resume state.
5. **Local compute by default.** External experiment tracking/upload is disabled unless explicitly configured; remote inputs are staged before compute when practical. The worker does not inherit arbitrary desktop secrets.
6. **Resource ownership.** One app-managed training attempt owns its declared accelerator set at a time in V1; overlapping internal attempts do not race for the same devices.
7. **Artifact finalization.** Checkpoints/artifacts are staged then finalized with manifests/integrity metadata. Partial output is not resumable/promotable; base artifacts are never overwritten in place.
8. **Evaluation precedes promotion.** Training completion creates a candidate. Local Models registration/promotion is a separate explicit step with artifact validation, lineage, evaluation references and license/provenance metadata.
9. **No hidden instruction/code authority.** Dataset/model bytes remain untrusted data. Per-job arbitrary package/custom repository code cannot execute inside Electron/core processes.

## Consequences

- Model Lab requires more explicit durable entities than a single `training_jobs` row.
- Backend adapters must translate a normalized plan and report actual environment/capability facts.
- Resume/export behavior may be more conservative than raw backend CLI capabilities.
- Privacy defaults are predictable even when training libraries have optional cloud integrations installed.
- Experiments remain explainable after crashes, retries, backend upgrades and artifact promotion.

## Alternatives considered

- **Persist only backend config/log directory.** Rejected: insufficient lineage and recovery semantics.
- **Treat retries/resumes as the same job execution.** Rejected: obscures which process produced which checkpoint/artifact.
- **Let each backend define dataset/checkpoint semantics directly in UI.** Rejected: creates parallel product contracts and makes migration/comparison fragile.
- **Auto-register the final checkpoint as a local model.** Rejected: conflates trainer state, inference artifact and evaluated candidate.

## Fitness / verification

Contract/integration tests must prove at least:

- mutable source changes create a different DatasetRevision/plan rather than silently reusing identity;
- retries/resumes create new attempts and preserve parent/checkpoint lineage;
- incompatible/partial checkpoints cannot resume;
- worker protocol never requires DB/SecretStore access or Python-object transport;
- external tracking/upload is off by default;
- overlapping app-managed device leases are rejected/queued;
- partial artifact directories cannot be promoted;
- base/candidate evaluation pins the same suite configuration;
- training completion alone does not register/activate a Local Model.

## Revisit trigger

Revisit if Phase 8 implementation evidence shows that a required supported backend cannot fit the normalized plan/attempt/checkpoint contract without losing a critical capability, or if distributed/remote training becomes a deliberate product scope rather than local post-training.
