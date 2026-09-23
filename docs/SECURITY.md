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
- user-entered Project instructions and repository instruction sources explicitly admitted by workspace trust/approval according to instruction precedence.

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

Threat: destructive commands, stale writes, concurrent agent edits, access outside workspace, persistence mechanisms, credential discovery.

Controls:

- structured tools before shell;
- classify read/write/delete/shell/network/credential/irreversible actions;
- workspace allowlists and path canonicalization;
- resource content/revision preconditions for mutations where prior state matters;
- one mutating run per physical workspace root in V1 unless explicitly isolated;
- command timeout/cancel/output caps;
- explicit scoped environment/secret injection instead of inheriting unrelated secret-bearing process state;
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

### Workspace / extension supply chain

Threat: opening an untrusted repository, installing a plugin, activating a Product Skill, or updating an extension silently elevates repository/package-controlled content into trusted instructions or executable host code.

Controls:

- workspace/root trust is explicit and revocable; restricted roots remain readable/indexable but repository-controlled instructions/config stay untrusted/inert;
- installation separate from review, activation and runtime permission;
- plugin/package staging is data-only: no package-manager lifecycle scripts, bounded extraction, and no path/symlink escape from the staging root;
- immutable package/Skill/server revision identity with source/integrity metadata;
- changed executable component, endpoint/command or requested capability creates a new review surface;
- Product Skill scripts/assets never auto-execute;
- arbitrary third-party code is not dynamically imported into Electron renderer/preload/main/core processes;
- future executable hooks/workers require an isolated capability-mediated extension boundary;
- signatures/scanners/publisher reputation improve provenance but never replace runtime policy.

### MCP confused-deputy / token leakage

Controls:

- version/profile-aware MCP implementation, including stateless modern request semantics where selected;
- preserve app-owned server/revision identity/provenance; server self-reported name/version is not trust identity;
- treat stdio activation as reviewed local process execution, with structured command/args/cwd and minimal environment;
- HTTP authorization uses resource/audience/issuer-aware flows where supported;
- least-privilege scopes and bounded step-up retry;
- never forward one server's token to another resource;
- validate Origin/server URL policy for locally hosted HTTP servers;
- treat tool annotations/results as untrusted;
- treat MCP/plugin-declared risk/effect metadata as hints, not authorization truth; unknown effect scope defaults conservative until local policy/classification narrows it;
- treat catalog TTL/cache metadata as freshness only, never integrity/trust;
- bound JSON Schema validation and do not auto-fetch arbitrary external `$ref` targets;
- treat MCP MRTR/elicitation answers as input data, never as local operation approval;
- for MCP-served Skills, preserve server origin in context, namespace identity by server revision + Skill URI, keep supporting reads origin-scoped, and treat digest/size verification as content binding rather than trust;
- activation approval for an MCP Skill is per-Skill and content-bound; changed manifest/frontmatter/digest invalidates it, nested Skills require separate approval, and dynamic/unverifiable Skill content does not receive persistent activation in V1;
- MCP Skill `allowed-tools`, hooks and scripts never grant host capability; host-side shell/process/code execution under an active MCP Skill requires explicit Skill-revision-scoped user authorization plus normal concrete operation policy;
- mediate MCP tool execution and Skill-originated host code execution through Tool Runtime + Policy Core.

### Provider-hosted capability bypass

Threat: a provider-side web/browser/code/server tool is presented as if it were an ordinary local tool even though its inner actions execute remotely and cannot be mediated per invocation by Tool Runtime.

Controls:

- distinguish application tools from provider-hosted capabilities in Provider Core;
- provider-hosted capabilities are disabled unless a product feature explicitly models them;
- require declared data/side-effect scope plus provider attribution before enabling;
- never use provider-hosted capabilities for local filesystem/shell/Git/credential mutations;
- do not imply local per-call approval guarantees when the provider executes opaque inner actions.

### Model download/execution

Threat: arbitrary remote code, unsafe model formats, poisoned model helpers.

Controls:

- prefer data-only model formats/runtimes and immutable source revisions/checksums where available;
- prefer safer data-oriented formats such as safetensors/GGUF when compatible with the selected runtime;
- do not enable arbitrary `trust_remote_code`, pickle-like unsafe loading, or repository helper execution silently;
- custom model/repository code executes only in an explicit isolated worker/runtime boundary, never inside Electron renderer/preload/main;
- surface source/license/revision/checksum/integrity metadata where available;
- distinguish loopback/LAN/remote endpoint class and external/app-managed process ownership;
- connecting a runtime never changes its bind/network exposure;
- opaque runtime/provider-hosted tools/MCP are disabled unless explicitly modeled and never inherit Tool Runtime authorization claims;
- local server authentication limitations are documented.

### Training datasets/jobs

Threat: secrets/PII in datasets, prompt/instruction injection through training data, dataset/model exfiltration, unsafe model serialization/custom code, training-process escape, inherited cloud credentials, hidden experiment trackers, path traversal, GPU/disk exhaustion and ambiguous partial checkpoints.

Controls:

- DatasetRevision/model bytes are untrusted data and never host instructions;
- local/offline compute by default with remote artifacts staged explicitly;
- external experiment tracking/upload disabled unless explicitly configured;
- worker environment receives only minimal resolved inputs and does not read app DB/SecretStore directly;
- arbitrary desktop/provider/cloud secrets are scrubbed rather than inherited by the worker;
- no arbitrary per-job package installation; model repository custom code is disabled by default and requires an explicit pinned high-risk worker/runtime path if supported, never Electron/core execution;
- explicit dataset preview/validation, split-leakage checks and basic secret scanning warnings;
- immutable TrainingPlan and backend/environment provenance before launch;
- app-owned accelerator lease prevents overlapping internal jobs on the same declared devices;
- canonicalized allowed input/output roots with traversal/symlink-escape defenses;
- hardware/disk estimates, bounded logs/checkpoint retention and cleanup;
- staged artifact/checkpoint finalization with manifest/integrity checks;
- cancellation/kill only for exact app-owned worker identity;
- no automatic cloud upload, hub publishing or model registration.

## 4. Permission model

Permission decisions are based on a normalized operation descriptor, not tool name alone. Approval is bound to the operation that was shown, not to mutable model wording.

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
  approvalRequestId: string;
  actor: { taskId: string; runId: string; agentId?: string };
  causalInstructionSources?: InstructionSourceRef[];
  tool: { id: string; version: string; provenance: string };
  operationFingerprint: string;
  risks: OperationRisk[];
  resources: ResourceDescriptor[];
  preconditions?: ResourcePrecondition[];
  summary: string;
  redactedArguments: unknown;
  expiresAt?: string;
}
```

Decision scopes may include:

- deny;
- allow once for this exact pending operation;
- allow for current task/run/session within constrained risk/resource scope;
- allow this tool/version on a constrained resource within this project.

Rules:

- never persist broad permission solely from model-generated wording;
- security-relevant instruction/extension provenance is part of grant matching; a grant scoped to one MCP Skill revision/origin cannot silently authorize another;
- a UI approval result is not an execution capability by itself; Tool Runtime must re-resolve resources/preconditions and Policy Core must re-evaluate;
- if tool version, normalized arguments, canonical target, workspace identity or required precondition changes while waiting, the pending approval becomes stale and cannot authorize the modified action;
- remembered grants are evaluated against current normalized operation data every time;
- deny/revoke/expiry semantics are explicit and auditable;
- approval records distinguish `approved` from `executed`, because execution can still fail or be blocked by a stale precondition.

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
- workspace trust/repository-controlled instruction activation;
- plugin/hook executable code or extension sandbox boundary;
- MCP server activation, auth/permissions, Skills/MCP Apps support;
- provider/runtime-hosted tools/capabilities;
- DB migration that can destroy user data;
- model download/custom code/unsafe model serialization;
- training-process launch.

Review threat surface, least privilege, rollback/failure modes, logging/redaction, cancellation, and tests.
