# Development Tooling Contract

> **Authority:** operational development contract
> **Scope:** external coding-agent Skills and developer-only repository intelligence. None of these capabilities are product runtime dependencies.

## 1. Purpose

Use external agent capabilities deliberately without turning the repository into a collection of copied Skills, generated agent rules, setup notes, or tool-specific boilerplate. Development tooling improves **how** the codebase is understood, designed, implemented, debugged, and reviewed; it never redefines **what** the product or frozen architecture is.

The core rule is **minimum sufficient routing**: use only the capabilities required for the current task, in a predictable order, and verify their outputs against canonical docs, source, and tests.

This repository names external capabilities and defines when to use them; tool-specific setup belongs to the capability itself. If a required capability is unavailable, follow the blocking semantics below and do not recreate it inside the product repository.

## 2. Capability inventory

| Capability | Status | Primary role |
| --- | --- | --- |
| Superpowers | REQUIRED for non-trivial engineering | planning, TDD/debugging discipline, implementation, verification, review |
| `ui-ux-pro-max` | REQUIRED for substantial UI | UI/UX knowledge, design-system choices, interaction, accessibility, desktop/React implementation |
| Graphify | REQUIRED after substantive source exists for broad structural analysis | repository graph, dependency/path/impact analysis, unfamiliar subsystem tracing |
| `frontend-design` | OPTIONAL | distinctive visual/art-direction refinement |
| Ponytail | OPTIONAL | simplicity/YAGNI/anti-over-engineering review |

## 3. Task routing policy

Classify the task before using external capabilities. A task may match multiple rows; use the union of **required** capabilities without adding unrelated ones.

| Task shape | Required route | Optional | Do not do |
| --- | --- | --- | --- |
| typo, tiny copy/docs correction, obvious localized config edit | canonical owner + direct edit/validation | none | invoke the full engineering stack |
| non-trivial feature/refactor | Superpowers + relevant subsystem docs/tests | Graphify if cross-module/impact is broad | use UI Skills for backend-only work |
| non-trivial bug/debugging | relevant Superpowers debugging workflow + failing evidence | Graphify when cause crosses modules or entry point is unclear | guess/fix before reproducing where reproduction is feasible |
| new screen/shell, major flow, redesign, design-system/accessibility work | Superpowers + `ui-ux-pro-max` + `UI_SYSTEM.md` + `UX_SPEC.md` | `frontend-design` for art-direction refinement; Graphify if UI change crosses architectural owners | substitute screenshots/taste for product UX contracts |
| small UI maintenance inside an established pattern | Superpowers if non-trivial + existing UI contracts | `ui-ux-pro-max` when design/accessibility decisions change | force a redesign pass for mechanical edits |
| repository-wide dependency/impact question, unfamiliar cross-module tracing, structural review | Graphify first once source exists + targeted source/tests; Superpowers when it leads to code/review work | architecture docs/fitness checks | broad grep/read as the first structural strategy when a current graph is available |
| architecture change or suspected frozen-boundary conflict | Superpowers + `ARCHITECTURE.md`/`CONTRACT_INVENTORY.md` + Graphify when source exists + source/tests/fitness evidence | ADR research | change a FROZEN rule from graph output or agent preference alone |
| code review | relevant Superpowers review workflow + actual diff/tests | Graphify for cross-module/architectural claims; Ponytail for complexity pass | review only the plan instead of the diff |
| external/version/security/protocol fact | primary-source research + record material dated finding in `research.md` | Graphify only if repository impact also matters | treat stale research notes as current fact |
| docs-only product/architecture clarification | canonical docs + accepted ADRs | Superpowers only if the change is a material design/architecture exercise | require Graphify when no code evidence is needed |

### Routing sequence

For a non-trivial task:

1. identify task class and active acceptance gate;
2. load the smallest canonical doc bundle;
3. use the relevant Superpowers Skill(s);
4. for substantial UI, use `ui-ux-pro-max` before design/implementation;
5. when broad structural repository knowledge is needed and substantive source exists, use Graphify before broad raw search;
6. inspect the exact source/tests identified by the route;
7. implement and validate narrowly;
8. run required wider gates and architecture fitness;
9. optionally use `frontend-design` for visual refinement or Ponytail for a simplicity pass when they add real value;
10. self-review the actual diff and persist evidence.

Capability count is not a quality metric. Do not use Graphify merely because code exists, and do not use UI Skills for non-UI work.

## 4. Availability and blocking semantics

- **Superpowers unavailable:** non-trivial implementation/refactor/debug/review is blocked. Independent factual research and small docs-only work may continue.
- **`ui-ux-pro-max` unavailable:** substantial UI work is blocked. Independent backend/docs/research work may continue. Because Phase 0 includes a substantial shell UI, Phase 0 cannot close until this capability is available.
- **Graphify unavailable:** narrow/local code work may continue when impact is demonstrably bounded. Broad repository architecture/dependency/impact claims are blocked unless equivalent explicit evidence is gathered; do not claim Graphify-backed validation occurred when it did not.
- **Optional capability unavailable:** continue without it; never turn an optional refinement into a blocker.

Availability does not imply use on every task.

## 5. External capability boundary

External Skills/tools are **execution methodology**, not repository content.

- use the capability by its canonical name and let its current instructions define its own invocation details;
- do not copy Skill bodies, generated rules/workflows, or environment-specific tool plumbing into this repository;
- do not let a Skill/tool modify FROZEN architecture, product scope, security policy, or canonical contracts on its own authority;
- record required-capability absence as a blocker at the point where it matters.

Canonical project docs and accepted ADRs outrank external capability instructions.

## 6. Superpowers operating model

Use Superpowers for non-trivial engineering work and select the relevant workflow for the task: planning, implementation, debugging, testing, or review.

Canonical/FROZEN project docs are already-approved design input. A Superpowers design/approval checkpoint does not reopen settled decisions. Ask the user only for a genuinely new material product/architecture choice or a protocol-defined hard blocker.

Superpowers is methodology, not product architecture. Its worktree/task/review mechanics must still respect repository Git state, frozen boundaries, permissions, and completion gates.

## 7. UI capability model

Use `ui-ux-pro-max` for substantial UI/UX work. `UI_SYSTEM.md` and `UX_SPEC.md` remain authoritative for product states, desktop interaction, architecture, accessibility, and validation gates.

Use `frontend-design` only when an additional art-direction/taste pass is useful. It may refine a chosen direction but cannot override product UX or accessibility constraints.

Use Ponytail only for an explicit simplicity/YAGNI pass after correctness and architecture are established. It must not drive removal of required abstractions such as Policy Core, Prompt Runtime, or normalized provider/tool boundaries.

## 8. Graphify operating model

Use Graphify for broad dependency/path/impact analysis, unfamiliar subsystem tracing, and structural review once substantive source exists.

For normal repository analysis, prefer Graphify's local/code-structure mode and keep repository intelligence advisory. When a current graph is available, query it before broad raw search for questions such as:

- which modules/types/functions are connected to X;
- what depends on or reaches Y;
- what areas may be affected by a cross-cutting change;
- where an unfamiliar subsystem's structural entry points are;
- whether an implementation appears to cross expected package boundaries.

Then open the exact source, tests, and contracts needed to verify consequential conclusions.

Graphify confidence is not architectural authority:

- **extracted/observed relationships** are useful navigation evidence but still require verification when consequential;
- **inferred relationships** are hypotheses requiring source evidence;
- **ambiguous relationships** are not conclusions until resolved.

Never change a FROZEN architecture rule solely because graph output suggests a different design.

## 9. Graph freshness and privacy

Treat Graphify's repository graph as local, regenerable developer state. Refresh it when relevant structural code has materially changed or when graph results conflict with observed source.

Keep secrets, credential stores, private datasets, downloaded models, user-profile data, build caches, and generated application data out of developer repository analysis. Semantic/model-backed analysis of non-code repository content is opt-in and requires privacy review before use.

Do not commit generated graph state or enable automatic repository hooks by default. If the team later wants shared graph artifacts or automation, make that a deliberate operating decision with freshness, privacy, CI, and merge behavior defined.

## 10. Relationship to the product Context Engine

Graphify is a **developer capability used to build this repository**. It is not the implementation of the application's Context Engine, repository index, retrieval layer, or product memory.

Do not import Graphify as a product dependency or make product correctness depend on Graphify unless a future product ADR explicitly evaluates and approves that change.

The product Context Engine must satisfy `CONTEXT_ENGINE.md`, its tests, privacy boundaries, and user-facing requirements independently.
