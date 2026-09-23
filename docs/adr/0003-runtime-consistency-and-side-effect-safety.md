# ADR-0003 — Runtime identity, replay, approval binding, and side-effect safety

- Status: accepted
- Date: 2026-09-23
- Class: FROZEN cross-cutting runtime/security contract
- Supersedes: none
- Superseded by: ADR-0006 (event-ordering detail only)

## Context

The V1 architecture already separated Agent Core, Provider Core, Prompt Runtime, Tool Runtime, Policy Core, Context Engine and Storage, but several cross-cutting runtime semantics remained underspecified:

- a single `AgentTask` identity was carrying concepts that become different once a task is resumed, retried or interrupted;
- provider retry/fallback could not be reconstructed precisely if attempts were overwritten or provider request IDs became de-facto application identity;
- an approval was re-evaluated, but the contract did not bind it to an immutable normalized operation fingerprint/precondition set;
- crash/timeout behavior did not state what happens when a non-idempotent side effect may already have been dispatched;
- multiple agent runs could otherwise mutate one physical workspace concurrently without an explicit conflict/lease rule;
- context and prompt inputs were described as bounded but not explicitly immutable/versioned for an in-flight model attempt.

These gaps can produce duplicate effects, stale overwrites, misleading audit history and non-reproducible agent runs even when individual subsystem boundaries are otherwise correct.

## Decision

Freeze the following V1 runtime invariants:

1. **Identity hierarchy** — `taskId`, `runId`, `turnId`, `modelAttemptId`, `toolCallId`, `toolAttemptId` and `approvalRequestId` are distinct concepts. Retry/fallback/resume/concrete tool redispatch creates new child execution identity instead of rewriting prior evidence. Provider-native request/session/tool IDs remain metadata.
2. **Canonical local state** — application/Storage task-run-turn-event history is authoritative. Provider response/session IDs are optional vendor-scoped continuation metadata only.
3. **Immutable request evidence** — Context Engine returns immutable versioned context packages; Prompt Runtime returns immutable prepared request snapshots/fingerprints. Once a provider attempt starts, changes create a new turn/request rather than mutating the in-flight snapshot.
4. **Route-plan compatibility** — Provider Core resolves an immutable per-turn RoutePlan before context/prompt packing. Transparent fallback candidates share one request/context envelope; the runtime never silently repacks an in-flight request to fit an incompatible fallback.
5. **Attempt preservation** — every provider retry/fallback is recorded as its own attempt; failed attempts and their usage/cost are not erased by the eventual success.
6. **Commit-aware retry** — provider attempts are not silently restarted/merged after user-visible output or acted-upon tool requests have committed unless an explicit provider continuation contract makes the boundary safe and observable.
7. **Approval binding** — a pending approval binds to normalized tool/version/arguments/resources/**expected** preconditions through an operation fingerprint. Before execution, Tool Runtime re-resolves current targets, verifies the bound preconditions still hold, and Policy Core re-evaluates the same operation/current facts. Expected hashes/revisions are never silently rewritten to make stale approval pass. A terminal/interrupted owning Run invalidates its pending approval.
8. **No exactly-once fiction** — each concrete tool dispatch has attempt evidence. Non-idempotent/irreversible effects are not automatically replayed after timeout/crash/cancellation once dispatch may have occurred. Ambiguous outcomes remain explicit and require reconciliation.
9. **Stale-write protection** — file/Git mutations use content/revision preconditions where the operation depends on previously observed state; stale evidence yields conflict/replan rather than overwrite.
10. **Workspace mutation ownership** — V1 permits at most one mutating run per physical workspace root at a time. Read-only runs may coexist. Isolated worktrees/roots may mutate independently and require an explicit apply/merge step.
11. **Durable consistency** — when runtime state plus lifecycle event are durable, Storage commits them consistently; database transactions are never held open while waiting on providers, user approvals, subprocesses or remote tools.
12. **Single model-generation spine** — all user-visible model generation, including ordinary chat, flows through Application → Agent Core → Prompt Runtime → Provider Core. Application may access provider registry/discovery/health administration directly, but it does not own a second generation loop.
13. **Durable reconstruction without token replay** — high-frequency text/reasoning/tool-progress deltas are transient by default. Canonical final normalized message/tool snapshots and explicit interrupted partial-output evidence are durable enough to reconstruct retained product history after restart. A process crash may lose the final unpersisted transient display tail; that loss is preferable to fabricating a completed message.
14. **Semantic request / provider attempt separation** — Prompt Runtime prepares provider-neutral semantics inside a RoutePlan envelope; Provider Core binds that immutable request to one route candidate per `modelAttemptId`. The semantic request itself is not rewritten to swap models/providers.

These rules refine existing ownership; they do not add a new top-level runtime module.

## Consequences

- Crash/restart and retry behavior becomes explainable instead of inferred from UI state.
- Usage/cost accounting can include failed/fallback attempts accurately.
- Human approval cannot be reused after a tool target/arguments changed while waiting.
- Concurrent agents cannot silently clobber one workspace in V1; higher concurrency requires isolated workspaces or a future explicit conflict model.
- Tool/process adapters need stronger operation descriptors, preconditions, concrete execution-attempt evidence and audit identities.
- Persistence gains additional runtime entities (`task_runs`, `turns`, `model_attempts`) and uniqueness/transaction invariants.
- Some apparently convenient automatic retries must stop and surface an ambiguous outcome instead.
- Provider adapters may retain bounded vendor-scoped continuation state required for correct protocol continuation, but product history and application identities remain local/canonical.

## Alternatives considered

### Keep one task ID/state and infer attempts from events

Rejected because resume/crash/fallback semantics become ambiguous and projections cannot reliably distinguish a durable goal from one execution instance.

### Rely on provider session/request IDs for continuity

Rejected because those IDs are vendor/account scoped, may expire, and would make local-first conversation/runtime history depend on remote retained state.

### Treat user approval as a boolean attached to the tool name

Rejected because arguments, paths, symlink targets, workspace revision or tool implementation can change between approval and execution.

### Allow concurrent mutation and rely on Git conflicts

Rejected for V1 because many filesystem/process side effects occur before Git conflict detection and because local dirty work may not be committed.

### Automatically retry every timed-out tool call

Rejected because many external mutations cannot provide exactly-once semantics and a timeout does not prove the side effect failed.

## Fitness / verification

Add deterministic tests for:

- unique ordered run event sequence and task/run/turn/attempt correlation;
- RoutePlan transparent-fallback envelope rejecting an incompatible smaller/different candidate rather than silently repacking;
- retry/fallback preserving separate attempt records and failed-attempt usage;
- prepared request/context snapshot immutability;
- partial provider stream failure not silently merged with a restarted attempt;
- stale approval rejection when arguments/target/tool version/bound precondition changes, including pending approval invalidation after owning Run interruption;
- stale file/Git precondition returning conflict without overwrite;
- logical tool call preserving separate `toolAttemptId` records across safe retries;
- ambiguous non-idempotent tool timeout/cancellation not auto-replayed;
- workspace mutation lease preventing two mutating runs on the same root;
- crash reconciliation creating a new run on resume rather than reviving old execution identity;
- state projection + lifecycle event consistency across simulated process interruption;
- ordinary chat proving the same Agent Core → Prompt Runtime → Provider Core generation spine used by later agent turns;
- restart reconstruction from canonical final message/tool snapshots even when transient stream deltas were not persisted;
- provider-neutral semantic request bound to different compatible route candidates without mutating its fingerprint;
- application tool ID remaining stable while provider-native tool-use identifiers differ by adapter/protocol.

## Revisit trigger

Revisit only when concrete V1 implementation evidence demonstrates that a rule prevents a required workflow and an alternative provides equal or stronger auditability, side-effect safety and recovery semantics. Parallel mutation of one physical workspace specifically requires a new conflict/transaction model and superseding ADR rather than an implementation shortcut.
