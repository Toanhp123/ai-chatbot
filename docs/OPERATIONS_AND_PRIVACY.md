# Operations, Privacy, Recovery and Distribution

## 1. Purpose

Desktop AI applications handle credentials, private conversations, source repositories, large model files and long-running processes. Operational behavior must therefore be designed as a product subsystem rather than left to packaging time.

## 2. Data classes

Keep data classes distinguishable:

- product DB: conversations, projects, settings, agent metadata, usage and references;
- secret store: API keys/tokens/credentials;
- rebuildable caches/indexes: repository maps, embeddings, thumbnails, extracted text caches;
- logs/audit events;
- user artifacts/exports;
- downloaded local models;
- Model Lab datasets/checkpoints/adapters/metrics;
- extension/MCP metadata and installed packages.

Each class needs an explicit location/lifecycle/cleanup policy. Avoid a single opaque app-data directory whose contents cannot be explained or migrated.

## 3. Profiles and test isolation

Runtime configuration should support an explicit profile/data root so development, E2E tests and production do not share data. E2E uses temporary isolated profiles and must not read real secrets/configuration accidentally.

Profile switching is not required in V1 UI, but the lower-level path abstraction must make isolation possible.

## 4. Backup and export

Provide a versioned export format when the corresponding features mature. Separate portable data from machine-bound secrets/caches.

Default exports should not include secret values. If users explicitly export sensitive material later, require clear confirmation and encryption/secure handling rather than silently packing secrets into a ZIP.

Backups should preserve schema/version metadata and use SQLite-safe snapshot/backup behavior rather than copying a live DB unsafely.

## 5. Import and migration

Validate import manifests before writing. Treat imported Markdown/config/extensions/project metadata as untrusted input. Import into a staging/temp location when practical, then commit after validation.

Persistent schema upgrades must be transactional/recoverable where possible, versioned, tested against representative previous versions, and capable of producing actionable recovery guidance if migration fails.

## 6. Crash recovery

On startup distinguish clean shutdown from interrupted work when useful. Long-running task state must not be resurrected blindly after a process crash: reconcile persisted task records with provider/process/tool reality and move unrecoverable in-flight operations into an interrupted/failed state with safe diagnostics.

Use atomic/temp-file replacement for important file-based config and artifact metadata. Avoid partially written configuration.

## 7. Updates and release channel

Application updates are security-sensitive code installation. Verify package/signature mechanisms supported by the chosen platform/distribution path, use HTTPS, separate update metadata from arbitrary web content, and do not grant downloaded extensions the same trust as signed app updates.

Support at least stable development vs production update behavior. A later product may add channels, but Phase 0 should keep update integration behind a service boundary rather than coupled to renderer UI.

## 8. Telemetry and diagnostics

Default product operation must remain useful without mandatory analytics. Any telemetry added later should be explicit, minimal and documented. Do not send conversation content, repository content, prompts, tool output, filenames, credentials or training data merely for analytics.

Crash/diagnostic reports must pass redaction. Prefer coarse event/counter metadata and user-triggered support bundles.

A support bundle should be previewable and contain only safe diagnostics such as application/version/platform info, redacted logs, configuration shape without secret values, migration status and correlation IDs. Never silently attach source files/conversation bodies.

## 9. Network transparency

Remote network activity should be attributable to a provider, MCP server, extension, web-research feature, updater or model download. Permission/policy layers should make sensitive/unexpected destinations reviewable where practical.

Local-first does not mean offline-only; it means local ownership/default storage plus explicit remote boundaries.

## 10. Local models and storage pressure

Model downloads and checkpoints can be very large. Track expected/actual size, destination, partial download state, checksum/version metadata when available, resumability and cleanup. Warn before operations that can materially consume disk space.

Deleting a model/checkpoint is destructive and should verify references/jobs before removal. Do not conflate deleting registry metadata with deleting files.

## 11. Privacy controls

Users should be able to understand and eventually control:

- which provider receives a request;
- whether a route permits cloud fallback;
- what project/file context was attached;
- which memories are active;
- which MCP/extensions have access;
- what diagnostic data can leave the machine;
- whether local model/training data leaves the machine (default: no unless explicitly configured).

Privacy-relevant choices belong in runtime policy/data, not only a settings label.

## 12. Uninstall/reset

Treat “reset app state”, “remove caches/indexes”, “remove downloaded models” and “delete user data” as separate operations. Never make cache clearing destroy source files, user artifacts or training datasets.

Document platform-specific app-data locations once packaging is implemented.

## 13. Tests

Test at least:

- profile isolation;
- safe DB migration from representative prior schemas;
- failed migration/recovery path;
- export excludes secrets by default;
- import rejects malformed/unsupported versions;
- redaction/support bundle behavior;
- interrupted task reconciliation;
- model/download cleanup boundaries when those phases arrive.
