# ADR-0006 — Cross-system identity, activation, and promotion consistency

- Status: accepted
- Date: 2026-09-24
- Class: FROZEN change / cross-cutting contract consistency
- Supersedes: ADR-0003 event-ordering detail only; all other ADR-0003 decisions remain in force
- Clarifies: ADR-0004 extension activation representation; ADR-0005 TrainingJob/promotion audit representation
- Superseded by: none

## Context

The full-system contract audit found several places where individually reasonable subsystem docs could produce incompatible implementations:

- durable Agent lifecycle events were ordered per Run even though Task-only events and multiple resume Runs must share one inspectable history;
- Tool Call and Tool Attempt identities were distinct, but event names did not consistently distinguish attempt terminal events from logical-call terminal state;
- extension revisions are immutable and may be active in multiple scopes, yet persistence wording mixed activation state into revision records;
- TrainingJob was canonical in Model Lab but missing from the frozen lineage wording;
- model registration/promotion required evaluation evidence, but an append-only promotion decision record was not explicit.

These are contract-consistency defects, not new product features or new top-level architecture modules.

## Decision

1. **Task-scoped durable event order.** Durable Agent lifecycle events use one monotonically allocated `(taskId, sequence)` order across all Runs of a Task. Run/Turn/Attempt IDs remain correlation dimensions. Task-only events never fabricate a Run.
2. **Tool call vs attempt events stay distinct.** Concrete dispatch/retry lifecycle uses `tool.attempt_*` events and `toolAttemptId`. Logical `tool.completed` / `tool.failed` / `tool.unknown_outcome` / `tool.cancelled` are emitted only when retry/reconciliation policy has produced a logical Tool Call terminal result.
3. **Prepared request/context terminology is canonical.** Cross-boundary persistence and diagnostics use the canonical `PreparedModelRequest`, `ContextPackage`, `RoutePlan`, and associated fingerprints rather than near-synonym request/context types.
4. **Instruction ownership remains single.** Context Engine selects bounded evidence/resources; Prompt Runtime owns authoritative instruction layering, final request packing, and compaction representation. Product Skill instruction bodies are not independently assembled by Context Engine.
5. **Agent exposure is not permission.** Agent-profile tool/MCP allowlists only narrow eligible descriptors. They neither activate extensions/servers nor grant runtime effects; Tool Runtime + Policy Core remains authoritative.
6. **Revision identity is separate from scoped activation.** Product Skill/plugin/MCP revision bytes and security-relevant identity are immutable. Activation is a separate association from a specific revision to an explicit scope; one revision may have multiple independent scoped activations.
7. **TrainingJob is a logical experiment, not an execution attempt.** A TrainingJob references one immutable TrainingPlan and may own multiple TrainingAttempts. Job status is a projection over attempts/promotion, not a second execution state machine.
8. **Promotion is append-only audited.** Every successful Model Lab registration/promotion appends a Model Promotion Record binding the exact ModelArtifactRevision, resulting Local Model/revision, supporting TrainingPlan/DatasetRevision/EvaluationRun evidence, actor/source, timestamp, and alias before/after references where applicable. Mutable artifact/alias state is not the sole promotion history.
9. **Unknown outcome vocabulary is explicit.** Ambiguous dispatched side effects and unreconciled training-worker terminal reality use `unknown_outcome` where the product cannot truthfully claim success/failure/cancellation.

## Consequences

- Storage allocates Task-level lifecycle sequence numbers rather than independent Run sequences.
- UI/recovery can render resume history in one stable event order without inventing synthetic Runs.
- Tool retries no longer risk a failed attempt being misread as a failed logical Tool Call.
- Extension activation can be revoked per scope without mutating or duplicating immutable revision identity.
- Model Lab audit/history can explain exactly when and why a candidate entered Local Models, even if aliases later move.
- No new top-level runtime package is introduced; this ADR refines contracts already owned by Agent Core, Prompt/Context, Extension Core, Storage, Tool Runtime and Model Lab.

## Alternatives considered

- **Keep per-Run event sequence plus a special task-only ordering scheme.** Rejected: creates two ordering contracts and makes resume timelines harder to reason about.
- **Treat activation as mutable state on each revision.** Rejected: one revision can be active in multiple scopes and revocation must not rewrite revision identity.
- **Use model-artifact `promoted=true` as audit history.** Rejected: loses actor/evidence/alias transition history and cannot represent repeated promotion decisions.
- **Let agent-profile allowlists grant permission.** Rejected: creates a second authorization model beside Policy Core.

## Fitness / verification

Tests/architecture checks must prove at least:

- Task event sequence remains monotonic across interrupted Run → resumed Run and includes Task-only events without synthetic Run IDs;
- retryable failed Tool Attempts do not emit logical Tool Call failure before retry/reconciliation terminates;
- Context Engine does not assemble Product Skill instruction authority or redefine Prompt Runtime precedence;
- one immutable extension/Skill revision can be active in multiple scopes and revoking one scope does not rewrite/revoke another;
- agent tool/MCP exposure allowlists cannot satisfy permission or extension-activation checks;
- TrainingJob retry/resume produces distinct TrainingAttempts while job status remains a projection;
- every Model Lab promotion creates an immutable Model Promotion Record and alias changes preserve before/after history.

## Revisit trigger

Revisit only if implementation evidence shows Task-scoped ordering cannot satisfy required concurrency/recovery semantics, scoped extension activation requires a materially different ownership model, or Local Models promotion evolves into a separate deployment/release system with stronger transactional requirements.
