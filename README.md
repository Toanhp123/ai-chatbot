# Chatbot Bootstrap v4.9 — Antigravity Full-System-Consistency Context Pack

This is a **context-and-execution bootstrap**, not application source code. Put the complete bundle at the repository root before asking Antigravity to build the product.

## What changed in v4.9

v4.9 keeps the v4.8 architecture/module DAG and performs a full-system contradiction/canonicalization audit rather than adding another subsystem.

ADR-0006 and coordinated contract fixes now make the following unambiguous:

- durable Agent lifecycle events are ordered once per Task across all Runs/resumes;
- Tool Attempt events are distinct from logical Tool Call terminal events;
- `PreparedModelRequest`, `ContextPackage`, and RoutePlan ownership/terminology are canonical across runtime and persistence;
- Context Engine selects evidence/resources while Prompt Runtime alone owns instruction authority and final compaction/request assembly;
- agent tool/MCP allowlists are exposure filters, never permission or activation grants;
- extension/Skill/MCP revision identity is immutable while global/project activation is a separate scoped association;
- Model Lab uses the canonical `TrainingJob` name and treats job status as a projection over TrainingAttempts;
- every Local Models promotion appends an immutable Model Promotion Record instead of relying on a mutable artifact flag;
- `unknown_outcome` vocabulary is used consistently where execution reality cannot be proven.

No new top-level runtime package, development Skill, or product feature was added. `AGENTS.md` and `PROMPT.md` remain unchanged from v4.8; this pass tightens canonical subsystem contracts and ADR governance only.

## Development capabilities

The bundle uses external development capabilities and contains **no project-local development Skills**. `docs/DEVELOPMENT_TOOLING.md` is the single canonical place to determine which capability is required for a task and how its evidence/blocking rules work.

## Layers

- `PROMPT.md` — one-shot mission and bootstrap target;
- `AGENTS.md` — compact always-on behavior, authority, and architecture enforcement;
- `docs/ARCHITECTURE.md` — FROZEN V1 process/module/dependency/runtime baseline;
- `docs/CONTRACT_INVENTORY.md` — contract ownership/stability map;
- `docs/GLOSSARY.md` — canonical terminology;
- `docs/DEVELOPMENT_TOOLING.md` — development-capability routing/status/blocking/evidence policy;
- `docs/ROADMAP.md` — canonical phase deliverables and acceptance criteria;
- `docs/` — subsystem contracts loaded only when relevant;
- `docs/IMPLEMENTATION_STATUS.md` — durable resume/evidence ledger.

## Recommended first prompt

> Read `AGENTS.md` and execute `PROMPT.md` end-to-end.

The shortest intended prompt is also sufficient:

> Build this project according to `PROMPT.md`.

## Context discipline

Do not concatenate all Markdown into one giant prompt. Keep always-on rules small and load only the canonical architecture/subsystem contracts needed for the current task. The documentation index in `docs/README.md` defines ownership and reading paths.

## Architecture-change rule

Antigravity may choose details explicitly marked **IMPLEMENTATION CHOICE**. It may not alter **FROZEN** process boundaries, dependency direction, ownership, trust boundaries, or accepted ADR-0003/ADR-0004/ADR-0005/ADR-0006 runtime/trust/Model-Lab/consistency invariants simply because another Skill/tool/design suggests something different.

A frozen change requires implementation evidence, a superseding ADR, updates to canonical docs/tests, and user approval when product architecture materially changes.

## Maintenance

- product mission/scope → `PROMPT.md` + `docs/PRODUCT_SPEC.md`
- persistent agent behavior → `AGENTS.md`
- development task/Skill/tool routing → `docs/DEVELOPMENT_TOOLING.md`
- architecture/dependency ownership → `docs/ARCHITECTURE.md`
- cross-cutting runtime identity/replay/side-effect invariants → `docs/adr/0003-runtime-consistency-and-side-effect-safety.md`
- workspace/MCP/extension/local-runtime trust invariants → `docs/adr/0004-extension-workspace-and-local-runtime-trust.md`
- Model Lab lineage/resume/artifact/promotion invariants → `docs/adr/0005-model-lab-lineage-execution-and-promotion.md`
- cross-system identity/event/activation/promotion consistency → `docs/adr/0006-cross-system-identity-activation-and-promotion-consistency.md`
- contract surface/stability → `docs/CONTRACT_INVENTORY.md`
- canonical terminology → `docs/GLOSSARY.md`
- milestone deliverables/acceptance → `docs/ROADMAP.md`
- implementation progress/resume/evidence → `docs/IMPLEMENTATION_STATUS.md`
- cross-cutting decision → `docs/adr/` + `docs/DECISIONS.md`
- deliberate compromise → `docs/TECH_DEBT.md`
- dated external facts → `docs/research.md`

Code, tests, and runtime evidence are implementation reality. Documentation must never claim an unimplemented feature works.
