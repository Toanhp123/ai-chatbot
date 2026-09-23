# Security Model

## 1. Security objective

The application intentionally combines model output with local files, shell commands, network services, credentials, plugins, MCP tools, and later model execution/training. Therefore the default threat model assumes **models and external content can be wrong or malicious**.

Autonomy is granted through scoped capabilities, never through implicit trust.

## 2. Trust boundaries

### Trusted policy plane

- platform/system sandbox rules;
- app **Policy Core** plus Tool Runtime enforcement path;
- signed/shipped application code;
- user decisions;
- explicit repository `AGENTS.md`/approved local instructions according to instruction precedence.

### Untrusted or conditionally trusted data

- model output;
- web pages/search results;
- repository content outside trusted instruction mechanisms;
- attachments/documents;
- MCP tool/resource/prompt content;
- plugin/marketplace metadata and executable payloads;
- training datasets;
- downloaded models/custom model code;
- terminal output;
- provider responses.

Untrusted text cannot grant itself authority.

## 3. Threats to address

### Prompt injection / instruction smuggling

Threat: external content asks the model to ignore policy, exfiltrate secrets, or invoke tools.

Controls:

- explicit instruction hierarchy;
- mark provenance for retrieved/tool/MCP content;
- do not concatenate external content into privileged system instructions;
- permission checks occur outside model reasoning;
- secrets are not automatically included in model context;
- tool arguments are validated independently of model output.

### Shell / filesystem damage

Threat: destructive commands, access outside workspace, persistence mechanisms, credential discovery.

Controls:

- structured tools before shell;
- classify read/write/delete/shell/network/credential/irreversible actions;
- workspace allowlists and path canonicalization;
- command timeout/cancel/output caps;
- explicit approval for dangerous operations;
- optional sandbox execution profile;
- audit records.

### Credential leakage

Threat: secrets leak through DB, prompts, logs, crash reports, extensions, MCP, or copied diagnostics.

Controls:

- `SecretStore` abstraction;
- DB stores `secretRef`, not plaintext;
- redact values and known secret-bearing headers;
- never log provider authorization headers;
- diagnostic export uses a redaction pass;
- secrets are only resolved immediately before a trusted transport/execution boundary.

### Electron renderer compromise

Controls aligned with current Electron guidance:

- context isolation;
- renderer sandbox;
- no Node integration for untrusted/remote content;
- restrictive CSP;
- narrow typed preload surface;
- validate IPC sender and message schema;
- restrict navigation/new windows;
- never blindly open untrusted external URLs;
- avoid privileged `webview` patterns unless separately reviewed.

### Plugin / hook supply chain

Threat: installed plugin executes malicious code or requests excessive authority.

Controls:

- installation separate from activation;
- manifest declared components and permissions;
- display source/version/checksum/signature metadata where available;
- executable hooks are high-risk capabilities;
- scoped filesystem/network/tool access;
- future signature/scanning hooks without pretending signatures alone imply safety.

### MCP confused-deputy / token leakage

Controls:

- version-aware MCP implementation;
- preserve server identity/provenance;
- HTTP authorization uses resource/audience-aware flows where supported;
- least-privilege scopes and bounded step-up retry;
- never forward one server's token to another resource;
- validate Origin/server URL policy for locally hosted HTTP servers;
- treat tool annotations/results as untrusted;
- mediate MCP tool execution through Tool Runtime + Policy Core.

### Model download/execution

Threat: arbitrary remote code, unsafe model formats, poisoned model helpers.

Controls:

- prefer data-only model formats/runtimes;
- do not enable arbitrary `trust_remote_code` silently;
- surface source/license/checksum when available;
- isolate runtime processes;
- network exposure is explicit;
- local server authentication limitations are documented.

### Training datasets/jobs

Threat: secrets/PII in datasets, dataset exfiltration, training process escape, disk exhaustion.

Controls:

- local by default;
- explicit path/data preview and validation;
- basic secret scanning warnings;
- isolated Python environment;
- hardware/disk estimation;
- cancellation/quotas;
- output path validation;
- no automatic cloud upload.

## 4. Permission model

Permission decisions are based on a normalized operation descriptor, not tool name alone.

Conceptual fields:

```ts
type OperationRisk =
  | 'read'
  | 'write'
  | 'delete'
  | 'shell'
  | 'network'
  | 'credential'
  | 'external-service'
  | 'irreversible';

interface PermissionRequest {
  actor: { taskId: string; agentId?: string };
  toolId: string;
  risks: OperationRisk[];
  resources: ResourceDescriptor[];
  summary: string;
  redactedArguments: unknown;
}
```

Decision scopes may include:

- deny;
- allow once;
- allow for current task/session;
- allow this tool on a constrained resource within this project.

Never persist broad permission solely from model-generated wording.

## 5. Secret storage

Use an app-level abstraction with statuses such as:

- `protected`;
- `temporarily-unavailable`;
- `degraded`;
- `unsupported`.

Electron `safeStorage` can back the initial desktop implementation, but Linux backend quality must be checked. If selected backend indicates weak/plaintext behavior, do not describe the credential as securely OS-protected.

## 6. IPC security

- Define explicit request/response schemas.
- Validate sender frame/origin/window identity.
- Do not expose generic `ipcRenderer.send` to web content.
- Do not pass arbitrary method names from renderer to main.
- Perform authorization in main/service layer even if UI has already hidden/disabled a control.

## 7. Network security

- HTTPS/WSS for remote endpoints unless user explicitly configures a local/insecure development endpoint.
- Keep “allow insecure endpoint” explicit and per-provider.
- Apply redirect policy; do not send authorization headers across untrusted redirects.
- Enforce request timeouts, body limits, and reasonable retry budgets.
- Proxy settings must not silently route credentials through unknown intermediaries.

## 8. Sandbox profile

Sandbox execution is optional for ordinary chat but should be pluggable for agent commands.

A sandbox profile can constrain:

- mounts and read/write mode;
- network enabled/disabled or allowlist;
- CPU/memory/process limits;
- wall-clock timeout;
- environment variables;
- secret injection;
- persistence/disposability.

“Full Agent in Sandbox” still means permissions inside a constrained environment, not unrestricted host root access.

## 9. Logging / diagnostics

Never record raw secrets. Define a redaction layer before durable log sinks. Raw provider request/response inspection in developer mode must exclude authorization material and should be opt-in.

Audit events for mutating/sensitive actions should capture:

- actor/task/tool;
- operation class;
- resource target;
- permission decision/source;
- start/end/result;
- redacted arguments;
- correlation IDs.

## 10. High-risk review checklist

Require a second security review for changes involving:

- authentication or token handling;
- credential storage;
- shell/sandbox/filesystem deletion;
- updater/release signing;
- plugin/hook executable code;
- MCP auth/permissions;
- DB migration that can destroy user data;
- model download/custom code;
- training-process launch.

Review threat surface, least privilege, rollback/failure modes, logging/redaction, cancellation, and tests.
