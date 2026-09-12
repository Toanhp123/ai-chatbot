---
title: "AI-Train / My-AI V2 — Architecture Baseline & Functional Graph"
status: "FROZEN"
revision: "R1"
date: "2026-09-10"
scope: "Product architecture, capability graph, ownership, process boundaries, persistence boundaries, execution semantics"
freeze_point: "Q120"
---

# AI-Train / My-AI V2 — Architecture Baseline & Functional Graph R1

## 1. Purpose

This document is the architecture baseline for the clean-slate V2 backend of AI-Train / My-AI.

V2 is **not** another refactor pass over the existing `src/` tree. It is a new backend architecture derived from the product's functional graph and the 120 product invariants locked during architecture discovery.

The old codebase is treated as **architecture archaeology** only.

It may be used to recover:

- real product behaviors worth preserving;
- valid edge cases and tests;
- proven algorithms/mechanics;
- artifact/data formats that remain valuable.

It must **not** define the new:

- module topology;
- class hierarchy;
- service/facade graph;
- dependency structure;
- compatibility surface;
- application architecture.

The existing frontend remains the presentation layer and will consume V2 through explicit generated/local API contracts.

---

## 2. North Star

AI-Train / My-AI V2 is a:

> **Single-user, local-only AI Studio with Generation as the central capability.**

Generation must work independently from Training.

A Generation target may originate from:

```text
Remote Provider
      │
      ├── Remote Model
      │
      └──────────────┐
                     │
Imported Local Model │
      │              │
      └──────────────┼──> GenerationTarget ──> Generation
                     │
Training Output      │
      │              │
      └──────────────┘
```

Training is a first-class capability but is never a prerequisite for Generation.

---

## 3. Functional Graph

### 3.1 Product-level graph

```text
                           ┌─────────────────────────┐
                           │      APPLICATION HOST   │
                           │ start / supervise / stop│
                           └────────────┬────────────┘
                                        │
                               Composition Root
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          │                             │                             │
          ▼                             ▼                             ▼
     API / Contracts               Platform                     App Bootstrap
          │                             │
          │                  ┌──────────┼───────────┐
          │                  │          │           │
          │               SQLite   ArtifactStore SecretStore
          │                  │          │           │
          │                  ├── Operations / Events
          │                  ├── Worker Supervision
          │                  ├── Observability
          │                  ├── Resource Lease
          │                  └── Migration Coordination
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRODUCT CAPABILITIES                            │
└─────────────────────────────────────────────────────────────────────────┘

                             GENERATION
                                 │
          ┌──────────────────────┼───────────────────────┐
          │                      │                       │
          ▼                      ▼                       ▼
    Conversation          GenerationPreset       Evaluation
          │                      │                       │
          └──────────────────────┼───────────────────────┘
                                 │
                                 ▼
                       GenerationRequest
                                 │
                       Capability Negotiation
                                 │
                          Frozen Intent
                                 │
                          Resource Plan
                                 │
                     ┌───────────┴────────────┐
                     │                        │
                     ▼                        ▼
             Remote Generation        Local Generation
                     │                        │
             Provider Driver           Runtime Driver
                     │                        │
             ProviderProfile          RuntimeEnvironment
                     │                        │
                SecretStore              Model Lease
                                              │
                                         Model Registry
                                              │
                                  Acquisition / Training
```

### 3.2 Dataset graph

```text
Dataset
 ├── Import
 ├── Inspect
 ├── Transform
 ├── Version
 ├── Split
 ├── Artifact
 ├── Training
 ├── Evaluation
 └── Knowledge ingestion
```

### 3.3 Model graph

```text
Models
 ├── Acquisition
 │    ├── Download
 │    └── Import
 ├── Integrity / Trust
 ├── Registry
 ├── Compatibility
 ├── Publication
 ├── GenerationTarget
 └── Runtime / Residency
```

### 3.4 Training graph

```text
Training
 ├── TrainingSpec
 ├── DatasetVersionRef
 ├── ModelArchitectureRef
 ├── TokenizerArtifactRef
 ├── ResolvedPlan
 ├── TrainingRun
 ├── ExecutionAttempt
 ├── Checkpoints
 └── Published Model Artifact
```

### 3.5 Runtime/resource graph

```text
SystemCapabilities
 ├── CPU
 ├── RAM
 ├── GPU
 ├── VRAM
 ├── Precision Support
 ├── Runtime Availability
 └── Backend Features
        │
        ▼
ResourcePlanner
        │
        ▼
ResolvedPlan
        │
        ▼
ResourceLease
        │
        ▼
Worker / Runtime
```

### 3.6 Future graph

```text
Knowledge / Retrieval
        │
        ▼
Prepared Context ──┐
                   │
Tools ─────────────┼──> Agent ──> Generation
                   │
Conversation ──────┘

Evaluation
    └── GenerationTargets + Dataset/EvaluationSet

Backup / Restore
    └── DB + Artifact Manifest + Integrity + Recovery
```

---

# 4. Major Capability Ownership

## 4.1 Generation

Generation owns:

```text
GenerationRequest
→ semantic validation
→ target resolution
→ capability negotiation
→ effective parameter resolution
→ frozen semantic execution intent
→ admission/resource planning
→ ExecutionAttempt
→ streaming/events
→ canonical GenerationOutcome
```

Generation does **not** own:

```text
conversation persistence
retrieval/vector search
tool policy
agent loop
provider secret storage
model downloading
model registry
training
UI decisions
```

## 4.2 Conversation

Conversation is above Generation and owns conversation identity, messages, metadata, context policy, summaries, default target reference and construction of GenerationRequest.

Conversation is not the Generation engine.

## 4.3 Models

```text
Models
├── Model Acquisition
│   ├── discover
│   ├── download
│   ├── import
│   └── verify materialization
│
├── Local Model Registry
│   ├── identity
│   ├── metadata
│   ├── format
│   ├── architecture
│   ├── tokenizer reference
│   ├── integrity
│   └── compatibility
│
├── Compatibility Resolution
│
├── Publication
│   └── Model → GenerationTarget
│
└── Runtime Residency
    ├── load
    ├── reuse
    ├── lease
    ├── evict
    └── unload
```

## 4.4 Dataset

Dataset is an independent capability owning identity, source, import, inspection, transformation, versioning, splitting and dataset artifacts.

Consumers may include Training, Evaluation, Knowledge/RAG, fine-tuning and synthetic-data workflows.

## 4.5 Training

Training owns TrainingSpec, TrainingRun, ResolvedPlan, resource admission, worker execution, progress, ExecutionAttempt, checkpoint semantics, recovery/resume, training outputs and optional publication requests.

Training output does not automatically become a GenerationTarget.

## 4.6 Tokenizer

Tokenizer is an identifiable artifact/capability, not a global hidden runtime singleton.

```text
TokenizerArtifact
├── id
├── kind
├── version
├── vocabulary metadata
├── encode/decode capability
├── artifact reference
└── compatibility metadata
```

## 4.7 Evaluation

Evaluation remains independent from Training.

```text
Evaluation
├── EvaluationSet / Dataset
├── GenerationTargets
├── EvaluationSpec
├── Execution
├── Metrics
└── EvaluationResult
```

Training may consume Evaluation. Evaluation does not depend on Training.

## 4.8 Knowledge / Retrieval

Future capability:

```text
Documents / Dataset / Notes / Repo
              │
              ▼
       Knowledge Ingestion
              │
              ▼
       Knowledge Artifact
              │
              ▼
          Retrieval
              │
              ▼
        Context Artifact
              │
              ▼
     Conversation / Generation
```

Generation must not query the vector store directly.

## 4.9 Tools

Tools own tool identity, input/output schema, permissions/policy and execution contract.

Models must never receive arbitrary Python/shell/filesystem execution outside tool policy.

## 4.10 Agents

Agents own goals, state, iteration loop, tool selection, Generation calls and termination policy.

Agent != Generation.

---

# 5. Platform Boundary

`platform/` exists only for mechanics that are genuinely cross-domain.

```text
platform/
├── persistence/
├── artifacts/
├── secrets/
├── operations/
├── events/
├── resources/
├── workers/
├── observability/
├── migrations/
├── filesystem/
└── backup mechanics/
```

`platform/` must not become the new `core/`.

Avoid dumping-ground packages such as `core/`, `common/`, `utils/`, `helpers/`, `services/` or `managers/` unless the contents have one clear architectural owner and responsibility.

---

# 6. Dependency Direction

```text
Frontend
   │
   ▼
API
   │
   ▼
Capability Entry Point / Application Use Case
   │
   ├───────────────┐
   ▼               ▼
Capability A    Capability B
   │               │
   └──── explicit contracts
           │
           ▼
      Platform ports
           │
           ▼
       Adapters
```

Forbidden directions include:

```text
Adapter → business policy
Capability A → internals of Capability B
Domain → FastAPI
Domain → ORM
Domain → Provider SDK
Worker → business DB
Frontend → DB
Frontend → raw filesystem path
API route → persistence internals
```

The graph must remain a DAG both statically and at runtime orchestration level.

---

# 7. Product Invariants #1–#120

## Group A — Product and Capability Foundations

### #1 — Generation-centric local AI studio
Generation is the central capability. Training is independent and optional for Generation.

### #2 — General Generation Runtime
GenerationRequest must support extensibility for prompt/messages, target, parameters, streaming, cancellation, metadata/context and future tools/RAG/multimodal semantics.

### #3 — Conversation != Generation
Conversation builds GenerationRequest. Direct Generation remains usable independently.

### #4 — Local-only forever
No User, Account, Tenant, RBAC, ACL, multi-user ownership or cloud-server abstractions.

### #5 — Hybrid persistence with hard ownership
DB is source of truth for domain state and metadata. Filesystem holds large artifacts. Runtime state is ephemeral. No dual source of truth.

### #6 — GenerationTarget abstraction
Remote models, local models and published/training-derived models converge through GenerationTarget while preserving their own domains.

### #7 — Strict capability negotiation
Unsupported requested semantics produce typed failure unless an explicit safe fallback policy was accepted.

### #8 — SecretStore
Secrets are distinct from config and provider metadata. Drivers resolve secrets through SecretStore only.

### #9 — Training is first-class but independent
Training may grow into a Training Studio but cannot become a Generation prerequisite.

### #10 — Dataset is an independent domain
Dataset supports Training, Evaluation, RAG, fine-tuning, synthetic data and other workflows.

## Group B — Configuration, Planning and Contracts

### #11 — Settings != Spec != RuntimeDecision
Avoid global EngineConfig/AppConfig god objects. Settings, immutable operation intent and resolved runtime decision are separate concepts.

### #12 — Planning != Execution
SystemCapabilities → ResourcePlanner → ResolvedPlan → ExecutionRuntime.

### #13 — Shared lifecycle primitives, domain operation types
Share lifecycle primitives only. Keep TrainingRun, GenerationSession/Operation, DatasetImport and ModelDownload as distinct concepts.

### #14 — Typed failures by domain + common API envelope
Internal failures map to typed domain failures. API serializes business semantics only.

### #15 — HTTP command/query + domain event stream
HTTP handles commands/queries. Realtime updates use a domain event stream, preferring SSE where sufficient.

### #16 — Frontend presentation ownership
Frontend owns presentation workflow and UI state. Backend owns business truth and execution semantics.

### #17 — Conversation owns semantic history/context; Generation owns execution
Conversation manages conversational semantics and builds normalized requests.

### #18 — LocalModelRegistry is model truth
Filesystem is only storage/discovery/import source. Registry owns canonical local model identity and metadata.

### #19 — Tokenizer identity != runtime instance
TokenizerArtifact is an identifiable artifact/capability referenced by Dataset, Training and Models.

### #20 — Stable driver contracts, built-ins first
Remote provider and local runtime extensibility occurs through stable driver contracts. Plugin frameworks are deferred until justified.

## Group C — Capability Boundaries and Orchestration

### #21 — SystemCapabilities is factual truth; Diagnostics is a consumer
Hardware/runtime truth belongs to SystemCapabilities. Diagnostics may inspect/report but does not redefine it.

### #22 — Evaluation is independent
Evaluation can benchmark GenerationTargets and may be consumed by Training without depending on Training.

### #23 — Knowledge/Retrieval is a separate capability
Retrieval prepares context artifacts upstream. Generation consumes normalized context.

### #24 — Tools and Agents are independent capabilities
Tool execution and agent loops remain outside Generation.

### #25 — Global resources + optional/default Project
Providers, Secrets, Models, Targets, Tokenizers, SystemCapabilities and App Settings are global. Conversations, Datasets, Knowledge, TrainingRuns and Evaluations can be project-scoped. A default Project avoids forced workspace UX.

### #26 — ArtifactStore owns mechanics; domain owns semantics
ArtifactStore provides allocation, atomic commit, integrity, reads, deletion mechanics and reconciliation. Domains define meaning.

### #27 — Minimal deterministic bootstrap
Bootstrap initializes lightweight foundations only. Heavy model loading, scanning, benchmarks and runtime probes remain lazy.

### #28 — Persistence ports follow capability/use-case intent
No GenericRepository[T], BaseRepository, CRUDService or RepositoryManager.

### #29 — Capability dependency graph is a DAG
No dependency cycles. Cross-capability interaction occurs through explicit contracts.

### #30 — Application layer exists only for real orchestration/policy
Avoid 1:1 forwarding services and facade chains.

## Group D — Legacy, Models, Runtime and API Evolution

### #31 — Delete CLI/console product surface
CLI-only product flow, renderers, observers, configuration and debug flow do not return in V2.

### #32 — Delete debug/explorer internals; redesign product inspection
Keep only real product-facing Playground, Dataset Inspection, Model Inspection and System Inspection.

### #33 — Model architecture semantics are invariant; legacy implementations are replaceable
Old MiniGPT/LLaMA/attention/RoPE class hierarchies are not sacred.

### #34 — Checkpoint/resume is a Training contract
Checkpoint resumes Training. Checkpoint is not a published GenerationTarget.

### #35 — ModelArtifactFormat != LocalRuntimeDriver
Artifact format and execution engine are separate concerns.

### #36 — ModelAcquisition != LocalModelRegistry
Downloaded/imported artifact != registered model != published GenerationTarget.

### #37 — Shared cache mechanics, domain-specific policy
Share mechanics only. Generation KV cache, dataset cache, runtime residency and acquisition cache each retain domain policy.

### #38 — Structured observability is cross-cutting
Domain does not depend on logger implementation. Domain events, logs, metrics and traces are separate concepts.

### #39 — Hybrid API semantics
Use resource-oriented reads and explicit command/use-case endpoints for state transitions.

### #40 — Version contracts/artifacts/migrations independently
Do not preserve compatibility forever. Persisted state receives explicit migrations.

## Group E — Host, Workers and Resources

### #41 — Backend is loopback-only
Bind only local loopback interfaces.

### #42 — Application Host owns backend lifecycle
Host starts, waits for READY, supervises, shuts down and launches frontend as needed.

### #43 — Lightweight coordinator + heavy worker subprocesses
Coordinator owns API/persistence/orchestration/planning. Heavy local runtime work may execute in subprocess workers.

### #44 — Resource contention is planner-based
Interactive generation receives admission priority, but existing workloads are not implicitly preempted.

### #45 — Shared scheduling primitives, no global generic job queue
Share priority/resource admission primitives while domains retain their own lifecycle semantics.

### #46 — Persistent operation records + domain recovery
Runtime disappears on crash; durable operation truth remains. Stale RUNNING operations become interrupted/recovered according to domain policy.

### #47 — Versioned artifact contract + explicit migration/import
Runtime consumes current-compatible artifacts only.

### #48 — Architecture rules are executable
CI/tests enforce boundaries, contracts, typing, migrations, artifact compatibility and recovery semantics.

### #49 — Old src is archaeology evidence
Reuse behavior and proven mechanics selectively. Do not port topology, wrappers, compatibility abstractions or old dependency graph.

### #50 — Composition Root + constructor injection
Only the composition root knows concrete implementations. No Service Locator or hidden dependency construction.

## Group F — Source Topology, Contracts and Tests

### #51 — Capability-first topology + tiny platform primitives
Organize source around product capabilities, not technical layers everywhere.

### #52 — Boundary types are split by semantics
Map types only where semantics genuinely change. Do not create mapping ceremony.

### #53 — Explicit idempotency + domain-owned retry
Queries are retry-safe by default. Side-effect commands use operation/idempotency semantics where appropriate.

### #54 — Canonical GenerationResult/Event
Provider SDK responses are translated into product-owned canonical Generation outcomes/events.

### #55 — Version each boundary independently
API, driver, artifact and DB schema versions evolve independently.

### #56 — Explicit per-domain state machine
Each domain owns its lifecycle transitions. Persistence stores them; API serializes them.

### #57 — Selective event persistence
Persist meaningful business events, not token/progress firehose. No full event sourcing.

### #58 — Registry only for dynamic extensibility sets
DriverRegistry is appropriate. CapabilityRegistry/ServiceRegistry/ApplicationRegistry are not.

### #59 — Shared foundation remains tiny
Only truly generic immutable primitives belong in shared foundation.

### #60 — Capability-first tests
Tests are organized around Generation, Conversation, Training, Dataset, Models, Evaluation, Knowledge, Platform and Architecture.

## Group G — Transport, Async, DB and Artifacts

### #61 — Backend schema is transport source of truth
Generate frontend transport/client types from backend machine-readable schema where possible.

### #62 — Async only for I/O/realtime
Pure domain logic remains synchronous. Heavy CPU/GPU work does not block the coordinator event loop.

### #63 — Abstract nondeterminism only when semantics require it
Clock, ID generator and RNG/seed abstractions are introduced only where determinism/recovery/testing requires them.

### #64 — Model identity/artifact != loaded residency
Model Registry owns identity. Runtime/Residency owns loaded model lifecycle.

### #65 — One physical local DB with capability ownership
Use one local DB while preserving logical table/schema ownership per capability.

### #66 — SQLite is the official V2 database
Do not introduce speculative multi-database portability.

### #67 — Backup/Restore is a small orchestration capability
Backups coordinate a consistent DB snapshot, artifact manifest, versions, hashes and reconciliation.

### #68 — Model acquisition trust/integrity/compatibility gate
Acquire → inspect → hash/integrity → compatibility → trust classification → register → optional publish.

### #69 — Explicit config resolution with precedence/provenance
Resolve defaults/settings/project/conversation/request into a deterministic effective spec before planning.

### #70 — State transition + durable significant event are atomic
Mutation and durable business event/outbox write occur in the same transaction.

## Group H — Communication, Validation and Worker Boundary

### #71 — Direct contracts for required answers; events for notifications
Do not event-drive everything.

### #72 — HTTP status is transport classification; domain+code is business truth
Frontend handles typed business code/domain, not raw messages/status alone.

### #73 — Validation has one owner
API validates shape, domain validates invariants, planner validates feasibility, driver validates provider/runtime compatibility.

### #74 — Worker never owns business DB/state
Worker receives resolved typed input and returns typed events/results/failures.

### #75 — SQLite transactions are short
Never hold a DB transaction while awaiting provider calls, worker execution or long I/O.

### #76 — API routes call the nearest stable capability entry point
Simple routes call capability entrypoints; cross-capability workflows use explicit application use cases.

### #77 — No mandatory Service classes
Entry points are named after responsibility, not generic Service/Manager conventions.

### #78 — Small explicit public capability surface
Cross-capability imports of internal persistence/runtime implementation are forbidden.

### #79 — Domain models are capability-owned
Cross-capability communication uses typed refs/contracts/summaries, not internal aggregates.

### #80 — Streaming/backpressure/cancellation semantics are explicit
Use bounded channels, end-to-end cancellation and controlled force-kill fallback.

## Group I — Generation Content, Security and Runtime Preparation

### #81 — GenerationContent != ConversationMessage != GenerationEvent
Request/result content, persisted conversation semantics and stream events are separate types.

### #82 — Prompt/context assembly occurs upstream
Conversation, Retrieval, Tools and Project defaults prepare normalized context. Generation does not query their stores directly.

### #83 — GenerationPreset is a small reusable resource
Preset carries intent/defaults, not runtime plan or raw provider payload.

### #84 — Loopback API has local session protection
This is not user auth. Use local session/bootstrap credentialing and strict origin handling.

### #85 — Filesystem boundary uses ScopedFileRef/import-export
Raw OS paths are not a common API/business contract.

### #86 — ProviderProfile + GenerationTarget
GenerationRequest references target_id, not endpoint/API key/raw headers.

### #87 — Outbound network is capability-policy owned
No GenericHttpService that lets all capabilities call arbitrary URLs.

### #88 — Runtime preparation occurs before execution
Execution does not secretly download/materialize missing dependencies.

### #89 — Coordinator and heavy runtime environments are distinct
Runtime environments can have their own versioned dependency/health identity.

### #90 — Runtime health probes are lazy and cached
Health/readiness is verified when needed and invalidated by relevant fingerprints.

## Group J — Capability Descriptors, References and V1 Boundary

### #91 — Backend exposes semantic capabilities; frontend owns presentation
No backend-supplied UI schema.

### #92 — Default Project exists from day one
Project-aware semantics can exist without forcing workspace setup.

### #93 — Artifact retention, reference release and physical GC are separate
Domain decides retention. ArtifactStore handles physical mechanics.

### #94 — Typed domain refs; mutable vs immutable semantics are explicit
Reproducible operations resolve mutable resources to immutable refs before execution.

### #95 — Persist submitted intent + resolved execution snapshot
History must not be reconstructed from current settings or logs.

### #96 — Selective optimistic concurrency
Use revisions where competing mutable transitions matter.

### #97 — Commands obey strict ownership; read projections are allowed
Read-only UI projections may aggregate across capabilities without mutation authority.

### #98 — Materialized projection/cache only after benchmark
Derived caches are disposable/rebuildable and never become product truth.

### #99 — V2 state/schema is independent from V1
V1 migration is one-way through an explicit importer/migrator. V2 runtime never falls back into V1 state.

### #100 — Future capability source only when a real vertical slice exists
No speculative empty packages, Base classes or placeholder interfaces.

## Group K — Rewrite Strategy and Hard Boundaries

### #101 — Rewrite order is Generation-first vertical spine

```text
1. Clean boot + minimal backbone
2. Remote Generation E2E
3. Conversation
4. Local Model + Runtime
5. Dataset
6. Training
7. Evaluation
8+. Knowledge / Tools / Agents
```

Each wave must be runnable and testable end to end.

### #102 — Definition of Done is vertical-slice based
A slice includes contracts, owned semantics, executable path, persistence where needed, typed failures, relevant cancellation/recovery, API surface and tests.

### #103 — DAG applies to imports and runtime orchestration
Callback/orchestration loops must not be used to hide cycles.

### #104 — Capability-owned migration content + tiny MigrationCoordinator
Capabilities own their schema evolution. Bootstrap only discovers/orders/applies and tracks versions.

### #105 — Structured correlation observability
Correlate request_id → operation_id → attempt/worker/driver as relevant without leaking tracing dependencies into domain code.

### #106 — Secrets are write-only at the product API
Frontend submits secrets but never receives plaintext secrets back.

### #107 — App-managed filesystem layout

```text
AppDataRoot/
├── db/
├── artifacts/
├── cache/
├── temp/
├── runtime/
├── backups/
└── logs/
```

Capabilities use typed references, not hard-coded raw paths.

### #108 — Explicit ResourceLease/Reservation
Planner admission creates controlled resource leases. Workers cannot self-claim scarce GPU/RAM.

### #109 — Versioned typed IPC between coordinator and worker
Use canonical serializable ExecutionCommand/ExecutionEvent contracts. Ban pickle/live object/ORM/DB connection/model object/arbitrary callable coupling across process boundaries.

### #110 — Worker only writes staged bytes
Coordinator/domain commit path validates staged output and atomically promotes it to a durable artifact before business references are created.

## Group L — Execution Semantics and Historical Truth

### #111 — Deadline != Timeout != Cancellation
Keep OperationDeadline, QueueDeadline, ProviderTimeout, WorkerHeartbeatTimeout and explicit Cancellation distinct.

### #112 — Terminal execution snapshot is immutable
Submitted intent, resolved execution snapshot and terminal outcome cannot be rewritten after terminalization.

### #113 — Partial Generation output is first-class but incomplete
Partial output may be preserved but must never masquerade as a final completed result.

### #114 — Shutdown uses bounded graceful draining
Host requests shutdown → coordinator enters DRAINING → stops new heavy admission → domain-specific stop/checkpoint/interruption → persists truth → releases resources/workers → closes DB.

### #115 — Startup recovery restores truth before deciding resume
Reconcile/classify first. Auto-resume only when domain policy and persisted resume policy explicitly allow it.

### #116 — Semantic execution intent is frozen before queue
Immutable refs, target identity, accepted parameters and fallback decisions do not drift while queued. Only volatile resource/runtime feasibility may be revalidated.

### #117 — Operation != ExecutionAttempt
Operation represents user intent and overall lifecycle. Each concrete execution try is a separate immutable ExecutionAttempt.

### #118 — Fallback remains within the same Operation but creates a new Attempt
Fallback is explicit, policy-controlled and auditable. Drivers may not silently switch providers/runtimes.

### #119 — GenerationTarget capability metadata has provenance and freshness
Differentiate declared, discovered and runtime-verified capability evidence. Refresh when stale rather than trusting forever or probing every request.

### #120 — Live resource lifecycle is separate from historical execution truth
Provider/Model/Target/Preset may be disabled/archived or removed from active use, while historical Operation/Attempt snapshots retain enough immutable metadata to understand past execution.

---

# 8. Proposed Source Shape

This is a directional topology, not a template that must be created before real behavior exists.

```text
src/
├── generation/
├── conversation/
├── models/
│   ├── acquisition/
│   ├── registry/
│   ├── compatibility/
│   └── runtime/
├── dataset/
├── tokenizer/
├── training/
├── evaluation/
│
├── platform/
│   ├── persistence/
│   ├── artifacts/
│   ├── secrets/
│   ├── operations/
│   ├── resources/
│   ├── workers/
│   ├── observability/
│   └── migrations/
│
├── api/
└── bootstrap/
```

Do not create `knowledge/`, `tools/` or `agents/` until each has a real vertical slice, per invariant #100.

---

# 9. First V2 Vertical Spine

The first meaningful product slice after the minimal foundation is Remote Generation E2E.

```text
Frontend
    │
    ▼
POST Generation
    │
    ▼
GenerationRequest
    │
    ▼
Resolve GenerationTarget
    │
    ▼
Capability Negotiation
    │
    ▼
Frozen Execution Intent
    │
    ▼
GenerationOperation
    │
    ▼
ExecutionAttempt
    │
    ▼
Remote Provider Driver
    │
    ▼
Canonical GenerationEvents
    │
    ▼
GenerationOutcome
    │
    ▼
Frontend streaming/render
```

Minimum supporting graph:

```text
ProviderProfile ──> SecretRef ──> SecretStore

GenerationTarget ──> ProviderProfile

Operation
├── immutable submitted request
├── frozen execution intent
├── immutable attempts
└── outcome
```

This slice must run end to end before expanding heavily into Training.

---

# 10. Training Spine

```text
TrainingSpec
     │
     ├── DatasetVersionRef
     ├── ModelArchitectureRef
     ├── TokenizerArtifactRef
     └── Training Parameters
     │
     ▼
Freeze Semantic Intent
     │
     ▼
ResourcePlanner
     │
     ▼
ResourceLease
     │
     ▼
TrainingRun
     │
     ▼
ExecutionAttempt
     │
     ▼
Worker
     │
     ├── progress
     ├── staged checkpoint bytes
     └── staged model bytes
     │
     ▼
Coordinator validation
     │
     ▼
Durable artifacts
     │
     ├── TrainingCheckpoint
     └── ModelArtifact
             │
             ▼
       Model Registry
             │
             ▼
        Publication
             │
             ▼
      GenerationTarget
```

Generation must not depend back on Training.

---

# 11. Ownership Matrix

| Concern | Owner |
|---|---|
| UI/UX/rendering | Frontend |
| API serialization | API |
| Generation semantics | Generation |
| Conversation history/context policy | Conversation |
| Dataset truth | Dataset |
| Model identity/compatibility | Models Registry |
| Model acquisition | Acquisition |
| Loaded model lifecycle | Runtime/Residency |
| Training lifecycle | Training |
| Checkpoint semantics | Training |
| Artifact byte mechanics | ArtifactStore |
| Secrets | SecretStore |
| Hardware facts | SystemCapabilities |
| Admission/resource planning | ResourcePlanner |
| Scarce resource accounting | ResourceLease coordinator |
| Worker execution | Worker runtime |
| DB mechanics | SQLite adapter |
| DB business ownership | Respective capability |
| Recovery policy | Respective domain |
| Bootstrap mechanics | Application Host / Bootstrap |
| Presentation workflow | Frontend |
| Provider SDK translation | Provider driver |

---

# 12. Patterns V2 Must Not Recreate

```text
God AppConfig
GenericRepository
BaseService
GlobalManager
ServiceLocator
GenericJobQueue
GlobalCacheManager
AppContext
GlobalState
CapabilityRegistry
RepositoryManager
GenericHttpService
shared mutable domain entity graph
raw exception strings as API contract
raw filesystem paths as business identifiers
pickle-based worker IPC
worker business-DB access
provider SDK objects leaking inward
ORM entities leaking inward
```

These are high-risk paths back toward the architectural pollution V2 is intended to eliminate.

---

# 13. Archaeology Classification After Baseline Freeze

From this point forward, do not continue expanding the product-invariant list unless implementation exposes a genuine architecture-level contradiction.

The next phase is:

```text
120 Invariants
      │
      ▼
Functional Inventory from old src/
      │
      ├── MUST KEEP
      ├── KEEP + REDESIGN
      ├── FUTURE
      └── DELETE
      │
      ▼
Capability Specifications
      │
      ▼
Dependency DAG
      │
      ▼
Vertical Slice Plan
      │
      ▼
Implementation
```

Examples of details that should **not** become new product invariants by default:

```text
exact retry count
exact worker pool size
exact SSE batching
exact model eviction algorithm
exact SQLite WAL tuning
exact runtime process count
exact cache limits
exact timeout values
exact endpoint naming
```

These belong to:

```text
Capability Spec
Implementation Policy
Benchmark-driven Optimization
```

---

# 14. Baseline Freeze

Architecture discovery is frozen at **Q120**.

The following are considered established:

- product architecture;
- functional capability graph;
- ownership boundaries;
- dependency direction;
- persistence boundaries;
- worker/process boundaries;
- resource-planning boundaries;
- execution lifecycle semantics;
- immutable historical execution semantics;
- V1→V2 archaeology/migration boundary;
- Generation-first rewrite order.

No Q121 is required for this architecture baseline.

The next architecture activity is to map the existing `src/` functional inventory into:

- `MUST KEEP`
- `KEEP + REDESIGN`
- `FUTURE`
- `DELETE`

and only then derive capability specs and implementation plans.
