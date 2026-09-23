# Data Model

## 1. Principles

- SQLite is local application state, accessed through the storage layer.
- Use migrations from day one.
- Core relational state should be explicit; JSON is reserved for extensible metadata where schema churn is expected.
- Credentials are never stored as plaintext in ordinary tables.
- High-volume append-only event data should have retention/compaction policy.
- Rebuildable indexes/caches are distinguishable from user-authored durable state.

## 2. Identity and IDs

Use stable opaque application IDs (UUID/ULID or similarly collision-safe identifiers) for durable entities. Provider IDs/model IDs remain external identifiers and are not primary keys.

All major rows should include timestamps and, where useful, a schema/version field for extensible payloads.

## 3. Core entities

### Providers

`providers`

- `id`
- `display_name`
- `protocol`
- `base_url`
- `auth_strategy`
- `secret_ref` nullable
- `config_json`
- `enabled`
- `created_at`, `updated_at`

`provider_models`

- provider-local model ID;
- display metadata;
- capability snapshot;
- source (`discovered`, `preset`, `manual`);
- user override metadata;
- last seen / health metadata.

`routes` / `route_candidates`

Ordered deterministic candidate list plus route policy.

### Conversations

`conversations`

- project association optional;
- title/status;
- default route/model;
- timestamps.

`messages`

- conversation ID;
- logical role/type;
- sequence/order;
- normalized content metadata;
- provider request correlation if applicable.

Large/binary attachment payloads should be file-backed with metadata references rather than arbitrary DB blobs unless measured otherwise.

`message_parts` may be used when content-part queries/versioning require normalization; do not introduce it until needed.

### Attachments and artifacts

`attachments`

- original file metadata;
- content hash;
- extraction status/version;
- cached extracted representation reference.

`artifacts` / `artifact_versions`

- type/title/project/conversation/task origin;
- versioned content/path;
- export metadata.

### Projects/workspaces

`projects`

- title/description/instructions;
- preferred route;
- settings.

`workspaces`

- project association (a project may own multiple workspace roots);
- canonical path;
- Git metadata cache;
- trust/index status.

### Tasks / events / tools

`tasks`

- parent task optional;
- project/conversation;
- agent configuration snapshot;
- execution workspace/root reference, optional base revision/branch/worktree metadata;
- state;
- route/model;
- budget/deadline fields;
- timestamps/cancellation.

`task_events`

Append-oriented typed events with sequence numbers and bounded payloads.

`tool_calls`

- task/event correlation;
- tool ID/version/provenance;
- normalized arguments (redacted as needed);
- status/timestamps;
- result summary/error reference;
- permission decision ID.

`approvals`

- normalized permission request;
- decision/scope;
- user/policy source;
- expiry/session scope.

### Context/indexes

`repository_indexes`

- workspace;
- index version;
- parser/indexer version;
- root hash/scan metadata;
- status/error.

Detailed symbol/search indexes may live in dedicated SQLite tables or sidecar storage depending on measured access patterns.

### Extensions

`skills`

Metadata, source, scope, enabled state, content/version fingerprint.

`plugins`

Manifest/source/version/install/activation/trust metadata.

`mcp_servers`

Transport config, protocol profile, auth secret reference, enabled state, health metadata. Tool catalogs may be cached with TTL/version hash but remain server-derived untrusted metadata.

`agents`

Configurable agent profile: instructions reference, route, tool allowlist, MCP/Skill associations, permission profile, iteration/budget limits.

### Memory

`memories`

- scope global/project;
- content;
- source/provenance;
- enabled;
- timestamps;
- optional confidence/metadata.

Memory mutations should be explicit and auditable.

### Usage

`usage_records`

- request/task/conversation/project associations;
- provider/model/route;
- token categories when available;
- latency/TTFT;
- cost/currency/source;
- raw provider usage metadata only if bounded and non-sensitive.

### Checkpoints

`checkpoints`

- task/workspace;
- Git commit/tree/stash/reference where applicable;
- app-managed backup metadata where needed;
- changed files summary;
- restore status.

### Local models

`local_runtimes`

- runtime type/base URL/process metadata;
- health/auth config reference.

`local_models`

- runtime/external ID;
- architecture/quantization/size/context/capabilities;
- location/source/license metadata where known;
- fit estimates cache.

### Model Lab

`datasets`

- local source path/hash;
- canonical format/version;
- stats/validation status;
- split metadata.

`training_jobs`

- backend;
- base model;
- dataset;
- immutable resolved config snapshot;
- status/process metadata;
- hardware snapshot;
- output path;
- timestamps.

`training_metrics`, `checkpoints`, `evaluations` or artifact-linked equivalents store structured progress/results without placing huge training logs in one JSON cell.

## 4. SQLite behavior

Evaluate WAL in Phase 0. Expected desktop pattern:

- one storage service owns migration lifecycle and write coordination;
- short transactions;
- background readers permitted;
- checkpoint behavior monitored;
- graceful shutdown closes connections;
- DB remains on local filesystem.

Do not place the primary DB on network-mounted storage and assume WAL semantics are safe.

## 5. Migrations

Each schema change:

- has an ordered reproducible migration;
- runs transactionally where SQLite permits;
- includes forward data transformation;
- has backup/restore strategy for destructive transformations;
- is integration-tested from at least the previous supported schema version;
- updates this document when conceptual ownership changes.

Avoid manual “fix production DB” instructions as the intended migration mechanism.

## 6. Retention

Potentially high-volume data requiring policy:

- task events;
- tool output/log excerpts;
- provider diagnostics;
- repository indexes;
- training logs;
- artifact versions.

Retention should be configurable later but defaults must prevent unbounded local growth.
