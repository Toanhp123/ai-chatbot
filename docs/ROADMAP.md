# Roadmap

The roadmap is vertical: every phase ends in a real usable workflow and executable evidence. FROZEN architecture comes from `ARCHITECTURE.md`; roadmap phases do not authorize bypassing it.

## Phase 0 — Foundation

Deliver:

- workspace/package structure reflecting the frozen ownership model as responsibilities become real;
- Electron shell with secure main/preload/renderer separation;
- typed versioned IPC/application seam;
- `contracts`, `application`, `provider-core`, `prompt-runtime`, `storage`, and other Phase-0-required boundaries without forbidden reverse dependencies;
- SQLite storage + reproducible migrations;
- `SecretStore` abstraction with security-health/degraded state;
- structured logging/redaction foundation;
- semantic design tokens/basic shell UI produced through the required substantial-UI capability route;
- normalized provider request/event types and Prompt Runtime boundary;
- explicit profile/data-root abstraction for production vs tests;
- deterministic fake-provider skeleton behind Provider Core;
- architecture fitness tests for frozen dependency/trust rules;
- developer-tooling behavior consistent with `DEVELOPMENT_TOOLING.md`, including the required route for final structural review once substantive source exists;
- stable root validation commands;
- canonical docs/ADRs/contract inventory aligned with scaffold.

Acceptance criteria:

- production build launches on the primary development OS;
- renderer has no direct Node/filesystem/provider/storage/tool/MCP/secret access;
- core packages do not import React/Electron;
- typed IPC/application seam is validated at runtime boundaries;
- DB migrates from empty schema and reopens cleanly;
- secret round-trip works on supported secure backend, with degraded state detectable;
- architecture-fitness command catches representative forbidden imports/edges;
- final Phase 0 structural review satisfies the evidence/blocking rules owned by `DEVELOPMENT_TOOLING.md`;
- fake provider is reachable only through Provider Core and excluded from production registration;
- shell UI has real empty/loading/error/degraded states required by Phase 1, keyboard/focus basics, and validation at multiple desktop sizes;
- `format:check`, `lint`, `typecheck`, `test`, `test:integration`, `test:architecture`, `test:e2e`, and `build` (or documented equivalents) are available;
- foundational architecture/security/data/provider/UI docs match actual code.

## Phase 1 — Real chat core

Deliver:

- provider/model registry and provenance/freshness-aware capability model;
- minimal Agent Core execution spine for ordinary chat using Task → Run → Turn → ModelAttempt identity/event contracts (no coding tools required yet);
- immutable Context/PreparedModelRequest snapshots for each turn;
- OpenAI-family adapter;
- Anthropic adapter;
- Gemini adapter or explicit documented deferral after the first two if active scope requires;
- custom compatible endpoints;
- normalized prompt assembly + streaming/errors/usage;
- persisted conversations/messages plus task/run/turn/model-attempt evidence and per-attempt usage;
- attachment metadata foundation;
- provider test harness;
- deterministic chat UI slice using real runtime/application contracts.

Acceptance criteria:

App launches in an isolated test profile → fake provider selected through normal application/provider administration seams → user turn enters Application → Agent Core resolves a RoutePlan through Provider Core → Context Engine builds the bounded evidence package → Prompt Runtime prepares the immutable provider-neutral request → Provider Core executes the concrete Model Attempt → normalized runtime/events reach the UI → conversation/messages/task-run-turn-attempt evidence and usage persist → app restarts with the same profile → persisted state remains.

Also:

- retry/fallback produces distinct attempt records, reuses one immutable provider-neutral semantic request only across compatible candidates, and never erases failed-attempt usage;
- disconnect after partial committed output is surfaced without silently concatenating a restarted attempt;
- cancellation stops a stream;
- at least one provider failure is normalized and rendered safely;
- UI contains no vendor stream parsing/payload construction;
- fake-provider malformed/disconnect cases have integration coverage;
- fake provider cannot enter production configuration/runtime;
- architecture fitness remains green.

A live/local provider smoke is supplemental when already authorized/configured.

## Phase 2 — Projects and code intelligence

Deliver:

- Projects with one-or-more workspace roots;
- project instructions;
- ignore-aware repository inventory;
- Tree-sitter structural parsing for initial languages;
- repository/symbol map;
- lexical search;
- context planner + token budgeting;
- read-only code Q&A;
- incremental indexing.

Acceptance criteria:

Open a real repository → ask about a symbol/feature → diagnostics show a bounded provenance-aware context set → answer references correct files → ignored/secret paths are excluded by default → editing a file causes incremental refresh rather than full rebuild.

## Phase 3 — Coding agent

Deliver:

- expand the Phase 1 Agent Task/Run/Turn runtime into the coding-agent loop;
- planning workflow;
- filesystem patch tools;
- command/process tools;
- read Git tools then scoped mutation tools;
- Policy Core + Tool Runtime approval path with operation-fingerprint binding/re-evaluation;
- stale-write resource preconditions, logical tool-call vs concrete tool-attempt identity, and explicit ambiguous-side-effect handling/reconciliation;
- one mutating run per physical workspace root unless using an explicitly isolated workspace/worktree;
- diff/checkpoint UI;
- optional isolated worktree/workspace execution for suitable tasks;
- test/lint/fix loop;
- cancellation propagation.

Acceptance criteria:

Request a small code change → agent inspects first → plans where appropriate → acquires mutation ownership → requests only necessary approval bound to the exact operation → patches files through Tool Runtime with stale-write preconditions → runs validation → displays diff → user can restore checkpoint without losing unrelated pre-existing work. A changed target/precondition or interrupted owning Run invalidates the pending approval rather than silently executing the modified action. A dispatched non-idempotent tool with ambiguous completion is surfaced/reconciled and is not auto-replayed.

## Phase 4 — MCP + Product Skills

Deliver:

- MCP server registry;
- stdio + current Streamable HTTP implementation;
- version/profile compatibility layer;
- HTTP auth foundation;
- tool/resource/prompt discovery with schema/cache/provenance revisions;
- relevance-based tool catalog exposure;
- workspace-trust state for repository-controlled instructions/contributions;
- global/project Product Skills with immutable revisions + scoped activation records;
- MCP Skills extension support when the selected SDK/profile is proven compatible, normalized into the same Product Skill runtime;
- progressive Skill loading with no script auto-execution.

Acceptance criteria:

Connect a fixture/real MCP server → inspect app-owned server revision/provenance/capabilities → expose only selected relevant tool schemas → invoke through Tool Runtime/Policy Core → disconnect/reconnect cleanly. Repository instructions stay untrusted in a restricted workspace. A local Product Skill can activate an immutable reviewed revision in an explicit scope without mutating revision identity. An MCP-delivered Skill can be discovered lazily, then explicitly activated **per Skill** against its server revision + Skill URI + held manifest/frontmatter revision while preserving remote-untrusted origin; changed/dynamic content does not silently inherit persistent activation, nested Skills need separate activation, `allowed-tools`/scripts grant no capability, and bundled scripts never auto-execute.

## V1 release gate

V1 is the stable combination of Phases 0–4 plus basic configurable custom agents.

Release only when:

- architecture fitness is enforced in CI and green;
- data migrations have upgrade tests;
- secrets/permission boundaries have focused security review;
- core E2E runs without paid APIs;
- crash/restart preserves conversations/projects/settings and safely reconciles interrupted tasks;
- test/production profiles cannot accidentally share secrets/state;
- backup/export/diagnostic boundaries are secret-safe;
- contract inventory matches real cross-boundary APIs;
- no production path relies on mock data;
- known limitations are documented.

## Phase 5 — Plugins + marketplace

Deliver only after the product Skill/MCP trust model is proven:

- versioned plugin manifest;
- install/update/disable/enable/uninstall;
- install vs activation separation;
- trust/permission review;
- registry abstraction/UI;
- bundled Product Skills/agents/MCP definitions;
- staged revision update + capability/permission diff + rollback metadata;
- declarative contributions first; no arbitrary host-process code loading;
- executable hooks/workers only after isolated capability-mediated extension runtime + sandbox/permission tests are proven;
- public plugin SDK only when third-party compatibility requires it.

## Phase 6 — Advanced agent platform

Deliver selectively:

- richer custom agents;
- synchronous then parallel subagents;
- conflict-aware parallel tasks;
- lifecycle hooks;
- web research mode;
- isolated browser automation;
- richer artifacts/trace.

## Phase 7 — Local AI

Deliver:

- local runtime detection/configuration;
- Ollama;
- llama.cpp-compatible;
- LM Studio compatible;
- optional vLLM/custom runtime;
- hardware inventory/fit estimates;
- endpoint class/process-ownership visibility;
- local model source/revision/integrity/custom-code metadata;
- local model metadata/management hooks without opaque runtime-hosted tool bypass.

Acceptance criteria:

Configure at least one supported local runtime through a canonical endpoint identity → classify endpoint as loopback/LAN/remote/unknown and surface auth/exposure state → list or manually configure a model with source/capability provenance → stream chat through the normal Agent/Prompt/Provider spine → surface capability mismatch instead of silently dropping requirements. Runtime stop/restart must not corrupt conversation state; app cleanup must not kill externally owned/unknown processes; connecting must not silently widen bind/CORS/network exposure; opaque runtime-hosted tools/MCP must not masquerade as Tool Runtime-authorized operations; model artifact metadata must preserve source/revision/integrity/custom-code risk; unsafe/custom model code must remain outside Electron host processes.

## Phase 8 — Model Lab

Deliver:

- immutable DatasetRevision import/validation/transform/split lineage;
- immutable TrainingPlan + TrainingJob/TrainingAttempt lifecycle;
- versioned isolated worker protocol/environment with local/offline-by-default compute;
- backend capability resolution for SFT/LoRA/QLoRA;
- NVIDIA backend path;
- Apple Silicon MLX-LM path;
- device resource lease + disk/hardware preflight;
- structured metrics and staged/finalized resumable checkpoints/artifacts;
- pinned evaluation suites and base-vs-candidate comparison;
- explicit candidate validation/export/Local Models promotion with append-only Model Promotion Record.

Acceptance criteria:

Import a dataset into an immutable revision → validate/dedupe and create reproducible non-overlapping splits → resolve immutable base model, tokenizer/template, backend capability/environment and resource fit into a TrainingPlan → acquire the declared device lease → launch one TrainingAttempt through the versioned worker protocol with external trackers/upload disabled by default → stream structured metrics → finalize a resumable checkpoint and/or inference adapter with manifest/integrity → run the same pinned evaluation suite against base and candidate → verify lineage/loadability/license metadata → explicitly register the candidate as a Local Model and append a Model Promotion Record. Retry/resume must create a new attempt, incompatible/partial checkpoints must not resume, OOM/failure must not silently mutate the plan, and TrainingAttempt completion alone must not promote a model.

## Phase discipline

Do not implement a later phase because its name/type appears in architecture. Reserve only the stable boundary required by known future integration; instantiate packages/services when their first real responsibility is implemented.
