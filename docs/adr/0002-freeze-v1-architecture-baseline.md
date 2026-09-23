# ADR-0002 — Freeze the V1 architecture baseline and enforce dependency direction

- Status: accepted
- Date: 2026-09-23
- Class: FROZEN architecture baseline
- Supersedes: the advisory/conceptual package language in bootstrap v4
- Superseded by: none

## Context

The bootstrap previously described strong architectural intentions but left enough phrases such as “conceptual monorepo” and “exact package count may be reduced” that an autonomous coding agent could reinterpret the system shape while implementing it. For a long-running agent-built desktop application, prose guidance alone is insufficient: ownership, dependency direction, and trust boundaries must be explicit and mechanically checkable.

The design also lacked a named application/use-case boundary and a first-class `policy-core`, which made it easier for UI/main/tool code to absorb orchestration or authorization logic accidentally.

## Decision

`../ARCHITECTURE.md` is the normative FROZEN V1 baseline.

Freeze:

- Electron + React main/preload/renderer process/trust split;
- renderer as presentation only;
- `contracts` as dependency base;
- explicit `application` use-case layer;
- distinct `agent-core`, `prompt-runtime`, `context-engine`, `provider-core`, `policy-core`, `tool-runtime`, `storage`, `mcp-host`, and `extension-core` ownership;
- the allowed dependency DAG and forbidden reverse edges;
- Tool Runtime + Policy Core as the effectful execution/authorization path;
- Provider Core as provider-specific transport boundary;
- Storage as SQLite boundary;
- architecture fitness checks as a Phase 0 requirement.

Physical packages are created when their first executable responsibility exists; empty future packages are not required. Once a boundary exists, it must obey the frozen ownership/import rules.

Changing a frozen rule requires concrete blocking/safety evidence, a superseding ADR, canonical-doc/test updates, and user approval when product architecture materially changes.

## Consequences

- Antigravity implements a known architecture instead of treating docs as a design suggestion.
- Architecture drift can fail CI rather than depend on reviewers remembering prose.
- The system gains clearer ownership for use cases and authorization.
- Some changes require slightly more ceremony because reverse imports or shortcut implementations are no longer acceptable.
- The baseline still permits current library choices and does not force speculative packages/features before their roadmap phase.

## Alternatives considered

### Leave architecture advisory and let the agent choose

Rejected because the project explicitly needs stable context across long autonomous runs; this makes package ownership and trust boundaries vulnerable to model preference drift.

### Freeze every library/file/package from day one

Rejected as unnecessarily brittle. Fast-moving Electron/native/SQLite/test tooling should remain implementation choices within frozen logical constraints.

### One large core package with conventions only

Rejected because provider, prompt, context, tool/policy, persistence, and extension boundaries carry different trust/compatibility responsibilities and need independently testable dependency rules.

## Fitness / verification

Phase 0 must introduce automated checks for the architecture fitness rules listed in `ARCHITECTURE.md`, including forbidden core UI imports, renderer runtime imports, provider/SQLite boundary violations, forbidden package edges/cycles, tool-policy bypasses, preload raw-object exposure, and fake-provider production leakage.

The exact checking library is an implementation choice.

## Revisit trigger

Revisit only when one or more of the following is demonstrated with concrete implementation evidence:

- a frozen dependency edge prevents a required V1 use case without a reasonable port/interface solution;
- an Electron/platform security requirement invalidates the current process boundary;
- a critical maintained dependency requires an incompatible boundary and no viable alternative exists;
- measured complexity or performance shows a frozen module split itself is the material cause and cannot be corrected internally;
- product scope changes enough that the V1 system boundary is no longer the intended product.
