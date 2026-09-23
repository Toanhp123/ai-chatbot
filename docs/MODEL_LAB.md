# Model Lab

## 1. Product promise and scope

Model Lab provides practical local post-training of compatible open-weight language models on hardware the user controls.

V1 methods:

- supervised fine-tuning (SFT);
- LoRA;
- QLoRA where the selected backend/model/hardware combination actually supports it.

Later methods such as DPO may be added only after dataset lineage, evaluation and worker contracts are mature.

Do not market this as training frontier foundation models from scratch. Backend feature existence does not make that feature a supported product contract.

## 2. Canonical identity model

Do not collapse the training lifecycle into one `jobId`.

- **Dataset** — logical user dataset.
- **DatasetRevision** — immutable normalized dataset snapshot with provenance/content identity.
- **TrainingPlan** — immutable resolved plan that fully defines one intended experiment.
- **TrainingJob** — user-visible logical experiment referencing one TrainingPlan.
- **TrainingAttempt** — one concrete worker execution. Retry/resume always creates a new attempt.
- **TrainingCheckpoint** — resumable state produced by one attempt and valid only under an explicit compatibility contract.
- **ModelArtifactRevision** — immutable adapter/merged/model output with lineage and integrity metadata.
- **EvaluationSuiteRevision** — immutable evaluation inputs/metrics/generation policy.
- **EvaluationRun** — evaluation of one or more concrete model/artifact revisions under one suite revision.

Mutable display names, file paths, backend job IDs and process IDs are metadata, not canonical identity.

## 3. Isolation and control plane

Training/evaluation never runs in Electron renderer/preload/main or ordinary core packages.

Architecture:

- the desktop/application controller validates user intent and persists durable state;
- a dedicated Model Lab service owns the Python training/evaluation environment and backend adapters;
- the controller sends a versioned, resolved, immutable TrainingPlan snapshot;
- the worker emits structured protocol events with attempt identity and sequence;
- outputs live under explicit artifact roots;
- stop/cancel/process cleanup are supported;
- worker/backend crashes cannot crash the desktop UI;
- the worker does not read the product SQLite DB or SecretStore directly;
- backend environments are app-managed/versioned; a job does not silently install arbitrary packages into its environment.

A separate process/environment is an isolation boundary, not automatically a security sandbox. Where OS-level network/filesystem sandboxing is unavailable, surface the degraded enforcement level rather than claiming hard isolation.

## 4. Backend capability resolution

Backends are adapters behind the Model Lab worker protocol. Do not branch product behavior merely on a backend name.

Before a TrainingPlan is launchable, resolve a capability snapshot covering at least:

- model family/architecture compatibility;
- SFT/LoRA/QLoRA support;
- quantization constraints;
- supported optimizer/precision modes;
- maximum sequence/packing constraints where known;
- checkpoint/resume capability;
- adapter export/merge capability;
- supported OS/device types;
- multi-device/distributed support;
- backend/runtime revision.

Unsupported/unknown is not silently coerced into a different method.

Initial candidates:

- NVIDIA/Linux or compatible accelerators: maintained Transformers + PEFT + TRL stacks; a configuration-driven backend such as Axolotl may be used when its supported subset is explicitly validated;
- Apple Silicon: MLX-LM is the preferred initial candidate for supported LoRA/QLoRA flows;
- CPU: small experiments only when technically reasonable, with a clear performance warning.

Do not build a custom training loop merely to expose a knob already handled by a maintained backend.

## 5. Dataset ingestion and lineage

Dataset import is a data pipeline, not a mutable file pointer.

Initial accepted source shapes:

- conversational `messages` JSONL;
- instruction/input/output;
- prompt/completion.

Import creates an immutable DatasetRevision with:

- source kind/path or external source identity;
- source file/content digests;
- canonical schema version;
- stable record IDs;
- record count and validation summary;
- source license/provenance metadata when known;
- transformation lineage.

Supported transformations must be explicit, versioned and reviewable. Record parameters and before/after counts for normalization, filtering, deduplication or format conversion. Never silently rewrite the user's original source file.

Training data content is always data, never an instruction source for the host agent or Prompt Runtime.

## 6. Dataset validation, split and preparation

Detect/report at minimum:

- malformed records/encoding;
- empty or unsupported roles/content;
- unsupported multimodal references;
- exact duplicates and feasible near-duplicate signals;
- extreme sequence outliers;
- obvious secret patterns;
- split overlap/leakage signals;
- missing/unknown provenance or license metadata.

Show useful statistics such as record count, role distribution, length distribution, duplicate rate, split sizes and estimated training tokens.

Split rules:

- split assignment is reproducible and part of the DatasetRevision/TrainingPlan lineage;
- stable record IDs, seed/strategy and resulting membership are persisted;
- exact record overlap across train/validation/test blocks launch until resolved;
- near-duplicate leakage is surfaced with evidence and explicit user resolution;
- a test split, when present, is not supplied to the training/early-stopping loop and is reserved for final evaluation.

Backend-specific preparation is a derived snapshot/cache, not a mutation of DatasetRevision. Its fingerprint includes at least:

- DatasetRevision and split identity;
- tokenizer revision;
- chat template revision/digest;
- max sequence/truncation policy;
- packing policy;
- loss-mask policy such as assistant-only/completion-only;
- preparation implementation/version.

Changing any of those values creates a new prepared-data fingerprint and normally a new TrainingPlan.

## 7. Immutable TrainingPlan

A launchable TrainingPlan contains a resolved snapshot of at least:

- plan schema/version and digest;
- base model source + immutable revision/digest;
- tokenizer/chat-template identity;
- DatasetRevision + split/prepared-data fingerprint;
- backend profile/environment revision + capability snapshot;
- method: SFT/LoRA/QLoRA;
- adapter target modules/rank/alpha/dropout where applicable;
- quantization configuration where applicable;
- loss policy;
- batch/micro-batch/gradient accumulation;
- learning rate, optimizer, scheduler;
- epochs/steps and evaluation/save cadence;
- max sequence length/packing;
- seed and requested determinism mode;
- device/resource selection;
- checkpoint/retention policy;
- output/artifact root;
- network/external-tracking policy.

The worker may reject a plan as unsupported, but it must not silently change semantic training parameters after launch.

If a calibration/autotune step changes batch size, precision, sequence length or another semantic parameter, it produces a new resolved TrainingPlan for user review before the real attempt.

## 8. Environment and reproducibility snapshot

Each TrainingAttempt records the actual environment used:

- worker protocol revision;
- Python/runtime revision;
- backend/library revisions;
- CUDA/ROCm/Metal/MLX stack revision as applicable;
- OS/architecture;
- device identities and available memory snapshot;
- driver/runtime versions where available;
- relevant determinism flags;
- effective seed(s).

Do not promise bit-for-bit reproducibility across different hardware/software. Distinguish:

- **replayable configuration** — enough provenance exists to recreate the intended plan;
- **deterministic mode requested** — deterministic backend settings were requested;
- **determinism verified/limited** — backend reports whether known nondeterministic operations remain.

A seed alone is never presented as proof of reproducibility.

## 9. Resource planning and leases

Before launch, estimate at least:

- model/download footprint if not already staged;
- expected output/checkpoint disk growth;
- RAM/VRAM/unified-memory fit;
- selected device set;
- likely runtime class/duration warning where feasible.

Estimates are advisory unless a hard constraint is known. Clearly impossible disk/device requirements must block launch.

V1 uses an app-owned **training resource lease**:

- one app-managed TrainingAttempt owns an exact accelerator/device set at a time;
- a distributed/multi-device attempt owns the full declared set as one lease;
- overlapping app-managed attempts are rejected/queued rather than racing into OOM;
- external processes using the same GPU may be detected/warned about but are never killed merely to make room.

Training resource leases are scheduling, not permission or security grants.

## 10. Worker protocol

The controller ↔ worker protocol is versioned and structured. Stdout/stderr are diagnostics, never the only state channel.

Minimum lifecycle:

1. worker hello/protocol + backend capability handshake;
2. controller assigns `trainingAttemptId`, TrainingPlan digest, local artifact roots and resource lease;
3. worker validates all referenced immutable inputs before compute;
4. worker emits monotonic attempt-scoped events/metrics;
5. controller may send cancel/status commands;
6. worker emits one terminal result: completed, failed, cancelled, interrupted or `unknown_outcome`;
7. controller validates/finalizes produced artifacts before registration.

Protocol messages never contain Python objects or arbitrary executable payloads. Every event includes attempt identity, event sequence and worker/backend revision.

The worker must not infer permission to access unrelated filesystem roots, credentials, network services or app state merely because a TrainingPlan exists.

## 11. Network, secrets and experiment tracking

The compute phase is local/offline by default.

- stage/download remote base-model/dataset artifacts before launching compute when possible;
- external experiment trackers are disabled unless explicitly configured by the user;
- do not inherit arbitrary cloud/provider/API tokens from the desktop process environment;
- never upload datasets, prompts, checkpoints, metrics or model artifacts implicitly;
- backend defaults such as “report to all installed integrations” must be overridden by the product's explicit tracking policy;
- publishing/push-to-hub is a separate explicit product action, not a training side effect.

If an explicit workflow needs network access, record destination/purpose and apply normal network/privacy policy. If the platform cannot technically enforce offline execution, label the restriction as configuration/best-effort rather than claiming a hard sandbox.

## 12. TrainingAttempt lifecycle, retry and cancellation

Typical attempt states:

`queued → preparing → running → finalizing → completed`

Terminal alternatives include `failed`, `cancelled`, `interrupted`, and `unknown_outcome` where external reality cannot be reconciled safely.

Rules:

- worker/process launch creates a concrete TrainingAttempt;
- retry creates a new attempt linked to the prior attempt;
- resume creates a new attempt with `resumeFromCheckpointId`;
- OOM/backend crash does not silently reduce batch/sequence/precision and continue under the same plan;
- cancellation first requests graceful stop, then terminates the exact owned process tree after a bounded timeout if necessary;
- a cancelled attempt remains cancelled even if it produced a valid checkpoint;
- app restart never assumes a training process completed merely because its PID disappeared;
- reattach is allowed only through an explicit authenticated/versioned worker-reconnect protocol; otherwise reconcile exact app-owned process identity, mark the attempt interrupted, and require an explicit new resume attempt.

## 13. Resume compatibility

A TrainingCheckpoint is resumable only when its manifest says it contains the backend state required for resume and the controller validates a compatibility fingerprint.

For full trainer-state resume, this commonly includes model/adapter state plus optimizer, scheduler, RNG, gradient-scaler and data-position/sampler state as applicable.

Resume compatibility covers at least:

- TrainingPlan identity or explicitly permitted compatible fields;
- base model revision;
- DatasetRevision/prepared-data fingerprint;
- tokenizer/template;
- method/adapter shape/quantization;
- backend/environment compatibility;
- world/device topology requirements where the backend imposes them.

An adapter-only artifact is not mislabeled as a full resumable checkpoint.

Changing training semantics after a checkpoint produces a new TrainingPlan/job lineage rather than pretending to be a transparent resume.

## 14. Checkpoint and artifact finalization

Distinguish:

- **resumable checkpoint** — internal training state;
- **adapter artifact** — inference/shareable PEFT output referencing its exact base model;
- **merged model artifact** — new derived model revision produced by an explicit merge/export step;
- **evaluation artifact** — metrics/output pairs/reports;
- **raw diagnostic log** — bounded support evidence, not a model artifact.

Checkpoint/artifact rules:

- write into a staging/temp location;
- finalize only after all required files are present and validated;
- create manifest + checksums/integrity metadata;
- incomplete/partial artifacts are never offered for resume/promotion;
- never overwrite the base model in place;
- a merge creates a new ModelArtifactRevision and estimates additional disk before execution;
- prefer data-oriented safe tensor formats such as safetensors when the backend supports them;
- retention cannot delete a checkpoint/artifact still referenced by an active resume, evaluation, promotion or export.

## 15. Evaluation contracts

Training completion is not model promotion.

Initial evaluation supports:

- validation loss/metrics from the backend;
- deterministic or bounded user-defined prompt suites;
- task-specific exact/structured metrics;
- side-by-side base vs candidate outputs;
- held-out test evaluation when a test split exists.

EvaluationSuiteRevision pins:

- input cases/dataset revision;
- metric/evaluator implementation revisions;
- tokenizer/template as relevant;
- generation parameters;
- seed/determinism settings where meaningful.

Base and candidate comparisons use the same applicable evaluation configuration. Evaluation results retain raw per-case references plus aggregate metrics; do not reduce model quality to one universal score.

If model-as-judge is added later, store judge provider/model revision, prompt/rubric, generation settings and judge output provenance. A judge score is attributed evidence, not ground truth.

## 16. Promotion and Local Models registration

A completed attempt yields a **candidate**, not an automatically registered Local Model or loaded runtime model.

Before promotion/registration:

- validate artifact manifest and file integrity;
- verify base-model dependency for adapters;
- perform a load/smoke inference check when supported;
- attach TrainingPlan/DatasetRevision/EvaluationRun lineage;
- surface base/dataset license/provenance metadata and unknowns;
- ensure no partial/unsafe artifact is being registered;
- require explicit action for merge/export/publish operations with material disk/network consequences.

Promotion creates/updates Local Models registry metadata by immutable artifact revision. Every successful registration appends an immutable **Model Promotion Record** binding the promoted ModelArtifactRevision, resulting Local Model/revision, EvaluationRun/TrainingPlan/DatasetRevision evidence, actor/source and timestamp. If a user-facing alias moves, record before/after alias references rather than overwriting promotion history. Re-promoting the same artifact creates another auditable record; it does not mutate the original decision.

Promotion does not silently replace an existing model alias or delete source/base artifacts.

Generate a local provenance/model-card style summary containing at least base model, datasets/revisions, method/config summary, evaluation references, environment, license metadata and known limitations.

## 17. Metrics, logs and retention

Structured events include at least:

- environment preparing;
- inputs validated;
- model loading;
- dataset preprocessing;
- training started;
- step/epoch;
- train/validation loss;
- learning rate/throughput;
- memory stats when available;
- checkpoint started/finalized/failed;
- evaluation started/result;
- cancellation requested;
- terminal state.

High-frequency metrics may be sampled/coalesced for durable DB storage. Raw worker logs are bounded/rotated and redacted. Never make raw logs the only machine-readable status source or copy private training examples into diagnostics by default.

## 18. Backend-specific notes

- TRL supports standard/conversational language-model and prompt-completion datasets; loss masking/template behavior must therefore be explicit in TrainingPlan rather than inferred later.
- PEFT/QLoRA capabilities vary by architecture/quantization backend; adapter target configuration is pinned in the plan and output adapter references the exact base-model revision.
- MLX-LM supports LoRA/QLoRA and resume/export flows for supported Apple Silicon models; these remain backend capabilities, not universal promises.
- Generic checkpoint APIs often require optimizer/RNG/scaler and related trainer state for exact resume; adapter weights alone are insufficient.

Use backend version/capability probes and contract tests rather than copying upstream defaults into product semantics.

## 19. Security/privacy invariants

- datasets/artifacts remain local by default;
- dataset/model content is untrusted data and never gains host instruction authority;
- no arbitrary per-job package installation; model/tokenizer repository custom code is disabled by default and, if a supported explicit high-risk path later enables it, the source/revision is pinned and execution remains inside the isolated Model Lab/local-runtime boundary rather than Electron/core;
- unsafe model serialization/custom code follows `LOCAL_AI.md`/`SECURITY.md` and stays outside Electron host processes;
- output roots are canonicalized/validated and cannot escape allowed artifact roots through traversal/symlink tricks;
- disk pressure/retention is explicit;
- deletion distinguishes registry metadata from underlying files;
- cancellation/process cleanup acts only on exact app-owned worker/process identity;
- user data is not sent to cloud trackers or model hubs without an explicit action.

## 20. Phase 8 acceptance shape

A credible Phase 8 E2E flow is:

import immutable dataset revision → validate/dedupe/split → select immutable base model → resolve backend capability + resource plan → freeze TrainingPlan → acquire device lease → launch one TrainingAttempt → stream structured metrics → finalize resumable checkpoint and/or adapter artifact → run pinned base-vs-candidate evaluation → validate provenance/integrity → explicitly register candidate in Local Models.

The deterministic CI path uses a fake/tiny worker and artifacts; real GPU smokes supplement but do not replace the protocol/lineage tests.
