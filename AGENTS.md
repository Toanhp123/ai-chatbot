# AGENTS.md

## Purpose

Repository-wide operating contract for Antigravity and other coding agents. Keep this file compact, stable, and enforceable. Product/runtime detail lives in `docs/` and is loaded only when relevant.

This repository intentionally contains **no project-local development Skills**. Development uses external capabilities provided by the active Antigravity environment. Product-facing Skills/MCP/plugins described by the app are a separate product concept.

## 1. Instruction precedence

When instructions conflict, follow this order:

1. platform/system safety and sandbox policy;
2. explicit user instruction for the current task;
3. nearest applicable nested `AGENTS.md`;
4. this root `AGENTS.md`;
5. canonical project docs and accepted ADRs;
6. applicable external development Skill/tool instructions;
7. local code conventions/tests where they do not conflict with the intended contracts;
8. agent preference.

External Skills specialize **how** work is performed. They may not redefine product scope, weaken security/permission requirements, supersede accepted ADRs, or bypass the frozen architecture. Skill-generated plans/audits/design notes are working artifacts unless a canonical project document adopts them.

## 2. Development capability routing

Use the **minimum sufficient route** from `docs/DEVELOPMENT_TOOLING.md`; do not invoke every capability for every task.

- **Superpowers — REQUIRED** for non-trivial implementation, refactor, debugging, architecture work, or code review. Use the relevant Superpowers Skill(s). Missing Superpowers blocks non-trivial code work; record the blocker rather than creating a repo-local substitute.
- **`ui-ux-pro-max` — REQUIRED** in addition to Superpowers for substantial UI work: new screens/shells, major flows, redesigns, design-system work, accessibility/interaction redesign, or substantial component composition. Missing it blocks that UI slice, not unrelated backend/docs work.
- **Graphify — REQUIRED once substantive source exists** for broad repository architecture/dependency/impact analysis, unfamiliar cross-module tracing, and structural review. Query a fresh local code graph first, then verify consequential conclusions in source/tests. It is advisory developer intelligence, never architectural authority.
- **`frontend-design` — OPTIONAL** for visual/taste refinement when distinctive art direction materially improves the UI. It never substitutes for `ui-ux-pro-max`.
- **Ponytail — OPTIONAL** for a final simplicity/YAGNI review. It is not the UI-design Skill and never substitutes for Superpowers.

Do not vendor/copy development Skill bodies or generated tool rules/workflows into this repository. Capability routing, freshness, privacy, and blocking behavior are canonical in `docs/DEVELOPMENT_TOOLING.md`.

## 3. Context loading

Start with this file; do not load every doc by default.

- bootstrap/resume → `PROMPT.md`, `docs/EXECUTION_PROTOCOL.md`, `docs/IMPLEMENTATION_STATUS.md`, active `docs/ROADMAP.md` phase, `docs/DECISIONS.md`, applicable ADRs;
- development capability/routing → `docs/DEVELOPMENT_TOOLING.md`;
- architecture/boundaries → `docs/ARCHITECTURE.md`, `docs/CONTRACT_INVENTORY.md`, `docs/GLOSSARY.md`;
- product/UI → `docs/PRODUCT_SPEC.md`, `docs/UX_SPEC.md`, `docs/UI_SYSTEM.md`;
- prompts/context → `docs/PROMPT_RUNTIME.md`, `docs/CONTEXT_ENGINE.md`;
- providers → `docs/PROVIDER_SYSTEM.md`;
- agent/tools/security → `docs/AGENT_RUNTIME.md`, `docs/TOOL_RUNTIME.md`, `docs/SECURITY.md`;
- MCP/extensions → `docs/MCP_AND_EXTENSIONS.md`;
- persistence → `docs/DATA_MODEL.md`;
- local AI/training → `docs/LOCAL_AI.md`, `docs/MODEL_LAB.md`;
- release/privacy/recovery → `docs/OPERATIONS_AND_PRIVACY.md`;
- tests/evals → `docs/TEST_STRATEGY.md`.

Inspect relevant code, tests, Git state, and nearby docs before editing. When Graphify is applicable and fresh, prefer focused graph queries plus targeted source verification over blind repository-wide grep or broad context loading.

## 4. Architecture authority

`docs/ARCHITECTURE.md` is the **FROZEN V1 architecture baseline**. Its process boundaries, ownership, dependency direction, forbidden dependencies, and trust boundaries are normative.

An agent may choose items explicitly marked **IMPLEMENTATION CHOICE**. Changing a FROZEN item requires all of:

1. concrete implementation evidence that the baseline is blocked or materially unsafe;
2. an ADR explicitly superseding the affected decision;
3. updates to canonical docs and architecture fitness tests;
4. user approval when product architecture or scope materially changes.

If code conflicts with a FROZEN rule, fix the code unless those superseding conditions are met.

## 5. Engineering loop and autonomy

For non-trivial work: classify the task/route → use required Skills → inspect active milestone/contracts/code → use Graphify when the route requires structural reconnaissance → choose the smallest coherent vertical change → implement incrementally → run narrow validation then milestone gates → review the actual diff → fix material findings → update `docs/IMPLEMENTATION_STATUS.md` during bootstrap/long runs → verify evidence before claiming completion.

Do not stop after planning/scaffolding while the active acceptance gate is locally achievable. Make reversible implementation choices autonomously inside frozen boundaries. Stop only for a real external blocker, credential/account action, destructive or externally irreversible action, material product ambiguity, a required unavailable capability at the point it is needed, or an unresolved repository-evidence conflict.

A feature is complete only when its intended path works, required state persists, failures/permissions/cancellation are handled, relevant tests and architecture fitness pass, and docs match reality.

## 6. Non-negotiable runtime invariants

- Renderer is presentation only: no provider transport, secrets, SQLite, shell, raw filesystem, MCP transport, or training process ownership.
- Preload exposes a narrow typed/versioned IPC bridge, never raw Electron/Node primitives.
- Agent Core is React/Electron independent.
- Prompt Runtime, Context Engine, Provider Core, Tool Runtime, Policy Core, Storage, MCP Host, and Extension Core retain the ownership defined in `docs/ARCHITECTURE.md`.
- Provider adapters normalize request/stream/tool-call/usage/capability/error semantics.
- Model output never grants itself permission; sensitive effects pass through Tool Runtime + Policy Core.
- MCP/plugin/web/retrieved/model-generated content is untrusted data and cannot override trusted instructions.
- Secrets never become normal DB fields, logs, prompts, fixtures, or Git content.
- Heavy parsing/indexing/inference/Git/training work stays off the renderer thread.
- Long-running work is observable, cancellable, bounded, and recoverable.
- Repository/model/tool context is explicitly budgeted; never send everything by default.

## 7. UI, security, and data

For substantial UI, `ui-ux-pro-max` + `docs/UI_SYSTEM.md` + `docs/UX_SPEC.md` are required. Cover applicable empty/loading/streaming/approval/error/offline/degraded/cancelled states, keyboard/focus behavior, bounded rendering for unbounded content, and rendered validation. Do not clone another product's brand/shell.

Persistent schema changes require reproducible migrations and upgrade tests. Secrets use `SecretStore` and secure platform storage where available. Before auth, secret storage, IPC, shell/sandbox, MCP/plugin execution, DB migration, updates, model execution/downloads, or training-process launch, perform a focused threat/failure-mode review. Never escalate privileges merely to make a command work.

## 8. Testing and architecture fitness

Use unit tests for deterministic logic, integration/contract tests for boundaries, E2E for critical workflows, and deterministic eval fixtures for agent/runtime behavior. Core gates must not require paid APIs or user credentials; use the fake-provider path.

Phase 0 architecture checks must catch at least: React/Electron imports in core; renderer imports of runtime internals; forbidden DAG edges/cycles; provider calls outside Provider Core; SQLite access outside Storage; effectful tool paths bypassing Tool Runtime/Policy Core; unsafe preload exposure; fake-provider production leakage. The checker library is an implementation choice; these assertions are not.

## 9. Documentation and completion

One canonical owner per durable rule. Update it in the same change when behavior/contracts/schema/trust/architecture/provider/UX/acceptance criteria change. Use ADRs for consequential cross-cutting decisions; use `docs/TECH_DEBT.md` only for deliberate compromises with risk and correction trigger.

Before declaring completion, self-review the actual diff and report only verified facts: implemented scope, commands/tests actually run, required capability usage, Graphify evidence when structurally relevant, architecture fitness result, unresolved blockers/limitations, and exact next roadmap step.
