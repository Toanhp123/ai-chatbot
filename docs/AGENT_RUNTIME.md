# Agent Runtime

## 1. Responsibility

Agent Core orchestrates model turns, context, tools, approvals, retries/fallbacks, subagents, cancellation, and task state. It must not depend on React/Electron and must not directly implement provider transports or raw shell access.

Agent Core owns orchestration semantics and emits typed transition/event data. Application persists durable runtime state through Storage; Agent Core does not import Storage. In-memory objects are projections/caches, not a second source of truth.

## 2. Execution identity hierarchy

Do not overload one identifier for every level of work. V1 uses stable correlation identities with these meanings:

- `taskId` — durable user goal/work item; may survive multiple executions/resumes;
- `runId` — one execution/resume of a task;
- `turnId` — one agent decision cycle within a run;
- `modelAttemptId` — one concrete provider/model attempt, including retries/fallback candidates;
- `toolCallId` — one logical model-requested tool invocation;
- `toolAttemptId` — one concrete execution/dispatch attempt of that logical tool call when retries/reconciliation are applicable;
- `approvalRequestId` — one pending human authorization request bound to a specific normalized operation;
- subsystem-specific long-running work keeps its own identity namespace; Model Lab uses `trainingJobId` + `trainingAttemptId` from `MODEL_LAB.md` rather than a generic Agent `jobId`.

IDs are opaque and never inferred from array positions or provider IDs. Provider request/session/tool-use IDs are vendor-scoped metadata attached to the applicable application identity; they do not replace application identities.

Every event carries the smallest sufficient correlation set. Task-scope events always carry `taskId`; run-scope and deeper events also carry `runId`; turn/model/tool events additionally carry `turnId` and the applicable attempt/call identifier. A task event that genuinely occurs without an active Run must not invent a fake `runId`.

## 3. Task and run state

Separate the durable task from an individual execution run so crash/restart/resume semantics stay explicit.

Minimum task status:

```text
open <-> blocked
open -> completed | failed | cancelled
blocked -> completed | failed | cancelled
```

`blocked` is non-terminal: an external condition may be satisfied later and the task can return to `open`. `completed`, `failed`, and `cancelled` are terminal unless an explicit product-level retry/reopen action creates new history rather than rewriting old evidence. A failed/interrupted **run** does not have to fail the Task; Application may leave the Task `open` and create a new Run.

Minimum run state:

```text
queued -> planning -> running
running <-> waiting_for_approval
running <-> waiting_for_input
running <-> paused
running -> completed | failed
queued | planning | running | waiting_* | paused -> cancelled | interrupted
```

`interrupted` means the process/runtime disappeared before a reliable terminal result was persisted. It is terminal for that run; resuming creates a new `runId`.

## 4. Runtime snapshot

Conceptual types:

```ts
interface AgentTask {
  id: string;
  status: TaskStatus;
  parentTaskId?: string;
  projectId?: string;
  conversationId?: string;
  createdAt: string;
  finishedAt?: string;
}

interface AgentRun {
  id: string;
  taskId: string;
  state: RunState;
  agentConfigSnapshotId?: string;
  routeId: string;
  activeModel?: ModelRef;
  workspaceSnapshot?: WorkspaceExecutionRef;
  turnCount: number;
  maxTurns: number;
  budget?: TaskBudget;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}
```

Persist the resolved agent configuration/route/policy references or immutable snapshots needed to explain a run later. Do not reconstruct historical behavior from whatever settings happen to be current after an upgrade.

## 5. Runtime loop

For each run:

1. validate task/run request, execution workspace and effective policy;
2. ask Provider Core to resolve an immutable `RoutePlan` for the turn, including the primary candidate, transparent-fallback candidates and shared request/context envelope;
3. ask Context Engine for an immutable bounded context package within the RoutePlan budget envelope;
4. ask Prompt Runtime for a prepared normalized request snapshot constrained by that envelope;
5. invoke Provider Core with the RoutePlan, prepared request, a new `modelAttemptId` and cancellation token;
6. convert provider deltas/tool requests/usage/errors into normalized events;
7. if tools are requested, validate the call and invoke only through Tool Runtime;
8. if approval/input is required, suspend the run with a correlated request event;
9. feed normalized tool results back through Prompt Runtime/Provider Core as the next turn input;
10. repeat within turn/time/cost/tool-call budgets;
11. complete, fail, block, cancel, pause, or interrupt explicitly.

A retry/fallback creates a new `modelAttemptId`; it does not rewrite the failed attempt. A resumed interrupted task creates a new `runId`; it does not pretend the old run continued.

## 6. Normalized runtime events

Use stable event categories rather than copying provider stream event names:

```text
task.created
task.state_changed
run.created
run.state_changed
turn.started
turn.completed
model.attempt_started
model.output_committed
model.attempt_completed
model.attempt_failed
model.attempt_interrupted
message.started
message.text_delta
message.completed
tool.requested
tool.attempt_started
tool.attempt_dispatched
tool.attempt_progress
tool.attempt_completed
tool.attempt_failed
tool.attempt_unknown_outcome
tool.attempt_cancelled
tool.completed
tool.failed
tool.unknown_outcome
tool.cancelled
approval.required
approval.resolved
input.required
usage.updated
artifact.created
checkpoint.created
context.compacted
run.completed
run.failed
run.cancelled
run.interrupted
task.completed
task.failed
task.cancelled
```

Events include timestamp, typed payload and correlation IDs, but not every event has the same durability class. `tool.attempt_*` events describe one concrete Tool Attempt; `tool.completed`/`tool.failed`/`tool.unknown_outcome`/`tool.cancelled` describe the logical Tool Call only after retry/reconciliation policy has reached a logical terminal result. Consumers must not infer a logical Tool Call terminal state from one failed retryable attempt.

**Durable lifecycle evidence** includes task/run/turn transitions, model-attempt start/first-output-commit/terminal metadata, canonical final normalized messages (or explicit partial-message evidence for interrupted committed output), tool requested/dispatch-attempt/terminal records, approvals, final/aggregate usage, artifacts/checkpoints and compaction metadata. Persisted lifecycle sequence is unique and monotonic per Task across all of its Runs. When a final `messages` projection and its lifecycle event are both durable, Storage commits them consistently and the event references the canonical message ID instead of duplicating an independent message body.

**Transient stream/progress events** include text/reasoning deltas, partial tool arguments, tool progress and high-frequency stdout/stderr chunks. They may be coalesced/dropped for slow UI consumers and are not required in SQLite to reconstruct the final conversation after restart. If retained for diagnostics, use bounded/expiring trace storage rather than treating every token delta as durable product history.

When state changes are durable, Application/Storage persist the state projection and corresponding lifecycle event atomically so restart cannot observe a new state without its evidence or vice versa. Agent Core emits the transition; it does not open database transactions.

## 7. Cancellation, interruption and user input

Cancellation is first-class and distinct from crash/interruption.

A cancellation request should propagate, where supported, to:

- provider stream/request;
- local tool invocation;
- spawned/managed process;
- MCP request/task;
- subagent;
- browser/sandbox task;
- Model Lab TrainingAttempt only when the task explicitly owns/started that attempt; cancellation uses the Model Lab controller and exact `trainingAttemptId`, not generic process/job inference.

Use cooperative cancellation plus hard termination for bounded owned child processes when necessary. Cancellation is not an error unless a subsystem fails to stop within policy.

User interruption/input is also explicit. New user input that changes the active goal must be represented as a new event/turn; do not mutate an already prepared model request or pending tool operation in place. If input arrives while a model attempt is active, first request cancellation/terminalization of that attempt (or queue the input) before preparing the new turn. If a side effect is already dispatched and its outcome is ambiguous, steering cannot erase that ambiguity; reconcile/surface it before later reasoning assumes the effect did or did not happen.

## 8. Retry, fallback and commit boundaries

Keep separate:

- **retry** — another attempt of the same logical candidate under bounded transient-failure policy;
- **fallback** — a new attempt using the next eligible route candidate;
- **resume** — a new run or provider-native continuation whose relationship to prior persisted state is explicit.

Provider Core owns model-attempt retry/fallback rules; Agent Core owns whether the run can continue after an attempt fails.

Never automatically replay a non-idempotent tool operation after an ambiguous timeout/crash. Model retries must not duplicate already committed side effects. If a provider attempt has already emitted user-visible output or tool requests that were persisted/acted upon, do not silently merge a restarted/fallback attempt into the same output stream; surface the boundary or fail/recover explicitly.

## 9. Tool loop safety

- Validate tool identity and schema.
- Resolve the current tool catalog snapshot, not model-invented tools.
- Enforce max tool calls/turn/run budget.
- Treat provider parallel-tool output as multiple correlated requests; assign application `toolCallId` values independently of provider-native tool-use IDs. Tool Runtime decides safe execution concurrency, and effectful calls are not automatically run in parallel.
- Avoid recursive agent/tool loops without a hard bound.
- Tool result content is untrusted context.
- Large output is summarized/truncated/file-backed with provenance instead of pushed whole into the next model request.
- Preserve security-relevant causal instruction provenance from the prepared turn into Tool Calls (notably active MCP-origin Skill revision/origin) so Policy Core can enforce source-scoped rules without inferring them from model prose.
- Respect Tool Runtime idempotency/precondition semantics; Agent Core must not retry tool calls by constructing a fresh ID to bypass an ambiguous prior result.

## 10. Custom agents

Agent definitions are data/configuration:

- name/description;
- system instructions;
- preferred route;
- allowed tools;
- allowed MCP servers;
- Skills;
- permission profile;
- maximum turns;
- optional token/cost/time budget.

`allowed tools` / `allowed MCP servers` are exposure/eligibility constraints only. They may narrow what the agent can see/request, but they never activate an extension/server or grant execution permission; workspace/extension activation and Tool Runtime + Policy Core still apply.

Do not create subclasses such as `SecurityReviewerAgent` in core unless behavior genuinely differs at runtime-contract level.

## 11. Subagents

A subagent receives:

- one explicit task;
- selected context bundle;
- selected tools;
- model/route;
- budget;
- parent correlation ID.

It does not receive entire parent history by default.

V1 executes subagents synchronously. Parallel subagents belong to the later advanced-agent phase with explicit concurrency/budget/conflict policy. When parallel mutation is eventually introduced, it must use isolated workspaces or a superseding conflict model rather than bypassing the V1 mutation-ownership rule.

## 12. Execution workspace isolation and mutation ownership

A run may execute against the user's active workspace or an isolated execution workspace (for example a Git worktree) when project/tool policy supports it. The run record identifies workspace root, base revision/branch/worktree metadata and any mutation-lease identity so paths, diffs and checkpoints are unambiguous.

V1 default: at most **one mutating run owns a physical workspace root at a time**. Read-only runs may coexist. Separate isolated worktrees count as separate roots only after canonical path/worktree identity is established.

A write/delete/Git-mutation/process operation that can modify workspace state must carry a valid workspace mutation lease/token supplied by Application and checked by Tool Runtime. Do not solve concurrency by “last writer wins”. The lease coordinates this application's mutating Runs; it does not freeze files against the user, IDEs, Git hooks or unrelated OS processes, so resource preconditions are still required.

A lease becomes unusable when its owning Run is terminal/interrupted or when Application revokes it. Do not release a mutating lease while an owned process that may still mutate the workspace is intentionally running unless that process has been transferred to an explicit managed lifetime with equivalent ownership/reconciliation semantics.

Isolation is a safety/product feature, not a way to bypass permissions. Merging/applying isolated work back to the primary workspace is a distinct user-visible mutation with conflict handling and fresh policy/precondition checks.

## 13. Context compaction interaction

Agent Core tells Context Engine what is semantically important:

- active goal;
- pending user request;
- unresolved decisions;
- current plan/changed files;
- important tool outputs;
- required identifiers.

Context Engine owns retrieval/source selection and recommends what older evidence may be omitted or compacted under budget. Prompt Runtime owns the actual compaction/summary representation and how compacted material is framed. Model-generated summaries remain derived/untrusted context, not a new trusted instruction layer.

## 14. Crash/restart and replay semantics

On restart:

- persisted completed/failed/cancelled task/run history remains inspectable;
- a run left in an active/waiting state is reconciled to `interrupted` unless a subsystem has an explicit durable reattach protocol;
- pending approvals/input requests owned by an interrupted/terminal Run are closed/staled and cannot later execute that old Run's tool call; a resumed Run re-plans/re-authorizes as needed;
- resuming creates a new run linked to the prior run and starts from persisted evidence/checkpoints;
- orphan owned child processes should be detected/cleaned where safely identifiable before mutation ownership is considered released;
- never claim a model/tool call completed without persisted terminal evidence;
- a tool dispatch with no trustworthy terminal evidence is reconciled or classified as `unknown_outcome`/interrupted according to its side-effect contract;
- never re-execute an ambiguous side effect merely because its completion event is missing.

Provider-native session/response handles may help continue transport state, but application task/run/event history remains canonical. A vendor session cannot be the only copy of conversation or execution state.

## 15. Observability

Expose useful summaries:

- task/run phase/state;
- active model/provider attempt;
- current tool;
- pending approval/input;
- files changed;
- elapsed time;
- token/cost info;
- actionable error/interruption reason.

Tracing/logging should preserve the task → run → turn → model/tool hierarchy so a failure can be reconstructed without raw chain-of-thought or secret-bearing payloads.

Do not expose private chain-of-thought as a product requirement.
