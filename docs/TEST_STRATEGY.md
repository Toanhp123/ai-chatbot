# Test Strategy

## 1. Goal

The application crosses unreliable and trust-sensitive boundaries: providers, streaming, tools, filesystem/processes, MCP, extensions, SQLite/migrations, local runtimes, and training workers. Tests must make core behavior deterministic enough for CI to run without paid APIs or personal credentials.

Testing also enforces architecture. A documented boundary without a fitness check is weaker than intended for this agent-built project.

## 2. Test layers

### Unit tests

Focus on deterministic logic:

- capability resolution with supported/unsupported/unknown + provenance/freshness;
- RoutePlan envelope/intersection and fallback eligibility;
- provider-neutral prepared request remaining fingerprint-stable while attempts bind compatible route candidates;
- normalized errors/usage/cost per model attempt;
- request/context fingerprint determinism;
- Policy Core evaluation;
- path canonicalization;
- manifest/schema parsing;
- context ranking/token allocation;
- prompt instruction precedence/provenance;
- tool-catalog relevance selection;
- migration helper logic;
- dataset validation.

### Contract/integration tests

Test subsystem boundaries:

- Prompt Runtime → normalized request contract;
- Provider Core adapter ↔ fake server;
- streaming/event/error normalization + first-output commit and attempt-terminal boundaries;
- application tool-call ID ↔ provider-native tool-use ID mapping;
- Task/Run/Turn/ModelAttempt/ToolCall/ToolAttempt persistence/correlation;
- durable lifecycle vs transient stream-event retention/projection, including restart from final snapshots without persisted token deltas;
- Tool Runtime ↔ Policy Core ↔ execution adapter;
- approval fingerprint/precondition re-evaluation;
- parallel read-only tool calls vs serialized effectful calls;
- workspace mutation-lease enforcement;
- SQLite migrations/repositories;
- application/IPC serialization + validation;
- Context Engine inventory/parsing/search;
- MCP Host ↔ fixture server across modern profile/selected legacy compatibility;
- MCP server/descriptor revision, cache TTL and schema-fingerprint behavior;
- MCP Skills → immutable Product Skill revision normalization **with remote-origin trust class and content-bound activation scope preserved**;
- extension install/revision/activation/permission separation;
- workspace trust → Prompt Runtime/Extension Core gating;
- local-runtime descriptor/ownership/capability normalization;
- checkpoint/restore;
- Model Lab controller ↔ fake worker.

### E2E tests

Critical desktop workflows use an isolated profile and deterministic fake provider through the real application/agent/prompt/provider/persistence path. Core E2E never requires a paid API or secret.

The initial deterministic E2E must prove the Phase 1 acceptance path owned by `ROADMAP.md`, including restart persistence, cancellation, and representative provider failure through production-normalized seams. This document owns **how that behavior is tested**, not a second copy of milestone acceptance.

Later E2E layers add project/code-edit/approval/checkpoint, MCP/product Skills, local AI, and Model Lab flows as their phases arrive.

## 3. Architecture fitness tests

Phase 0 must create a dedicated automated architecture gate, exposed as `test:architecture` or a clearly equivalent root command.

It must fail on at least:

- React/Electron imports in core packages;
- renderer imports of provider/storage/tool/MCP/application internals outside allowed contracts/client adapters;
- package edges/cycles forbidden by `ARCHITECTURE.md`;
- provider vendor SDK/HTTP transport use outside Provider Core;
- SQLite driver/raw SQL use outside Storage;
- raw filesystem/shell/Git mutation paths bypassing Tool Runtime/Policy Core;
- workspace-mutating built-in adapters that can execute without the required mutation-lease contract;
- dynamic loading/import of installed third-party extension code into Electron renderer/preload/main/core packages;
- preload exposing raw Node/Electron primitives;
- fake-provider production import/registration leakage.

The checker implementation is flexible. Prefer deterministic source/dependency analysis over LLM judgment for CI.

When a new FROZEN architecture rule is added, add a corresponding fitness test where mechanically possible.

## 4. Fake provider server

Simulate deterministically:

- successful stream and non-stream response;
- one and parallel tool calls;
- structured output;
- usage only at end / usage increments;
- malformed frame;
- disconnect;
- timeout;
- rate limit;
- auth failure;
- context overflow;
- unsupported capability;
- cancellation;
- deterministic fallback-chain cases, including candidates with incompatible context/tool/schema envelopes;
- disconnect after partial committed output;
- separate failed/successful attempt accounting;
- provider continuation-handle/opaque-state expiry or mismatch without loss of canonical local history;
- crash/restart after transient streamed text proves an unfinalized tail is never fabricated as a completed message.

Golden fixtures belong at the normalized internal boundary, not as vendor payload snapshots embedded in UI tests.

## 5. MCP fixture server

Provide controlled profiles for:

- stdio basic tools/resources/prompts;
- current Streamable HTTP profile;
- selected legacy profile only if intentionally supported;
- authorization required/insufficient scope;
- tool list changes;
- malformed schema;
- tool error vs protocol error;
- cancellation/timeout;
- name collision across servers;
- modern no-handshake/discovery request semantics and per-request capability profile;
- list TTL/cache-scope expiry without treating TTL as integrity;
- bounded JSON Schema 2020-12 validation and external `$ref` rejection;
- MRTR/input-required flow proving user input is distinct from local approval;
- remote MCP Task handle correlation distinct from Agent Task/Run;
- MCP Skills list/get/resource flow when supported, including namespace collision, held-manifest/frontmatter verification, per-Skill activation binding, lazy origin-scoped supporting-file reads, baseline resource/size limits, nested-Skill independent activation, and dynamic-content handling with no persistent V1 activation.

## 6. Security tests

Automate where feasible:

- renderer cannot access Node primitives/raw runtime modules;
- unauthorized/invalid IPC rejected;
- secrets absent from logs/snapshots/DB fields;
- workspace path traversal/symlink escape denied;
- permission grant scoping;
- approval becomes stale when tool version/arguments/canonical target/precondition changes;
- symlink/target swap between approval and execution is rejected;
- destructive operation requires approval under policy;
- extension install/update has no executable side effect; package lifecycle scripts do not run and archive traversal/symlink/expanded-size attacks are rejected;
- arbitrary installed extension code cannot dynamically import into renderer/preload/main/core processes;
- restricted workspace `AGENTS.md`/Skill/plugin config cannot enter trusted instruction/execution layers;
- Product Skill bundled scripts cannot execute during discovery/install/activation;
- one immutable extension/Skill revision may be active in multiple scopes without mutating revision identity; revoking one scoped activation does not silently revoke or rewrite another;
- MCP-served Skill provenance remains origin-visible + remote-untrusted after activation/snapshotting, cannot override user/project/local-trusted instruction layers, same-name Skills cannot silently shadow across origins, and implicit Skill resource reads cannot cross to another MCP server;
- digest-consistent MCP Skill content is not promoted to trusted solely because hashes match; nested Skills require independent activation and dynamic/not-content-bindable Skills do not receive persistent V1 activation;
- MCP Skill `allowed-tools`, hooks, scripts or similar metadata never satisfy local capability/permission checks; host-side shell/process/code execution causally requested by an MCP Skill requires both the Skill-revision-scoped user authorization required by the Product Skill policy and the concrete Tool Runtime/Policy Core operation decision;
- malicious MCP/tool/web/file/plugin text cannot mutate trusted policy/instruction layers;
- MCP schema/revision change stales affected pending approval;
- MCP elicitation input cannot satisfy local operation approval;
- auth token is not sent to the wrong resource/redirect destination;
- external/unknown local runtime is never killed by app cleanup;
- connecting to a LAN/remote/unknown local-runtime endpoint surfaces network/auth exposure and never silently changes bind/CORS/listen settings; credentials are scoped to the canonical endpoint and not leaked across redirect/resource changes;
- opaque runtime-hosted MCP/tools cannot masquerade as Tool Runtime authorized actions;
- unsafe/custom model code requires explicit isolated path and never executes in Electron host processes;
- degraded SecretStore state is surfaced.

## 7. Migration/recovery tests

For supported migration paths:

- create DB at previous schema;
- seed representative data;
- migrate;
- verify constraints/indexes/data;
- reopen storage/application;
- test failure rollback/backup policy.

As recovery features arrive, test interrupted-run reconciliation/new-run resume, **task-scoped durable event sequencing continuing monotonically across multiple Runs**, pending approval invalidation when the owning Run ends, state-projection + lifecycle-event/final-message consistency across simulated interruption, ambiguous non-idempotent side effects not auto-replayed, outcome reconciliation proving success/failure only from trustworthy postconditions/status without replay, stale mutation-lease/fencing rejection where multiple processes are possible, export-without-secrets, import validation, redacted diagnostics, and download/model cleanup.

## 8. Context/prompt tests

Fixture repositories verify:

- ignore/secret exclusions;
- incremental changed-file indexing/content-address reuse;
- immutable context package snapshot/fingerprint;
- multi-root path identity;
- exact-symbol and related-test retrieval;
- token-budget truncation;
- provenance preservation;
- untrusted prompt injection cannot override trusted instructions/policy;
- compaction preserves active objective/constraints/next step;
- relevant tool schema selection is bounded;
- stale retrieved file precondition causes conflict/replan rather than overwrite.

## 9. Deterministic agent/runtime evals

Use provider-independent scenario fixtures where exact unit assertions are insufficient:

- correct relevant file/tool selection;
- deterministic route fallback with distinct attempt records;
- partial provider output is not silently merged with a restarted attempt;
- coding task stops for required approval;
- changed pending operation or interrupted owning Run invalidates prior approval;
- safe tool retries preserve one logical `toolCallId` with distinct concrete `toolAttemptId` evidence, and failed retryable Tool Attempts do not emit a logical Tool Call failure before retry/reconciliation policy terminates;
- two mutating runs cannot own the same physical workspace root in V1;
- bounded loop/cancellation terminates cleanly;
- subagent context is scoped;
- compacted state preserves active constraints.

Do not make core CI depend on stochastic remote-model quality scores. Optional live-model evals run separately.

## 10. UI tests and design verification

Use component/integration tests for deterministic interaction state and targeted Electron E2E for critical workflows.

For substantial UI changes, validation evidence includes:

- the required substantial-UI capability route from `DEVELOPMENT_TOOLING.md` was satisfied;
- keyboard/focus path works;
- applicable empty/loading/streaming/error/approval/degraded states are covered;
- at least two realistic desktop viewport sizes were inspected;
- screenshots/rendered surfaces were self-critiqued when tooling supports it;
- no forbidden renderer imports were introduced;
- screenshot regression is added only for stable/high-value screens.

Visual attractiveness does not compensate for broken accessibility or runtime architecture.

## 11. Model Lab tests

Core CI uses fake/small jobs, not expensive GPU training. Hardware-specific tiny training smokes are supplemental and never replace protocol/lineage tests.

Test at least:

- dataset content identity, explicit transforms, deterministic split membership and exact cross-split leakage rejection;
- tokenizer/template/truncation/packing/loss-mask changes producing a new prepared-data fingerprint/TrainingPlan;
- backend capability/config resolution rejecting unsupported combinations rather than silently coercing method/settings;
- worker protocol version/capability handshake, attempt-scoped monotonic events and no DB/SecretStore/Python-object boundary leakage;
- external tracker/upload/network policy disabled by default even when integrations are installed;
- accelerator lease collision/queue semantics and cleanup after failed launch;
- retry/resume creating new TrainingAttempts while preserving lineage;
- graceful cancel → bounded process-tree termination and interrupted-restart reconciliation;
- OOM/backend failure never mutating semantic plan values in-place;
- partial/integrity-failed checkpoints/artifacts rejected for resume/promotion;
- resume compatibility over base/dataset/preparation/method/backend state and required optimizer/RNG/scaler/data-position state where supported;
- staged → finalized checkpoint/artifact transition and retention references;
- base/candidate evaluation using one pinned EvaluationSuiteRevision/config;
- TrainingAttempt completion not auto-registering a Local Model; promotion requires validated immutable artifact lineage/load smoke/evaluation evidence and appends an immutable Model Promotion Record, including alias before/after evidence when applicable.

## 12. Phase gate

Every phase exit requires the applicable subset of:

- format/check;
- lint;
- typecheck;
- unit tests;
- integration/contract tests;
- architecture fitness;
- production build;
- deterministic E2E acceptance flow;
- UI/accessibility/rendered review when UI changed substantially.

Never report a gate passed unless the commands/evidence actually ran successfully.
