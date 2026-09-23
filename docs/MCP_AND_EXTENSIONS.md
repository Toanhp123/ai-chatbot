# MCP, Skills, Plugins, Hooks, and Marketplace

> Scope note: every Skill/agent/plugin in this document is a **feature of the application being built**. It is unrelated to the external development capabilities used by Antigravity while implementing this repository (Superpowers, `ui-ux-pro-max`, Graphify, and optional refinement Skills). See `DEVELOPMENT_TOOLING.md`.


## 1. Unifying principle

Extensibility is layered:

- **MCP** connects remote/local protocol servers exposing tools/resources/prompts.
- **Skills** are focused instruction/resource packages loaded progressively.
- **Agents** are reusable configurations of instructions/model/tools/Skills/permissions.
- **Plugins** are installable bundles that may contain Skills, agents, commands, hooks, MCP definitions, and optional UI metadata.
- **Marketplace** distributes metadata/packages; it is not a security authority.

## 2. MCP architecture

### Internal components

- server registry;
- transport adapters;
- protocol-version compatibility profiles;
- authorization coordinator;
- capability/tool/resource/prompt catalog;
- health/log state;
- internal descriptor mapper;
- permission/provenance bridge to Tool Runtime.

### Transports

Support:

- stdio;
- current Streamable HTTP;
- legacy HTTP compatibility only if ecosystem need justifies tested support.

Do not mix transport mechanics with tool semantics.

## 3. MCP protocol compatibility

Research baseline: `2026-07-28`.

Current Streamable HTTP differs materially from 2025-era revisions. Therefore:

- do not hard-code one handshake/session assumption;
- associate every connection/profile with protocol revision/capability metadata;
- test compatibility matrices with fixtures/servers;
- prefer current per-request POST semantics for new HTTP integrations;
- cancellation behavior depends on transport/profile;
- protocol downgrade must be explicit/observable.

## 3.1 Current extension model

The `2026-07-28` generation also formalizes an extension mechanism. Treat extensions as explicitly negotiated capabilities, not as assumptions attached to every MCP server.

In particular, the Tasks extension can represent long-running server work with durable task handles and polling/cancellation semantics. This is useful for future integrations, but it must remain distinct from the app's own `AgentTask` model:

- MCP Task = protocol/server execution state;
- app AgentTask = user-visible orchestration state owned by this application.

An adapter may correlate the two, but must not collapse them into one persistence model. V1 does not require Tasks support unless a selected SDK/server dependency makes it necessary; reserve capability metadata and add conformance fixtures before enabling it.

## 4. MCP authorization

For HTTP servers that implement authorization:

- follow current MCP/OAuth discovery semantics;
- store tokens in SecretStore, not server config JSON;
- bind tokens to target resource/audience;
- request least-privilege scopes;
- support bounded step-up authorization when server challenges scopes;
- never forward bearer tokens to a different MCP resource;
- redact tokens from logs/tool context.

For stdio, credentials generally come from a controlled launch environment/secret injection policy rather than pretending HTTP OAuth applies.

## 5. MCP tool catalog

Do not expose every connected tool schema to every model call.

Maintain metadata index containing:

- server ID/provenance;
- tool name/title/description;
- input/output schema fingerprints;
- trust/permission hints;
- tags/keywords;
- health/availability;
- protocol profile.

Context planner/tool router selects a small relevant set. User can pin tools/servers.

Tool name collisions are disambiguated using stable internal IDs such as `serverId/toolName`; never assume MCP server names are globally unique.

## 6. Skills

Canonical package shape:

```text
skill-name/
  SKILL.md
  references/   # optional
  scripts/      # optional
  assets/       # optional
```

Skill metadata should make discovery possible without loading full instructions.

Scopes:

- global;
- project;
- optionally path-scoped via project rule mechanisms.

Activation modes may include explicit, auto-discovered by task relevance, or always-on by user configuration. Always-on skills must remain rare because they consume persistent context.

A Skill guides behavior; it does not grant permissions.

## 7. Project rules / instruction files

Recognize project instruction files such as `AGENTS.md` and optionally `CLAUDE.md` as repository context according to configured precedence. More-specific path rules refine broader project rules.

Repository content is not allowed to override app security policy.

## 8. Plugin manifest

Conceptual fields:

```json
{
  "id": "com.example.plugin",
  "name": "Example",
  "version": "1.0.0",
  "publisher": "example",
  "description": "...",
  "minAppVersion": "...",
  "permissions": [],
  "components": {
    "skills": [],
    "agents": [],
    "commands": [],
    "hooks": [],
    "mcpServers": []
  },
  "source": {},
  "integrity": {}
}
```

Validate manifests against a versioned schema.

## 9. Install vs activate

Installation:

- fetch/copy package;
- verify manifest/integrity metadata where available;
- record source/version;
- inspect requested permissions/components;
- no executable hooks/scripts automatically run.

Activation:

- user/project enables components;
- effective permissions are resolved;
- executable capability may require approval/review;
- lifecycle events become eligible.

## 10. Hooks

Potential lifecycle events:

- session/task start/end;
- user prompt submit;
- before/after model request;
- pre/post tool use;
- tool error;
- before/after compaction;
- subagent start/stop.

Hooks have explicit capability classes: observe, enrich, transform, block. They cannot bypass permission policy or access arbitrary secrets.

V1 can omit general executable hooks while keeping manifest boundary reserved.

## 11. Marketplace

Registry operations:

- browse/search/filter;
- inspect versions/source/components/permissions;
- install/update/disable/enable/uninstall.

Before activation show:

- publisher/source;
- version;
- requested permissions;
- executable hooks/scripts;
- MCP definitions;
- bundled Skills/agents;
- integrity/signature info where available;
- trust warnings.

Popularity/download count is not security evidence.

## 12. Security tests

Test:

- malicious prompt/tool descriptions do not alter instruction precedence;
- MCP tool results cannot grant permission;
- token/resource binding;
- plugin install has no execution side effect;
- path traversal inside packaged assets;
- manifest schema rejection;
- tool-name collision handling;
- bounded tool catalog/context size;
- server disconnect/auth expiry and recovery.
