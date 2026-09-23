# Contract Inventory

> **Authority:** normative cross-boundary contract map
> **Purpose:** prevent duplicate/parallel protocols and make architecture changes reviewable.
> **Rule:** a contract has one owner. Consumers may adapt it at the boundary but must not redefine its semantics locally.

## Stability classes

- **V1-STABLE** — once implemented and used across packages/persistence, breaking semantic changes require migration/versioning and usually an ADR.
- **INTERNAL-STABLE** — stable across internal subsystem boundaries; can evolve deliberately with all consumers/tests updated.
- **EXPERIMENTAL** — intentionally early; may change within the active phase but still has one owner.

## Inventory

| Contract | Owner | Initial stability | Primary consumers | Non-negotiable rule |
| --- | --- | --- | --- | --- |
| Desktop IPC request/event envelopes | `contracts` + desktop main/preload adapters | V1-STABLE after Phase 1 | renderer, preload, main/application | versioned + validated; no raw Electron/Node exposure |
| Application use-case DTOs | `application` / exported through `contracts` where cross-process | INTERNAL-STABLE | renderer/main | presentation-safe; no vendor/SQL/process objects |
| `AgentTask` state/events | `agent-core` | V1-STABLE after Phase 3 | application/UI/audit | distinct from MCP Tasks; typed cancellation/terminal states |
| Normalized model request | `prompt-runtime` + `contracts` | V1-STABLE after Phase 1 | agent-core, provider-core | provider-neutral before adapter translation |
| Normalized model stream/event | `provider-core` + `contracts` | V1-STABLE after Phase 1 | agent-core/application/UI | vendor frames never leak outward |
| Provider capability/model metadata | `provider-core` | INTERNAL-STABLE | routing/settings/UI | behavior driven by capabilities, not provider-name branching |
| Provider error taxonomy | `provider-core` | V1-STABLE after Phase 1 | agent/application/UI | raw vendor errors wrapped with safe diagnostics |
| Context evidence/package | `context-engine` + `contracts` | INTERNAL-STABLE | prompt-runtime, diagnostics | bounded + provenance-aware |
| Prompt instruction layers/assembled request diagnostics | `prompt-runtime` | INTERNAL-STABLE | agent/provider/dev diagnostics | trusted precedence explicit; untrusted content cannot promote itself |
| Tool descriptor/invocation/result | `tool-runtime` + `contracts` | V1-STABLE after Phase 3 | agent, MCP adapter, extensions | schema validated; cancellation/audit supported |
| Permission request/decision/grant scope | `policy-core` + `contracts` | V1-STABLE after Phase 3 | tool-runtime, application/UI, storage adapter | Policy Core owns semantics/evaluation; Application/Storage persist grant records; model/tool text cannot grant permission |
| MCP server/profile/tool/resource/prompt descriptor | `mcp-host` + `contracts` | INTERNAL-STABLE | application/tool/context/extension layers | protocol/version/provenance preserved |
| Product Skill/extension manifest | `extension-core` | V1-STABLE when Phase 4/5 ships | application/settings/context | install/activate/permission are separate states |
| Storage repository interfaces | `storage` | INTERNAL-STABLE | application/core via explicit ports | raw SQL/driver does not escape Storage |
| Persisted DB schema/migrations | `storage` + `DATA_MODEL.md` | V1-STABLE once released | storage only | forward migrations + upgrade tests; secrets by reference |
| Secret reference/health | desktop secure-storage adapter + `contracts` | V1-STABLE after Phase 0 | application/settings/providers | secret values never ordinary persistence/log data |
| Structured log/audit envelope | owning runtime + shared contract fields | INTERNAL-STABLE | diagnostics/support/recovery | correlation + redaction required |
| Fake-provider protocol/fixtures | provider test harness | EXPERIMENTAL then INTERNAL-STABLE | integration/E2E | same normalized provider seam; impossible to register in production |
| Model Lab worker protocol | application/controller + `services/model-lab` | V1-STABLE when Phase 8 ships | desktop controller, Python worker | versioned structured messages; no Python objects across boundary |

## Change rules

Before changing a contract:

1. identify its owner and stability class;
2. update the owner first, not a downstream local copy;
3. update all producers/consumers and contract tests in the same change;
4. add migration/version negotiation for persisted/external V1-STABLE changes;
5. use an ADR when semantics change across multiple architectural owners;
6. update this inventory if ownership or stability changes.

## Contract anti-patterns

Do not create:

- a second provider event type in the UI because a component needs a convenience field;
- a second permission model inside MCP or plugins;
- feature-local SQLite schemas outside Storage migrations;
- vendor request objects as application DTOs;
- renderer-only copies of agent/tool states that diverge semantically from runtime contracts;
- a second notion of “task” that silently conflates Agent Tasks, tool calls, training jobs, and MCP Tasks.
