# Contract Inventory

> **Authority:** normative cross-boundary contract map
> **Purpose:** prevent duplicate/parallel protocols and make architecture changes reviewable.
> **Rule:** a contract has one owner. Consumers may adapt it at the boundary but must not redefine its semantics locally.

## Stability classes

- **V1-STABLE** — once implemented and used across packages/persistence, breaking semantic changes require migration/versioning and usually an ADR.
- **INTERNAL-STABLE** — stable across internal subsystem boundaries; can evolve deliberately with all consumers/tests updated.
- **EXPERIMENTAL** — intentionally early; may change within the active phase but still has one owner.

## Inventory

| Contract | Owner | Initial stability | Primary consumers | Non-negotiable rule |
| --- | --- | --- | --- | --- |
| Desktop IPC request/event envelopes | `contracts` + desktop main/preload adapters | V1-STABLE after Phase 1 | renderer, preload, main/application | versioned + validated; no raw Electron/Node exposure |
| Application use-case DTOs | `application` / exported through `contracts` where cross-process | INTERNAL-STABLE | renderer/main | presentation-safe; no vendor/SQL/process objects |
| Task/Run/Turn execution identity + lifecycle | `agent-core` + `contracts` | V1-STABLE after Phase 1 | application/storage/UI/provider/tool | task != run != turn; resume/retry creates new child identity; lifecycle evidence ordered |
| Model attempt identity/result | `provider-core` + `contracts` | V1-STABLE after Phase 1 | agent-core/storage/usage | each retry/fallback is preserved; provider IDs are metadata, not app identity |
| Runtime event durability/projection | `agent-core` + `application/storage` + `contracts` | V1-STABLE after Phase 1 | UI/recovery/diagnostics | lifecycle/final snapshots durable; task-scoped monotonic event sequence spans Runs; high-frequency deltas transient by default; final message projection/event stay consistent; restart never requires token replay |
| Prepared normalized model request snapshot | `prompt-runtime` + `contracts` | V1-STABLE after Phase 1 | agent-core, provider-core | immutable provider-neutral semantics; model/provider bound only by the concrete Model Attempt; semantic fingerprint + context/tool/config snapshot identity |
| Normalized model stream/event | `provider-core` + `contracts` | V1-STABLE after Phase 1 | agent-core/application/UI | vendor frames never leak outward |
| Provider capability/model metadata | `provider-core` | INTERNAL-STABLE | routing/settings/UI | tri-state support + provenance/freshness; behavior driven by facts, not provider-name branching |
| RoutePlan / request envelope | `provider-core` + `contracts` | INTERNAL-STABLE | agent-core, context-engine, prompt-runtime | resolved before prompt packing; transparent fallbacks must honor one prepared-request envelope |
| Provider continuation/session state | `provider-core` | INTERNAL-STABLE | agent/storage | IDs/opaque replay-safe metadata are vendor scoped; strategy recorded; never canonical application identity/history |
| Provider error taxonomy | `provider-core` | V1-STABLE after Phase 1 | agent/application/UI | raw vendor errors wrapped with safe diagnostics |
| Context evidence/package | `context-engine` + `contracts` | INTERNAL-STABLE | prompt-runtime, diagnostics | immutable, bounded, provenance + root/hash/snapshot-aware |
| Prompt instruction layers/assembled request diagnostics | `prompt-runtime` | INTERNAL-STABLE | agent/provider/dev diagnostics | trusted precedence explicit; untrusted content cannot promote itself |
| Tool descriptor/invocation/result | `tool-runtime` + `contracts` | V1-STABLE after Phase 3 | agent, MCP adapter, extensions | schema validated; app tool ID distinct from provider tool ID; operation fingerprint/preconditions/idempotency/unknown-outcome semantics explicit |
| Tool execution attempt | `tool-runtime` + `contracts` | INTERNAL-STABLE after Phase 3 | agent/storage/audit | each concrete dispatch/retry preserves attempt evidence; ambiguous dispatched effects are reconciled or remain unknown, never silently replayed |
| Workspace mutation lease | `application` + `contracts`; enforced by `tool-runtime` | INTERNAL-STABLE | agent/tool/storage/UI | one mutating run per physical root in V1 unless isolated; lease never substitutes for permission |
| Permission request/decision/grant scope | `policy-core` + `contracts` | V1-STABLE after Phase 3 | tool-runtime, application/UI, storage adapter | approval binds to operation fingerprint/resource scope and is re-evaluated before execution |
| Workspace/root trust snapshot | `application` + `contracts` | V1-STABLE after Phase 2/4 | prompt-runtime, extension-core, context/tool UI | repository-controlled instructions/config only become trusted/active under explicit trusted source state; permission still separate |
| MCP server/revision/profile/tool/resource/prompt descriptor | `mcp-host` + `contracts` | V1-STABLE after Phase 4 | application/tool/context/extension layers | app-owned server revision identity; protocol/profile/provenance/freshness/schema fingerprint preserved; server self-info/TTL are not trust/integrity |
| MCP remote interaction/task correlation | `mcp-host` + `contracts` | INTERNAL-STABLE after Phase 4 | tool-runtime, application/UI, storage | MRTR input != permission; MCP Task identity remains remote and distinct from Agent Task/Run |
| Product Skill revision / extension manifest | `extension-core` + `contracts` | V1-STABLE when Phase 4/5 ships | prompt-runtime/application/settings/context/tool-policy provenance | immutable revision identity; scoped activation references the revision separately; local/plugin/MCP sources converge here while preserving origin + instruction-trust class; MCP origin remains remote-untrusted; MCP activation approval binds server revision + Skill URI + held manifest/frontmatter revision; `allowed-tools`/scripts are not permission grants |
| Plugin/extension revision + scoped activation | `extension-core` + `contracts` | V1-STABLE when Phase 5 ships | application/UI/storage | revision identity is immutable; activation is a separate scoped association; source/package/capability/executable changes create a new reviewed revision; no arbitrary in-process third-party execution |
| Local runtime/model descriptor | `application` + Provider Core contracts | INTERNAL-STABLE when Phase 7 ships | provider-core/settings/UI/storage | canonical endpoint class, process ownership, capability provenance and model source/revision/integrity remain explicit |
| Storage repository interfaces | `storage` | INTERNAL-STABLE | application/core via explicit ports | raw SQL/driver does not escape Storage |
| Persisted DB schema/migrations | `storage` + `DATA_MODEL.md` | V1-STABLE once released | storage only | forward migrations + upgrade tests; secrets by reference |
| Secret reference/health | desktop secure-storage adapter + `contracts` | V1-STABLE after Phase 0 | application/settings/providers | secret values never ordinary persistence/log data |
| Structured log/audit envelope | owning runtime + shared contract fields | INTERNAL-STABLE | diagnostics/support/recovery | task/run/turn/attempt/tool correlation + redaction required |
| Fake-provider protocol/fixtures | provider test harness | EXPERIMENTAL then INTERNAL-STABLE | integration/E2E | same normalized provider seam; impossible to register in production |
| Model Lab worker protocol | application/controller + `services/model-lab` | V1-STABLE when Phase 8 ships | desktop controller, Python worker | versioned structured messages with TrainingAttempt identity/sequence; no Python objects/DB access across boundary; terminal state and artifact finalization explicit |
| DatasetRevision / prepared-data fingerprint | Model Lab controller/data pipeline + `contracts` | V1-STABLE when Phase 8 ships | worker, evaluation, storage, UI | immutable content/provenance/split lineage; tokenizer/template/packing/loss-mask preparation identity cannot be inferred from mutable paths |
| TrainingPlan / TrainingJob / TrainingAttempt | Model Lab controller + `contracts` | V1-STABLE when Phase 8 ships | worker, storage, UI, recovery | plan immutable before compute; retry/resume creates a new attempt; backend cannot silently mutate semantic parameters |
| TrainingCheckpoint / ModelArtifactRevision | Model Lab controller + `contracts` | V1-STABLE when Phase 8 ships | worker, storage, Local Models, evaluation | resumable checkpoint != adapter/model artifact; finalized manifest/integrity required; base model never overwritten in place |
| EvaluationSuiteRevision / EvaluationRun / Model Promotion Record | Model Lab controller + `contracts` | INTERNAL-STABLE when Phase 8 ships | evaluation worker, storage, Local Models, UI | evaluation configuration pinned; every registration/promotion is append-only audited against immutable artifact + lineage/evaluation evidence; training completion alone never registers a Local Model |

## Change rules

Before changing a contract:

1. identify its owner and stability class;
2. update the owner first, not a downstream local copy;
3. update all producers/consumers and contract tests in the same change;
4. add migration/version negotiation for persisted/external V1-STABLE changes;
5. use an ADR when semantics change across multiple architectural owners;
6. update this inventory if ownership or stability changes.

## Contract anti-patterns

Do not create:

- a second provider event type in the UI because a component needs a convenience field;
- a second permission model inside MCP, plugins, or agent-profile tool/server allowlists;
- a second Product Skill runtime for MCP-delivered skills;
- Product Skill identity based only on display name/URI, or normalization that makes an MCP remote-untrusted Skill indistinguishable from a local/reviewed Skill;
- repository instruction trust inferred merely from opening/indexing a workspace;
- provider/runtime-hosted opaque tools presented as Tool Runtime-authorized actions;
- feature-local SQLite schemas outside Storage migrations;
- vendor request objects as application DTOs;
- renderer-only copies of agent/tool states that diverge semantically from runtime contracts;
- a second notion of “task” that silently conflates Agent Tasks, Runs, Turns, tool calls, training jobs, and MCP Tasks;
- provider response/session IDs used as primary application identity;
- approval records that authorize mutable display text rather than the normalized operation fingerprint/resource scope;
- tool retries that create a fresh logical tool ID to hide an ambiguous earlier side effect;
- Model Lab resume that treats an adapter/inference artifact as a complete trainer checkpoint without manifest/compatibility evidence, model registration implied solely by training completion, or a mutable artifact flag used as the only promotion audit history.
