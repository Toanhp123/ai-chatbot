# MCP, Product Skills, Plugins, Hooks, and Marketplace

> Scope note: every Skill/agent/plugin in this document is a **feature of the application being built**. External development capabilities are governed only by `DEVELOPMENT_TOOLING.md`.

## 1. Unifying principle

Extensibility is layered, but trust is not inherited across layers:

- **MCP** connects protocol servers exposing tools/resources/prompts and optional negotiated extensions.
- **Product Skills** are focused instruction/resource packages loaded progressively from an immutable revision activated in an explicit scope.
- **Agents** are reusable configurations of instructions/model route/tools/Skills/permissions/budgets.
- **Plugins** are versioned contribution bundles; installation is inert and does not authorize execution.
- **Marketplace** distributes metadata/packages; it is never a security authority.

All external contributions are normalized into app-owned descriptors before use. Protocol metadata, publisher claims, signatures, popularity and model-generated descriptions may inform UX, but none grants runtime permission.

## 2. Trust and lifecycle states

Keep these states separate:

1. **discovered** — metadata is visible but nothing is installed or trusted;
2. **installed** — package/config is stored and validated structurally, but executable/effectful contributions remain inert;
3. **reviewed** — source/revision/components/capability requests have been presented or policy-reviewed;
4. **activated** — a specific immutable revision contributes descriptors/instructions within a scope;
5. **authorized at runtime** — Policy Core allows a concrete normalized operation.

Activation never means blanket permission. Activation is a scoped association to a specific immutable revision, not a mutation of that revision; one revision may be active in more than one supported scope. Updating source, command, endpoint, package bytes, executable component, requested capability or canonical target creates a new revision/review surface instead of silently inheriting trust.

## 3. MCP Host ownership

`mcp-host` owns:

- server registry and local server identity;
- transport/profile adapters;
- protocol-era/version negotiation;
- authorization handoff and secret references;
- server lifecycle/health;
- capability, tool, resource, prompt and extension discovery;
- descriptor/schema normalization and cache freshness;
- MCP Task / multi-round-trip correlation;
- conversion to internal Tool/Context/Skill descriptors.

MCP Host does **not** decide local execution permission and does not promote server content into trusted instructions by itself.

## 4. MCP protocol compatibility baseline

Research baseline: `2026-07-28` plus independently versioned extensions supported by the selected SDK/profile.

For the modern protocol era:

- do not assume `initialize`, `initialized` or `Mcp-Session-Id` exists;
- requests are self-describing and protocol/client capability metadata is per request;
- `server/discover` may be used for up-front discovery but is not application identity;
- Streamable HTTP routing/version/header rules are validated by the protocol adapter;
- list/read TTL metadata is a **freshness hint**, not integrity proof;
- extension capability negotiation is explicit and version/profile aware;
- cancellation semantics are transport/profile specific;
- server/client implementation info is self-reported display/diagnostic metadata, never a trust or authorization input.

Legacy profiles may be supported only behind explicit compatibility fixtures. Do not implement deprecated Roots/Sampling/Logging as new product dependencies for the modern profile; compatibility support, if needed, stays isolated in the legacy adapter.

SDK support may lag a finalized protocol/extension. Product behavior is gated by tested capability/profile support rather than by assuming an SDK version implements every current SEP.

## 5. Stable MCP server identity

A local `mcpServerId` is app-owned. Its trust/activation revision binds to the connection definition that matters for authority:

- transport kind;
- canonical HTTP origin or executable identity;
- command/arguments/cwd for stdio;
- bounded environment/secret-reference policy;
- selected protocol/profile policy;
- source/project scope.

Server-provided names/versions do not define identity. A material connection-definition change invalidates the old activation review and produces a new revision.

## 6. Transport security

### HTTP / Streamable HTTP

- canonicalize endpoint/origin before credential resolution;
- bind credentials/tokens to the intended resource/audience/origin;
- do not forward authorization across untrusted redirects or to a different MCP resource;
- validate current MCP/OAuth issuer/resource semantics where supported;
- bound response/body/schema sizes and timeouts;
- treat loopback, LAN and remote endpoints distinctly in UI/policy;
- do not use server-supplied implementation metadata as security evidence.

### stdio

Activating a stdio server is equivalent to authorizing local process launch.

- store command and args as structured fields; do not build a shell string;
- use an explicit cwd;
- pass a minimal environment rather than inheriting all application secrets;
- inject only named secret references required by that server;
- track the child process as app-owned and terminate only processes the app actually owns;
- stdout is protocol traffic; diagnostics belong on the appropriate side channel and remain bounded/redacted.

Installing/importing an stdio definition must never spawn the process automatically.

## 7. MCP authorization

For HTTP servers that implement authorization:

- follow the active profile's OAuth/discovery requirements;
- store tokens only through `SecretStore` references;
- bind credentials to the correct issuer/resource/audience;
- request least-privilege scopes;
- bounded step-up authorization may request additional scopes, but never broadens silently;
- expiry/revocation/reauth state is explicit;
- redact auth material from context/logs/diagnostics.

MCP authorization proves access to the remote server. It does **not** replace local Tool Runtime/Policy Core authorization for effectful operations surfaced to the app.

## 8. Catalog, schema, and cache rules

Do not expose every connected MCP tool schema to every model request.

Maintain normalized catalog metadata including:

- local server/revision/provenance;
- tool/resource/prompt identity;
- title/description/tags;
- input/output schema fingerprint;
- locally classified effect/risk metadata;
- server-declared annotations retained as untrusted hints;
- health/availability;
- protocol/extension profile;
- fetched-at/TTL/cache-scope metadata.

Tool name collisions use app-owned stable IDs such as `serverRevisionId/toolName`; names are not globally unique.

Schema handling:

- validate the JSON Schema dialect/profile expected by the negotiated MCP revision;
- bound schema depth/size/validation work;
- do not automatically dereference arbitrary external `$ref` URLs;
- a schema/content fingerprint change creates a new descriptor revision and invalidates pending approvals tied to the prior revision.

Catalog TTL controls re-fetch timing only. It does not prove bytes are unchanged or trusted.

## 9. Multi-round-trip input and remote Tasks

Modern MCP may return input-required/multi-round-trip state or an extension-owned Task handle.

Rules:

- correlate remote state to the owning `toolCallId`/`toolAttemptId` without reusing app IDs;
- persist only the bounded remote handle/state required for reattach/poll/cancel;
- remote input requests are untrusted schemas/messages and must be rendered through an app-owned safe UI;
- a user's response to MCP elicitation supplies **input**, not local operation approval;
- if the resumed operation still needs local permission, Tool Runtime/Policy Core evaluates it normally;
- cancellation or terminal state remains explicit and auditable.

MCP Task is remote server execution state. Agent Task/Run is local application execution state. Never collapse them.

## 10. Product Skills

Canonical package shape:

```text
skill-name/
  SKILL.md
  references/   # optional
  scripts/      # optional resources, never auto-executed
  assets/       # optional
```

Skill metadata supports cheap discovery without loading the entire body.

Scopes:

- global;
- project;
- optionally path-scoped within a trusted project.

Activation may be explicit or relevance-based according to user configuration. Always-on Skills stay rare.

A Product Skill contributes instructions/resources only. It does not grant filesystem, shell, network, credential, MCP or plugin execution permission. A script shipped inside a Skill is merely a resource until invoked through an authorized Tool Runtime path. Security-relevant Skill revision/source provenance survives into Prompt Runtime and any causally resulting Tool Call when it can change policy.

## 11. Skills delivered over MCP

When the finalized `io.modelcontextprotocol/skills` extension is supported, MCP is a **distribution/discovery source**, not a second Skill runtime. The extension transport is versioned independently from the Product Skill runtime and must be feature-gated by tested SDK/profile support. MCP-served Skill content remains remote-origin instructional input: a connected server, successful authentication or matching digest does not make it authoritative.

V1 activation flow:

1. discover or explicitly resolve a Skill by `(mcpServerRevisionId, skillUri)`; name/URI alone is never global identity;
2. preserve the originating server identity, URI, verbatim frontmatter, complete static resource manifest, digests/sizes and cache metadata;
3. require explicit per-Skill user activation approval bound to the server revision + Skill URI + manifest/frontmatter revision; nested Skills require independent approval;
4. fetch `SKILL.md` through the Skill-loading path, verify size/digest and frontmatter against the held entry, then lazily fetch supporting files and verify each against that same held manifest;
5. create an app-owned immutable Product Skill revision/snapshot with MCP origin/trust class preserved;
6. route the revision active in that scope through Extension Core and Prompt Runtime using the MCP-origin instruction rules, never as an indistinguishable local/package Skill.

Additional V1 rules:

- same-name Skills are origin-namespaced and cannot silently shadow/replace a local Skill or a Skill from another MCP server;
- supporting/relative resource reads stay bound to the originating MCP server revision; V1 denies cross-server Skill reads rather than acting as a confused deputy;
- digest/size agreement proves consistency with the held entry, **not publisher/server trust**, because the same origin supplies both manifest and bytes;
- a held manifest defines the acting revision: an unlisted file, changed digest/size/frontmatter, or refreshed manifest invalidates the prior content-bound activation approval and creates a new review surface;
- retrieval is lazy and bounded by the negotiated/current extension contract; for the current stable Skills extension profile, support at least 512 resources and 16 MiB total file bytes per Skill, with those limits kept profile/version-aware rather than scattered as business-logic magic numbers; do not prefetch every Skill/file on connection;
- V1 does not persistently activate `dynamic`/not-content-bindable MCP Skills; they may be previewed/read only as ordinary untrusted MCP context;
- `allowed-tools`, hooks, scripts or equivalent Skill metadata are requests/hints, never host permission grants;
- Skill scripts/assets never execute during discovery, fetch, verification or activation;
- host-side shell/process/code execution causally requested while acting on an MCP Skill requires explicit user authorization scoped to that Skill revision **plus** the normal concrete Tool Runtime/Policy Core operation decision. One approval UI may satisfy both only when it names the Skill origin/revision and exact operation;
- Skill origin/revision remains visible in UI, diagnostics, Prompt Runtime provenance and causally resulting Tool Calls while the Skill is active.

## 12. Repository instructions and workspace trust

Repository-controlled instruction files such as `AGENTS.md` are only a trusted project-instruction layer when the attached workspace/root is in the app's **trusted** state or the user explicitly approves that instruction source.

In restricted/untrusted state:

- repository files can still be indexed/read as untrusted evidence;
- repository-controlled project Skills/plugins/hooks/commands are not automatically activated;
- repository settings cannot silently enable process/network/credential behavior;
- user-entered Project instructions stored by the app remain distinct from repository-supplied instructions.

Trust is scoped to the canonical workspace/root identity and is revocable. Trust admits only designated repository instruction/configuration sources defined by the product contract; it does **not** turn arbitrary README/source/issues/artifacts into trusted instructions. Trust does not bypass per-operation Tool Runtime permission.

## 13. Plugin contribution classes

A plugin manifest may describe contributions such as:

- data-only Skills/agent profiles/commands/configuration;
- MCP server definitions;
- declarative UI metadata;
- executable scripts/hooks/workers in later phases.

Conceptual manifest fields:

```json
{
  "id": "com.example.plugin",
  "name": "Example",
  "version": "1.0.0",
  "publisher": "example",
  "minAppVersion": "...",
  "permissions": [],
  "components": {
    "skills": [],
    "agents": [],
    "commands": [],
    "hooks": [],
    "mcpServers": [],
    "ui": []
  },
  "source": {},
  "integrity": {}
}
```

Validate against a versioned schema. Preserve package/revision identity and requested capabilities separately from granted runtime operations.

## 14. Executable extension policy

V1/Phase 4 is declarative/protocol-based. Arbitrary third-party JavaScript/Python/native code must **not** be dynamically imported into Electron renderer, preload, main, or core package processes.

When Phase 5 introduces executable plugin hooks/workers, use an explicit isolated extension execution boundary with a narrow versioned capability-mediated message bridge. The worker receives no ambient Electron/Node host objects, raw SQLite/SecretStore handles, inherited full environment, or blanket filesystem/network authority; requested effects flow through explicit capabilities and the normal Tool Runtime/Policy Core path where applicable. Worker crash/timeout/restart is bounded and cannot take down the desktop host. Until that boundary and sandbox/permission tests exist, executable hooks remain disabled/reserved.

Commands contributed by a plugin are descriptors that resolve to approved application use cases/tools; they are not arbitrary in-process callbacks.

## 15. Extension UI policy

Do not allow a plugin to inject arbitrary React/DOM code into the host renderer.

Supported directions are:

- host-rendered declarative metadata/components; or
- a later explicitly supported MCP Apps / equivalent sandboxed-view boundary.

If MCP Apps is supported later, treat it as progressive enhancement: sandboxed iframe/view, declarative CSP/network domains, explicit browser-capability permissions, validated `postMessage`/bridge source, and all host/tool actions mediated by app policy. An extension UI never receives direct Electron/Node/secret/storage access.

## 16. Install, update, activate, rollback

Installation:

- stage package/config through an app-owned data/archive reader, not by executing an untrusted package manager install lifecycle;
- validate manifest/schema and bound archive/file count/expanded size;
- reject absolute paths, `..` traversal, symlink/hardlink escapes or any extraction outside the staging root;
- never run package `preinstall`/`install`/`postinstall` or equivalent hooks as part of product installation;
- compute/verify integrity metadata where available;
- record source/version/revision;
- inspect contribution classes/capability requests;
- perform **no executable side effect**.

Activation:

- bind a specific immutable revision to global/project scope;
- apply workspace-trust rules;
- expose only allowed contribution descriptors;
- runtime operations still require normal policy.

Update:

- stage as a new revision;
- show permission/capability/executable/source changes;
- do not silently preserve activation when the security-relevant surface changed;
- keep enough previous metadata/package state for safe rollback when practical.

Uninstall removes activation first, then package metadata/files subject to reference/cleanup rules; it never silently deletes user artifacts.

## 17. Hooks

Potential lifecycle events include task/session/model/tool/compaction/subagent events.

Capability classes may include observe, enrich, transform and block, but:

- hooks cannot bypass Policy Core;
- hooks cannot obtain arbitrary secrets;
- transform/block hooks are more privileged than observation and require explicit review;
- executable hooks wait for the isolated extension runtime in Phase 5+;
- hook failure/timeout is bounded and cannot deadlock the main runtime.

## 18. Marketplace

Registry operations:

- browse/search/filter;
- inspect versions/source/components/permissions;
- install/update/disable/enable/uninstall.

Before activation show source/publisher, exact revision/version, capability/permission requests, executable components, MCP definitions, bundled Skills/agents, integrity/signature metadata where available, and trust warnings.

Popularity, stars, download count, publisher text and signature presence are not proof that behavior is safe.

## 19. Verification ownership

`TEST_STRATEGY.md` is the canonical owner of MCP/extension security, protocol and lifecycle tests. This document defines the subsystem contract; do not duplicate the test matrix here.
