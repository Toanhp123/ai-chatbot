# Tool Runtime and Policy Core

## 1. Responsibility

Tool Runtime is the only normal path for agent-initiated local/external actions. It owns registration, schema validation, normalized-operation construction, permission-request construction, execution, cancellation/timeout, normalized results, side-effect identity/preconditions, managed process lifecycle and audit events. **Policy Core** separately owns deterministic authorization evaluation.

Provider adapters, MCP clients, plugins, and agents may **describe/request** tools; they do not get to bypass Tool Runtime.

## 2. Tool contract

Conceptual interface:

```ts
interface ToolDefinition<I, O> {
  id: string;
  version: string;
  title: string;
  description: string;
  inputSchema: JsonSchema;
  risk: ToolRiskDescriptor;
  provenance: ToolProvenance;
  execute(ctx: ToolExecutionContext, input: I): Promise<ToolResult<O>>;
}
```

Internal schemas may be richer than any provider schema. Provider Core maps the supported subset into provider-specific tool definitions.

Tool identity is `(id, version, provenance)`. A tool implementation/manifest change that can change operation semantics must change version/fingerprint so historical approvals/audit records are not accidentally reused for different code.

## 3. Invocation identity and operation normalization

A model/tool request first becomes a normalized invocation before permission evaluation or execution:

```ts
interface NormalizedToolInvocation {
  toolCallId: string;
  toolId: string;
  toolVersion: string;
  input: unknown;
  operation: OperationDescriptor;
  operationFingerprint: string;
  causalInstructionSources?: InstructionSourceRef[];
  preconditions?: ResourcePrecondition[];
  workspaceLeaseId?: string;
}
```

`operationFingerprint` covers the normalized effect-bearing semantics relevant to approval: tool/version, canonical target resources, normalized redacted argument shape/argument hash where safe, risk classes, workspace identity and required preconditions. Security-relevant causal instruction provenance (for example an active MCP-origin Skill revision when that changes policy) is separately bound to the permission request/grant scope rather than hidden in display text. It excludes volatile display text and secrets.

When an argument contains a secret, fingerprint the stable secret reference/declared capability rather than the secret value itself. The fingerprint is a correlation/safety value, not a cryptographic authorization token. Policy Core receives the normalized operation plus security-relevant causal provenance; it does not parse arbitrary model prose to determine what is allowed.

## 4. Initial built-in tool families

### Filesystem

- list directory;
- read file/range;
- create file;
- apply patch;
- move/rename;
- delete (higher-risk approval).

Mutating file tools should accept expected-content hash/version or equivalent preconditions when operating on previously read state. A stale precondition produces a conflict result instead of overwriting newer content.

### Search

- find files;
- grep/text search;
- symbol search;
- definition/reference/diagnostics when code-intelligence adapter supports them.

### Git

Read operations first:

- status;
- diff;
- log;
- show.

Mutations later with permission:

- create branch;
- stage;
- commit.

Push/force-push/publish remain high risk and not part of ordinary V1 autonomous flow.

Git mutations carry expected repository/worktree identity and, where semantics depend on it, expected base/head revision.

### Execution

- run bounded command;
- start managed process;
- read managed process output;
- stop managed process.

Prefer direct process APIs over shell interpolation when a command can be represented as argv.

## 5. Path and resource safety

Before filesystem operations:

- canonicalize path;
- resolve symlinks according to policy;
- confirm resource lies within approved workspace roots unless separately granted;
- prevent `..` traversal after normalization;
- distinguish read/write/delete scope;
- handle case-insensitive filesystems correctly;
- bind mutating operations to the canonical workspace/worktree identity;
- validate applicable content/revision preconditions immediately before mutation.

An approval for `/workspace/a.ts` must not become approval for whatever a changed symlink later points to. Canonical target/resource identity is part of re-evaluation.

Precondition checks reduce stale-write risk but are not a magical filesystem transaction against unrelated editors/processes. Mutating adapters should re-check as close as practical to commit, write through safe temp/atomic-replace patterns where semantics permit, and record the resulting hash/revision so a post-write race can be detected/reconciled rather than silently assumed away.

## 6. Command/process safety

Classify commands by parsed executable/arguments and requested resources where practical. Do not rely only on regex blacklists.

Potentially sensitive classes:

- recursive delete;
- privilege escalation;
- package publish;
- Git force push;
- credential/keychain access;
- network download/pipe-to-shell;
- system service changes;
- commands outside workspace;
- arbitrary interpreter execution.

A sandbox can reduce risk but does not make irreversible external actions safe.

Command specs explicitly include executable/argv, canonical cwd, timeout, environment policy, declared effect scope (read-only/workspace-write/external-write/unknown), and network/sandbox requirements. Do not inherit the entire parent process environment by default into agent-started commands when it may contain unrelated secrets. Secret injection is explicit and scoped.

Unknown or arbitrary interpreter/shell commands default to the more conservative effect/risk scope; never infer “read-only” merely because the model says the command is safe.

Long-lived/background processes are **managed resources**, not fire-and-forget shell detaches. A started process receives a process handle with owning run/tool call, PID/process-generation identity where available, bounded logs and cleanup/cancellation policy. Unmanaged `nohup`/background escape is not the normal V1 path.

## 7. Policy evaluation and approval binding

Policy Core input includes:

- actor/task/run/agent;
- security-relevant causal instruction provenance (active Product Skill revision/origin where applicable);
- tool/version/provenance;
- normalized operation risks;
- canonical resource targets;
- operation fingerprint;
- resource/workspace preconditions where applicable;
- project/session policy;
- current remembered/scoped grant snapshot supplied by Application/Storage;
- sandbox profile;
- redacted arguments.

Output:

```text
allow
allow-with-audit
require-user-approval
deny
```

Policy decisions are deterministic and testable. Tool Runtime supplies normalized operation/resource context plus the current grant snapshot; Policy Core returns the decision. The LLM does not author its own permission grant.

When a Tool Call is causally produced while an MCP-origin Skill is active, preserve that Skill revision/origin in the invocation. Shell/process/code-execution authorization requires an explicit user grant scoped to that MCP Skill revision in addition to concrete operation policy; MCP Skill `allowed-tools` cannot satisfy this requirement.

If approval is required, the pending request records a unique `approvalRequestId`, the `toolCallId`, operation fingerprint, canonical resource summary, risk classes, preconditions and expiry/lifecycle metadata.

When the user approves/denies:

1. Application records the decision and updates any remembered scoped grant according to lifecycle rules;
2. Tool Runtime reloads the current grant snapshot;
3. Tool Runtime re-resolves the current canonical targets and **checks the originally bound expected preconditions against current resource state**; it does not rewrite expected hashes/revisions to make them pass;
4. Tool Runtime recomputes/compares the operation fingerprint from the bound normalized semantics;
5. Policy Core re-evaluates that same operation with the updated grant/current resource facts;
6. execution proceeds only if the operation identity still matches, required preconditions hold, the owning Run is still eligible, and policy returns allow.

If tool version, arguments, canonical target, workspace identity or bound expected precondition semantics changed while waiting, or if the owning Run became terminal/interrupted, the old pending approval is stale. Do not “adjust” the call under the existing `approvalRequestId`; create a new normalized invocation in the active Run and evaluate it from scratch. An already-valid broader remembered grant may allow that new operation, otherwise issue a new approval request.

### 7.1 User-facing permission profiles

Useful profiles may include:

- `Read Only`;
- `Ask Before Changes`;
- `Allow Workspace Edits`;
- `Allow Safe Commands`;
- `Full Agent in Sandbox`.

Treat these as presets over normalized permission policy, not hard-coded trust levels. `Full Agent in Sandbox` still cannot silently perform irreversible external actions or escape configured sandbox/resources.

## 8. Side-effect and retry semantics

Tool Runtime does not promise magical exactly-once execution across arbitrary OS/network failures. It makes ambiguity explicit.

Classify invocation semantics where possible:

- pure/read-only and safely retryable;
- idempotent mutation when the target/API provides an idempotency/precondition mechanism;
- non-idempotent/irreversible mutation.

A `toolCallId` is the logical invocation. Every concrete dispatch/retry gets a distinct `toolAttemptId` with start/dispatch/terminal evidence. Persist a dispatch-intent marker before crossing an external side-effect boundary; once such an attempt may have been dispatched, absence of a success event is not proof of failure.

Rules:

- Agent Core may not generate a fresh `toolCallId` just to replay an ambiguous side effect;
- safely retryable reads may be retried under bounded policy with a new `toolAttemptId`;
- idempotent mutations may retry only with the same stable logical `toolCallId`, idempotency key and bound preconditions where supported;
- non-idempotent mutations are not automatically retried after timeout/crash/cancellation once dispatch may have occurred;
- cancellation after dispatch means “stop further work if possible”, not “the effect was rolled back”; terminal state may still be success, failure or unknown outcome based on observed evidence;
- after an ambiguous dispatch, attempt bounded **reconciliation** only when the target exposes trustworthy postconditions/status/idempotency lookup (for example resulting file hash, process identity, remote request key, or API operation status); reconciliation is observation, not replay;
- if reconciliation cannot prove success/failure, the invocation becomes a typed `unknown_outcome`/interrupted result requiring inspection, never fabricated success/failure.

External APIs that support idempotency keys should derive/use a stable key scoped to the logical tool call without leaking internal secrets.

### 8.1 Parallel tool calls

A provider/model may request multiple tool calls in one turn. That is a request shape, not permission to execute all effects concurrently.

V1 rules:

- each call receives its own `toolCallId`, normalized operation, policy decision and audit record;
- independent read-only calls may run concurrently under bounded concurrency;
- workspace/external mutations are serialized by default unless the executor can prove disjoint resources plus an explicit concurrency contract;
- two calls may not bypass the workspace mutation lease by being emitted in one provider batch;
- result correlation uses `toolCallId`; do not depend on completion order matching provider request order;
- if one call is denied/blocked/fails, define the remaining-call policy explicitly rather than implicitly cancelling or continuing all siblings.

## 9. Tool result contract

Normalize:

- success/error/unknown outcome;
- structured output;
- human-readable summary;
- artifacts/files created;
- output truncation metadata;
- provenance;
- retryability/idempotency classification where known;
- postconditions such as resulting file hash/revision when useful.

Large terminal/tool output is bounded and optionally stored as an artifact/log with a smaller model-facing excerpt. Tool result content is untrusted model context even when the tool itself is trusted.

## 10. Audit

Every mutation and sensitive action records:

- task/run/turn/tool call ID plus concrete `toolAttemptId` when execution was dispatched;
- causal Product Skill/extension revision provenance when policy-relevant;
- tool version/provenance;
- operation fingerprint;
- permission decision/approval request ID;
- affected canonical resources;
- precondition/resulting-version summary;
- start/end time;
- status/error/unknown-outcome class;
- redacted arguments/result summary.

Audit records must distinguish “permission granted” from “execution completed”.

## 11. Sandbox abstraction

Execution backend interface should support local and sandboxed implementations:

```ts
interface ExecutionBackend {
  run(spec: CommandSpec, signal: AbortSignal): Promise<CommandResult>;
  start(spec: ProcessSpec, signal: AbortSignal): Promise<ProcessHandle>;
}
```

Docker may be first optional sandbox, but Tool Runtime contracts must not depend on Docker-specific types.

## 12. Checkpoints and workspace mutation lease

Before a meaningful multi-file mutation task:

- inspect Git/workspace status;
- avoid overwriting unrelated dirty work;
- create checkpoint metadata;
- use Git tree/commit/stash strategy only after defining how uncommitted user work is preserved;
- record changed files per task/run.

V1 allows only one mutating run to own a physical workspace root at a time unless work occurs in explicitly isolated worktrees/roots. Application issues the workspace mutation lease; Tool Runtime requires it for workspace mutations. The lease is not permission by itself and never bypasses Policy Core. It coordinates application Runs only; external editors/processes can still race, so content/revision preconditions and post-write evidence remain necessary.

If multiple application processes can mutate the same profile/workspace, lease acquisition/revocation must use one atomic shared owner/fencing mechanism; otherwise V1 must enforce a single mutation coordinator process. A stale process/Run must not continue mutating merely because it still holds an old in-memory token.

Never use destructive `git reset --hard` as a generic undo path without explicit protection of pre-existing work.
