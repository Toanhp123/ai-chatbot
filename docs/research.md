# Research Notes

> **Authority:** research/evidence only.
> **Rule:** this file records dated external facts and implementation implications. It does not silently override canonical architecture/product docs.

Last review: **2026-09-23**.

## 1. Antigravity rules and Agent Skills

Primary sources:

- https://www.antigravity.google/docs/skills?tab=ide
- https://antigravity.google/docs/ide/rules/
- https://antigravity.google/docs/migration/workflows-to-skills
- https://antigravity.google/docs/cli/gcli-migration/

Findings:

- Antigravity 2.0 supports the open Agent Skills format: a skill directory with `SKILL.md`, optional resources/scripts/examples, and progressive disclosure.
- The agent discovers skills semantically and can also invoke one explicitly by name/slash command.
- Antigravity continues to parse/enforce root `AGENTS.md`/workspace rules.
- Legacy Workflows are being retired in favor of Agent Skills.

Repository implication:

- Keep development Skills external to the product repository; do not vendor Skill bodies or generated agent plumbing.
- `AGENTS.md` can explicitly require skill names so Antigravity activates them when relevant.
- Missing required development Skills should be treated as a capability blocker rather than silently copying or reimplementing them.

## 2. Superpowers development methodology

Primary source:

- https://github.com/obra/superpowers
- https://github.com/obra/superpowers/releases

Findings:

- Superpowers is a composable development methodology around design/planning, TDD, systematic debugging, review, verification, worktrees/subagents, and evidence-before-completion.
- Current releases explicitly support Antigravity (support was added in the 6.x line; v6.4.1 was released 2026-09-18).
- The project itself emphasizes complexity reduction and verification rather than only code generation.

Repository implication:

- Do not duplicate Superpowers workflow prose in this repo because it will age and waste context.
- Require Antigravity to use the relevant Superpowers Skills for non-trivial work and let the capability define its own detailed workflow.

## 3. UI/design Skill selection

Selected required Skill:

- `ui-ux-pro-max`: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

Optional companion reviewed:

- Anthropic `frontend-design`: https://github.com/anthropics/skills/tree/main/skills/frontend-design

Other references reviewed:

- https://github.com/aladicf/better-web-ui
- https://github.com/hueyexe/frontend-agent-skills

Why `ui-ux-pro-max` is the required baseline for this project:

- its current metadata explicitly targets web, mobile, **and desktop** UI/UX work and includes an Antigravity platform template;
- it covers design-system direction, accessibility, interaction, responsive layout, typography/color, charts, and stack-specific implementation guidance rather than aesthetics alone;
- its searchable guidance can be used selectively, which fits the repository's progressive-context strategy;
- the project itself documents a complementary stack where `ui-ux-pro-max` is the UI/UX knowledge layer and Anthropic `frontend-design` is the visual/taste layer.

Repository policy therefore keeps only one hard UI dependency: **`ui-ux-pro-max` is REQUIRED for substantial UI**. `frontend-design` is an optional second-pass visual refinement; it is not another bootstrap blocker. `UX_SPEC.md`/`UI_SYSTEM.md` remain authoritative for this product's flows, states, accessibility, architecture, and acceptance gates.

### Ponytail clarification

Primary sources:

- https://github.com/DietrichGebert/ponytail
- representative skill: `skills/ponytail/SKILL.md`

Ponytail is an anti-over-engineering/YAGNI coding skill: reuse existing code, standard library/native platform first, minimize dependencies/abstractions, and prefer the smallest solution that works. It is **not** a UI-design skill.

Repository implication:

- remove all “Pongtail UI skill” assumptions;
- require `ui-ux-pro-max` for substantial UI;
- keep `frontend-design` optional for visual refinement;
- treat Ponytail only as an optional simplicity audit.

## 4. Architecture-documentation repositories reviewed

### BASIS Architecture

Source:

- https://github.com/basis-foundation/basis-architecture

High-value patterns:

- explicit component responsibilities and dependency rules;
- a dedicated enforceable kernel-boundary document;
- a decision test for where code belongs;
- distinction between conceptual/reference architecture and implementation;
- canonical glossary to stop terminology drift;
- reviewer-oriented start paths.

Applied here:

- `ARCHITECTURE.md` now freezes ownership and dependency direction;
- explicit boundary decision test;
- `GLOSSARY.md` added;
- architecture changes require evidence instead of agent preference.

### Oak Open Curriculum Ecosystem

Source:

- https://github.com/oaknational/oak-open-curriculum-ecosystem
- architecture decision index: `docs/architecture/architectural-decisions/README.md`

High-value patterns:

- documentation carries explicit authority/status/last-reviewed concepts;
- “Start Here” reading paths instead of expecting readers/agents to ingest everything;
- ADRs include superseded/deprecated/proposed state and are treated as a governed corpus;
- architecture/quality rules are connected to agentic engineering practice.

Applied here:

- docs index now defines authority classes and task-specific reading paths;
- decision register separates FROZEN, OPERATING, IMPLEMENTATION CHOICE, and DEFERRED;
- superseding rules are explicit.

### Architecture Decision Record / MADR projects

Sources:

- https://github.com/architecture-decision-record/architecture-decision-record
- https://github.com/adr/madr

High-value patterns:

- decisions capture context, decision, consequences, alternatives, and revisit conditions;
- architecture “fitness functions” turn decisions into objective automated checks.

Applied here:

- ADR template adds verification/fitness and superseding metadata;
- architecture rules must gain automated fitness checks in Phase 0.

### Recon Core

Source:

- https://github.com/recon-labs/recon-core

High-value patterns:

- separates framework behavior, architecture, implementation guidance, decisions, compatibility, and public contract inventory;
- contract changes are explicit review surfaces rather than incidental type edits.

Applied here:

- `CONTRACT_INVENTORY.md` records owner/stability/consumers/change rules for cross-boundary contracts.

### arc42 + arc42-language

Sources:

- https://github.com/arc42/arc42-template
- https://github.com/docToolchain/arc42-language

High-value patterns:

- arc42 is a pragmatic completeness structure spanning goals, constraints, system context, solution strategy, building blocks, runtime/deployment, cross-cutting concepts, decisions, quality requirements, risks/debt, and glossary;
- `arc42-language` treats architecture as human-readable Markdown plus machine-verifiable structured information and explicitly targets architecture drift in agent-assisted development;
- documentation coverage and architecture conformance are separate: coverage helps humans/agents locate the right contract, while executable fitness checks prove selected boundaries remain true.

Applied here:

- retain the existing domain-oriented canonical files instead of copying arc42 into a second hierarchy;
- add an arc42-style coverage map to `README.md` as a completeness check;
- keep architecture fitness tests as the executable enforcement layer;
- do not add a docs DSL/toolchain dependency during bootstrap unless plain Markdown + architecture tests proves insufficient.

## 5. Architecture conclusion for this project

The previous bootstrap had good subsystem descriptions but was still **architecture-guided**: an agent could reinterpret package boundaries or collapse responsibilities because physical/package language was described as conceptual.

v4.1 changes the model to:

- **FROZEN logical architecture** — process/trust boundaries, ownership, dependency DAG, effect boundaries;
- **IMPLEMENTATION CHOICE** — fast-moving/reversible libraries and local mechanics;
- **DEFERRED** — future systems not to scaffold speculatively;
- **fitness functions** — mechanical checks so architecture is executable, not prose only;
- **contract inventory + glossary** — less semantic drift over long agent runs.

This is intentionally stricter than typical human-only docs because the primary implementer may be a long-running autonomous coding agent.

## 6. Context/repository understanding references

References:

- https://aider.chat/docs/repomap.html
- https://docs.continue.dev/customize/deep-dives/custom-providers

Implication: prefer compact structural/symbol maps and explicit relevant context sources under token budgets rather than whole-repository prompts.

## 7. Multi-provider routing references

References:

- https://docs.litellm.ai/docs/routing
- https://www.librechat.ai/docs/quick_start/custom_endpoints

Implication: provider/model selection stays capability/policy driven with explicit timeout/retry/fallback behavior and normalized errors/usage.

## 8. MCP/extensions references

References:

- https://www.jan.ai/docs/desktop/mcp
- https://www.librechat.ai/docs/features/mcp
- https://docs.openwebui.com/features/extensibility/plugin/tools/
- https://blog.modelcontextprotocol.io/posts/2026-07-28/
- https://ts.sdk.modelcontextprotocol.io/v2/migration/support-2026-07-28
- https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks

Implication: preserve MCP protocol/profile metadata, separate transport from internal tool semantics, expose relevant tools lazily, and keep install/activation/permission distinct. MCP Tasks remain distinct from the product's `AgentTask`.

## 9. Toolchain version research policy

Node/Electron/provider SDK/MCP SDK/local-runtime/training-stack versions change quickly. Re-check official sources immediately before scaffold or upgrade. Keep stable architectural constraints in canonical docs and record only dated compatibility facts here.


## 10. Graphify developer codebase-intelligence layer — 2026-09-23

Primary sources:

- https://github.com/Graphify-Labs/graphify
- https://github.com/Graphify-Labs/graphify/blob/v8/ARCHITECTURE.md
- https://github.com/Graphify-Labs/graphify/blob/v8/graphify/install.py

Observed capabilities relevant to this project:

- Graphify converts code/docs and other inputs into a queryable knowledge graph with relationship confidence (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`), community detection, path/query/explain workflows, and a human-readable report.
- Source-code extraction supports local deterministic AST parsing across many languages without requiring a model API.
- `.gitignore` is respected and `.graphifyignore` can add stricter exclusions.
- Google Antigravity is a supported platform and Graphify can be used as an external developer capability without making its generated agent plumbing part of the product repository.
- Upstream recommends graph-first navigation when a graph exists, followed by targeted source reads.

Project decision:

- use Graphify as external developer tooling, not as product architecture or the app's Context Engine;
- require it after scaffold for broad architecture/dependency/impact analysis;
- keep the repo's own `AGENTS.md` as the always-on Graphify policy;
- default to local code-structure extraction for routine repository analysis;
- keep generated graph state local/regenerable by default and do not enable Graphify Git hooks during bootstrap;
- semantic extraction through external/model backends is opt-in and subject to privacy review.

This preserves Graphify's navigation value without allowing generated/inferred graph data or tool-specific plumbing to become architectural authority.


## 11. Development capability routing verification — 2026-09-23

Primary sources:

- https://github.com/obra/superpowers
- https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/src/ui-ux-pro-max/templates/platforms/agent.json
- https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/cli/src/index.ts
- https://github.com/Graphify-Labs/graphify
- https://github.com/Graphify-Labs/graphify/blob/v8/graphify/install.py
- https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
- https://www.antigravity.google/docs/skills?tab=ide
- https://www.antigravity.google/docs/gcli-migration

Current observations:

- Superpowers supports Antigravity and should remain an external engineering-methodology layer rather than copied project instructions.
- `ui-ux-pro-max` supports Antigravity and substantial UI/UX work; its value is the design-system/accessibility/interaction knowledge layer, not repository setup mechanics.
- Anthropic's `frontend-design` Skill is primarily visual/art-direction guidance; it complements rather than replaces the broader UI/UX/accessibility/design-system role assigned here to `ui-ux-pro-max`.
- Graphify supports Antigravity, local deterministic code parsing, and graph-first navigation; it remains external developer intelligence rather than product/runtime architecture.

Applied policy:

- canonical project docs/ADRs outrank external Skill instructions;
- classify tasks and use the minimum sufficient capability route rather than invoking all available tools;
- Superpowers is mandatory for non-trivial engineering;
- `ui-ux-pro-max` is mandatory only for substantial UI work;
- Graphify is mandatory for broad structural repository analysis after substantive source exists, but not for tiny/local edits;
- optional `frontend-design` and Ponytail passes never become blockers;
- generated developer state stays out of Git by default.
