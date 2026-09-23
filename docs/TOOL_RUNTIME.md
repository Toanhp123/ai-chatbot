# Tool Runtime and Policy Core

## 1. Responsibility

Tool Runtime is the only normal path for agent-initiated local/external actions. It owns registration, schema validation, permission-request construction, execution, cancellation/timeout, normalized results, and audit events. **Policy Core** separately owns deterministic authorization evaluation.

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

## 3. Initial built-in tool families

### Filesystem

- list directory;
- read file/range;
- create file;
- apply patch;
- move/rename;
- delete (higher-risk approval).

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

### Execution

- run bounded command;
- start process;
- read process output;
- stop process.

Prefer direct process APIs over shell interpolation when a command can be represented as argv.

## 4. Path safety

Before filesystem operations:

- canonicalize path;
- resolve symlinks according to policy;
- confirm resource lies within approved workspace roots unless separately granted;
- prevent `..` traversal after normalization;
- distinguish read/write/delete scope;
- handle case-insensitive filesystems correctly.

## 5. Command safety

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

## 6. Policy evaluation

Policy Core input includes:

- actor/task/agent;
- tool/provenance;
- normalized operation risks;
- resource targets;
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

Policy decisions are deterministic and testable. Tool Runtime supplies the normalized operation/resource context plus the current grant snapshot; Policy Core returns the decision. The LLM does not author its own permission grant.

When a user approves or denies a requested scope, Application persists/updates any remembered grant according to its lifecycle rules and returns a scoped decision. Tool Runtime must then **re-evaluate the same normalized operation through Policy Core** with the updated grant snapshot before execution. A UI approval event is therefore evidence for policy evaluation, not a direct execution bypass.


## 6.1 User-facing permission profiles

The original product concept proposed useful profiles such as:

- `Read Only`;
- `Ask Before Changes`;
- `Allow Workspace Edits`;
- `Allow Safe Commands`;
- `Full Agent in Sandbox`.

Treat these as presets over the normalized permission policy, not hard-coded trust levels. `Full Agent in Sandbox` still cannot silently perform irreversible external actions or escape the configured sandbox/resources.

## 7. Tool result contract

Normalize:

- success/error;
- structured output;
- human-readable summary;
- artifacts/files created;
- output truncation metadata;
- provenance;
- retryability where known.

Large terminal/tool output should be bounded and optionally stored as an artifact/log with a smaller model-facing excerpt.

## 8. Audit

Every mutation and sensitive action records:

- task/tool call IDs;
- tool version/provenance;
- permission decision;
- affected resources;
- start/end time;
- status/error class;
- redacted arguments/result summary.

## 9. Sandbox abstraction

Execution backend interface should support local and sandboxed implementations:

```ts
interface ExecutionBackend {
  run(spec: CommandSpec, signal: AbortSignal): Promise<CommandResult>;
  start(spec: ProcessSpec, signal: AbortSignal): Promise<ProcessHandle>;
}
```

Docker may be first optional sandbox, but tool-runtime contracts must not depend on Docker-specific types.

## 10. Checkpoints

Before a meaningful multi-file mutation task:

- inspect Git status;
- avoid overwriting unrelated dirty work;
- create checkpoint metadata;
- use Git tree/commit/stash strategy only after defining how uncommitted user work is preserved;
- record changed files per task.

Never use destructive `git reset --hard` as a generic undo path without explicit protection of pre-existing work.
