# Agent Runtime

## 1. Responsibility

Agent Core orchestrates model turns, context, tools, approvals, retries/fallbacks, subagents, cancellation, and task state. It must not depend on React/Electron and must not directly implement provider transports or raw shell access.

## 2. Task model

Minimum state machine:

```text
queued
  -> planning
  -> running
  -> waiting_for_approval
  -> running
  -> completed
  -> failed
  -> cancelled
  -> blocked
```

`blocked` means progress requires external/user action that is not represented as an immediate tool approval. Keep terminal states immutable.

## 3. Task snapshot

Conceptual type:

```ts
interface AgentTask {
  id: string;
  parentTaskId?: string;
  state: TaskState;
  projectId?: string;
  conversationId?: string;
  agentConfigId?: string;
  routeId: string;
  activeModel?: ModelRef;
  iteration: number;
  maxIterations: number;
  budget?: TaskBudget;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}
```

Persist enough state/events to explain what happened and recover UI after restart. Do not attempt to transparently resume arbitrary in-flight external calls after crash in V1.

## 4. Runtime loop

1. Validate task request and effective policy.
2. Resolve agent configuration and route.
3. Ask Context Engine for a bounded context package.
4. Start provider request with cancellation token.
5. Convert provider deltas/tool requests/usage/errors into normalized events.
6. If tools are requested, validate call + invoke through Tool Runtime.
7. If approval required, suspend task and emit `approval.required`.
8. Feed normalized tool results back through provider adapter.
9. Repeat within iteration/time/cost/tool-call budgets.
10. Complete, fail, block, or cancel explicitly.

## 5. Normalized runtime events

Use stable event categories rather than copying provider stream event names:

```text
task.created
task.state_changed
model.request_started
message.started
message.text_delta
message.completed
tool.requested
tool.started
tool.progress
tool.completed
tool.failed
approval.required
approval.resolved
usage.updated
artifact.created
checkpoint.created
context.compacted
task.completed
task.failed
task.cancelled
```

Events should include task ID, monotonic sequence, timestamp, and typed payload.

## 6. Cancellation

Cancellation is first-class.

A cancellation request should propagate, where supported, to:

- provider stream/request;
- local tool invocation;
- spawned process;
- MCP request/stream;
- subagent;
- browser/sandbox task;
- Model Lab job only when task explicitly owns it.

Use cooperative cancellation plus hard termination for bounded child processes when necessary. Cancellation is not an error unless a subsystem fails to stop within policy.

## 7. Retry vs fallback

Keep separate:

- **retry**: same logical model/provider attempt under bounded transient-failure policy;
- **fallback**: switch to the next eligible route candidate.

Do not blindly retry non-idempotent tool calls. Model request retries must not duplicate already-committed side effects.

## 8. Tool loop safety

- Validate tool identity and schema.
- Resolve the current tool catalog snapshot, not model-invented tools.
- Enforce max tool calls/iteration budget.
- Avoid recursive agent/tool loops without a hard bound.
- Tool result content is untrusted context.
- Large output is summarized/truncated/file-backed with provenance instead of pushed whole into next model request.

## 9. Custom agents

Agent definitions are data/configuration:

- name/description;
- system instructions;
- preferred route;
- allowed tools;
- allowed MCP servers;
- Skills;
- permission profile;
- maximum iterations;
- optional token/cost/time budget.

Do not create subclasses such as `SecurityReviewerAgent` in core unless behavior genuinely differs at runtime-contract level.

## 10. Subagents

A subagent receives:

- one explicit task;
- selected context bundle;
- selected tools;
- model/route;
- budget;
- parent correlation ID.

It does not receive entire parent history by default.

V1 can execute subagents synchronously. Parallel/background work belongs to a later phase with explicit concurrency and conflict policy.

## 11. Execution workspace isolation

A task may execute against the user's active workspace or an isolated execution workspace (for example a Git worktree) when the project/tool policy supports it. The task record must identify the workspace root/branch/base revision so tool paths, diffs and checkpoints are unambiguous.

Isolation is a safety/product feature, not a way to bypass permissions: the same Tool Runtime + Policy Core path still mediates filesystem, process, network and destructive operations. Merging/applying isolated work back to the primary workspace is a distinct user-visible operation with conflict handling.

## 12. Context compaction interaction

Agent Core tells Context Engine what is semantically important:

- active goal;
- pending user request;
- unresolved decisions;
- current plan/changed files;
- important tool outputs;
- required identifiers.

Context Engine owns how older content is summarized/evicted under budget.

## 13. Crash/restart semantics

On restart:

- persisted completed/failed/cancelled tasks remain inspectable;
- tasks left `running` are reconciled to an interrupted/failed state unless a subsystem has an explicit reattach protocol;
- orphan child processes should be detected/cleaned where safely identifiable;
- never claim a model/tool call completed without persisted evidence.

## 14. Observability

Expose useful summaries:

- phase/state;
- active model;
- current tool;
- pending approval;
- files changed;
- elapsed time;
- token/cost info;
- actionable error.

Do not expose private chain-of-thought as a product requirement.
