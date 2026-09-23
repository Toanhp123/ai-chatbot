# Chatbot Bootstrap v4.4 — Antigravity Architecture-Locked Context Pack

This is a **context-and-execution bootstrap**, not application source code. Put the complete bundle at the repository root before asking Antigravity to build the product.

## What changed in v4.4

v4.4 keeps the frozen product architecture and v4.3 capability routing, but removes **external-tool installation/setup noise** from the bootstrap:

- docs now say **which Skill/tool to use and when**, not how to download/install/update it;
- Superpowers, `ui-ux-pro-max`, and Graphify own their own invocation/setup details;
- project docs keep only routing, blocking, privacy, freshness, evidence, and authority rules;
- Graphify remains required for broad structural analysis after substantive code exists, without hard-coding CLI commands into the project context;
- no project-local development Skill/tool plumbing is added.

The product architecture is unchanged from the frozen v4.1+ baseline.

## Development capabilities

- **Superpowers** — required for non-trivial engineering;
- **`ui-ux-pro-max`** — required for substantial frontend/UI work;
- **Graphify** — required after scaffold for broad repository architecture/dependency/impact analysis;
- **`frontend-design`** — optional visual/art-direction refinement;
- **Ponytail** — optional simplicity/YAGNI review only.

The bundle contains **no project-local development Skills**. The agent is expected to use the named capabilities when the routing policy requires them. `docs/DEVELOPMENT_TOOLING.md` is the canonical routing/blocking/privacy/freshness/evidence policy.

## Layers

- `PROMPT.md` — one-shot mission and bootstrap target;
- `AGENTS.md` — compact always-on behavior, authority, capability gates, and architecture enforcement;
- `docs/ARCHITECTURE.md` — FROZEN V1 process/module/dependency baseline;
- `docs/CONTRACT_INVENTORY.md` — contract ownership/stability map;
- `docs/GLOSSARY.md` — canonical terminology;
- `docs/DEVELOPMENT_TOOLING.md` — task routing plus external Skill/Graphify operating policy;
- `docs/` — subsystem contracts loaded only when relevant;
- `docs/IMPLEMENTATION_STATUS.md` — durable resume/evidence ledger.

## Recommended first prompt

> Read `AGENTS.md` and execute `PROMPT.md` end-to-end. Use the minimum sufficient capability route from `docs/DEVELOPMENT_TOOLING.md`: Superpowers for non-trivial engineering, `ui-ux-pro-max` for substantial UI, and Graphify for broad structural repository analysis once substantive source exists. Treat `docs/ARCHITECTURE.md` as the frozen V1 baseline, run architecture fitness checks, continue autonomously through the bootstrap gate in `docs/EXECUTION_PROTOCOL.md`, persist progress in `docs/IMPLEMENTATION_STATUS.md`, and stop only for a hard blocker defined by the protocol.

A shorter prompt should also work:

> Build this project according to `PROMPT.md`.

## Context discipline

Do not concatenate all Markdown into one giant prompt. Keep always-on rules small and load only the canonical architecture/subsystem contracts needed for the current task. The documentation index in `docs/README.md` defines ownership and reading paths.

## Architecture-change rule

Antigravity may choose details explicitly marked **IMPLEMENTATION CHOICE**. It may not alter **FROZEN** process boundaries, dependency direction, ownership, or trust boundaries simply because another Skill/tool/design suggests something different.

A frozen change requires implementation evidence, a superseding ADR, updates to canonical docs/tests, and user approval when product architecture materially changes.

## Maintenance

- product mission/scope → `PROMPT.md` + `docs/PRODUCT_SPEC.md`
- persistent agent behavior → `AGENTS.md`
- development task/Skill/tool routing → `docs/DEVELOPMENT_TOOLING.md`
- architecture/dependency ownership → `docs/ARCHITECTURE.md`
- contract surface/stability → `docs/CONTRACT_INVENTORY.md`
- canonical terminology → `docs/GLOSSARY.md`
- implementation progress/resume → `docs/IMPLEMENTATION_STATUS.md`
- cross-cutting decision → `docs/adr/` + `docs/DECISIONS.md`
- deliberate compromise → `docs/TECH_DEBT.md`
- dated external facts → `docs/research.md`

Code, tests, and runtime evidence are implementation reality. Documentation must never claim an unimplemented feature works.
