# Architecture Decision Register

This file is the compact current-decision index. Detailed rationale belongs in `docs/adr/` when a decision materially constrains future implementation.

## Decision classes

- **FROZEN** — part of the V1 architecture/product baseline. Changing it requires a superseding ADR and the architecture change protocol.
- **OPERATING** — repository/agent workflow rule. Change deliberately when workflow evidence justifies it.
- **IMPLEMENTATION CHOICE** — the architecture defines the constraint, while the concrete library/mechanism may be selected during implementation.
- **DEFERRED** — intentionally not decided/built until its roadmap trigger.

## Current decisions

| ID | Class | Status | Decision |
| --- | --- | --- | --- |
| D-001 | FROZEN | accepted | Desktop-first, local-first application; cloud sync is not an early architectural dependency. |
| D-002 | FROZEN | accepted | Electron + React; secure main/preload/renderer split; core services stay outside renderer. |
| D-003 | FROZEN | accepted | Provider-neutral internal protocol; vendor payloads do not propagate into application/UI/agent contracts. |
| D-004 | FROZEN | accepted | V1 routing is deterministic and capability/policy driven before any adaptive routing. |
| D-005 | FROZEN | accepted | Central Tool Runtime + Policy Core mediate effectful agent/MCP/extension actions. |
| D-006 | FROZEN | accepted | Layered code context: inventory/structure/lexical/optional semantic retrieval under explicit token budgets; never whole-repo-by-default. |
| D-007 | FROZEN | accepted | MCP compatibility is profile/version aware; core does not hard-code one historical session model. |
| D-008 | FROZEN | accepted | Product Skills use progressive disclosure; metadata discovery is cheap and full bodies/resources load only when relevant. |
| D-009 | FROZEN | accepted | Extension installation/activation does not imply permission grant. |
| D-010 | FROZEN | accepted | Local inference integrates maintained runtimes/endpoints; no custom inference engine. |
| D-011 | FROZEN | accepted | Model Lab is an isolated post-training worker/control plane outside Electron runtime. |
| D-012 | FROZEN + IMPLEMENTATION CHOICE | accepted | SQLite is the local durable store with reproducible migrations; exact driver/migration library is selected during Phase 0. |
| D-013 | FROZEN | accepted | Secrets are behind `SecretStore`; SQLite holds opaque references/metadata only. |
| D-014 | OPERATING | accepted | Bootstrap is autonomy-first for reversible repository decisions; stop only for defined hard blockers. |
| D-015 | OPERATING | accepted | Fresh-repository defaults are defined by ADR-0001; coherent existing repository choices take precedence when compatible. |
| D-016 | FROZEN | accepted | Required bootstrap E2E is credential-independent via deterministic fake provider through the production-normalized provider seam. |
| D-017 | FROZEN | accepted | Prompt Runtime is a distinct boundary from Context Engine and Provider Core. |
| D-018 | OPERATING | accepted | Development Skills stay external to the product repo: use Superpowers for non-trivial engineering and `ui-ux-pro-max` for substantial UI; no repo-local substitute. |
| D-019 | FROZEN | accepted | Isolated worktree/workspace execution may be introduced for coding tasks, but it never bypasses Tool Runtime/Policy Core and apply-back is explicit/conflict-aware. |
| D-020 | FROZEN | accepted | `ARCHITECTURE.md` defines the V1 logical modules, ownership, dependency DAG, and architecture fitness requirements; ADR-0002 governs change. |
| D-021 | FROZEN | accepted | `contracts` is the only dependency-base package; `application` is the use-case boundary; `policy-core` is explicit and separate from execution. |
| D-022 | OPERATING | accepted | Substantial UI must use `ui-ux-pro-max` plus `UX_SPEC.md`/`UI_SYSTEM.md`; rendered self-critique is required where possible. `frontend-design` is an optional visual-taste companion, not the required baseline. |
| D-023 | OPERATING | accepted | Architecture documentation is governed by canonical ownership, a glossary, a contract inventory, ADR history, and executable fitness checks rather than prose alone. |
| D-024 | OPERATING | accepted | Development capabilities use a minimum-sufficient task-routing policy owned by `DEVELOPMENT_TOOLING.md`; external capability instructions cannot override canonical product/architecture contracts. |
| D-025 | FROZEN | accepted | Runtime consistency follows ADR-0003: task/run/turn/attempt identities are distinct, prepared requests/context are immutable snapshots, approvals bind to normalized operations, non-idempotent side effects are never blindly replayed, and V1 serializes mutations per physical workspace root unless isolated. |
| D-026 | FROZEN | accepted | Workspace trust gates repository-controlled instruction/extension authority; opening/indexing a root does not automatically trust its `AGENTS.md`, Skills, hooks, commands or plugin config. |
| D-027 | FROZEN | accepted | Extension/MCP trust follows ADR-0004: install is inert, activation binds immutable reviewed revisions; MCP-delivered Skills preserve remote-untrusted origin and require content-bound per-Skill activation; Skill metadata/`allowed-tools` cannot grant host permission; arbitrary third-party code is never dynamically imported into Electron/core processes. |
| D-028 | FROZEN | accepted | Local AI endpoints/models carry explicit endpoint class, process ownership and artifact provenance; opaque runtime-hosted tools and model custom code never inherit app Tool Runtime/host-process trust. |
| D-029 | FROZEN | accepted | Model Lab follows ADR-0005: immutable dataset/plan/attempt/artifact lineage, explicit resume compatibility, local/offline-by-default compute, accelerator leases, staged artifact finalization, and evaluation before model promotion. |
| D-030 | FROZEN | accepted | Cross-system consistency follows ADR-0006: Task-scoped durable event ordering across Runs, Tool Call vs Tool Attempt event separation, canonical PreparedModelRequest/ContextPackage ownership, exposure-not-permission agent allowlists, immutable revision + scoped activation separation, TrainingJob projection semantics, and append-only Model Promotion Records. |

## Implementation choices still open

These are intentionally left to current implementation evidence. Selecting one does not authorize changing frozen boundaries.

- SQLite driver and migration integration;
- schema validation library;
- renderer state-management strategy/library;
- typed IPC helper/library;
- architecture dependency-checking library;
- first Tree-sitter languages and native/WASM binding choice;
- checkpoint implementation for pre-existing dirty workspaces;
- sandbox backend/fallback mechanism when Phase 3 requires it;
- exact MCP SDK/version support matrix compatible with the frozen protocol-profile boundary;
- extension package distribution/integrity mechanism when Phase 5 begins;
- telemetry mechanism only if/when an explicit opt-in policy is accepted;
- exact Model Lab backend adapter mix, environment manager and hardware-specific launch mechanism within ADR-0005.

Record an ADR when the choice is consequential, hard to reverse, compatibility-sensitive, or changes a cross-cutting contract. Routine reversible library selection within the frozen boundaries does not require an ADR.

## Deferred decisions

- marketplace governance/distribution beyond the Phase 5 boundary;
- generalized parallel/multi-agent conflict model beyond Phase 6;
- browser automation runtime beyond its roadmap phase;
- optional cloud sync/collaboration architecture;
- advanced adaptive provider routing based on accumulated operational data.

## Superseding rule

An ADR that changes a FROZEN decision must explicitly name the superseded ID(s), update `ARCHITECTURE.md`/other canonical owners, update architecture/contract tests, and explain migration consequences. An ADR file by itself does not silently supersede the current architecture.
