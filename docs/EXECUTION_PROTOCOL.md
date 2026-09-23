# Autonomous Execution Protocol

> **Authority:** operational bootstrap contract
> **Goal:** let Antigravity resume and execute the active roadmap slice without repeatedly asking the user to make routine engineering choices.

## 1. Start / resume sequence

At the beginning of a bootstrap or resumed long run:

1. read `../AGENTS.md`;
2. read `../PROMPT.md`;
3. read `IMPLEMENTATION_STATUS.md`;
4. inspect Git/workspace state and existing code/build/test setup;
5. read the active `ROADMAP.md` phase;
6. read `DECISIONS.md` and applicable ADRs;
7. for structural work, read `ARCHITECTURE.md`, `CONTRACT_INVENTORY.md`, and relevant `GLOSSARY.md` terms;
8. read `DEVELOPMENT_TOOLING.md` to classify the task and determine the minimum sufficient capability route;
9. load only subsystem docs needed for the next executable step;
10. update the status ledger with facts discovered before making material changes.

Do not reset or re-scaffold coherent existing work merely because the bootstrap docs describe a fresh-repository path.

## 2. Required capability routing

Use `DEVELOPMENT_TOOLING.md` as the **only authority** for which external capabilities are required/optional, when they are blocked, and what evidence/freshness/privacy rules apply.

For each material slice:

1. classify the task and select the minimum sufficient route there;
2. use the required capabilities before the work stage they govern;
3. record the selected route, actual capability use, and any route-specific evidence in `IMPLEMENTATION_STATUS.md`;
4. if a required capability is unavailable, apply that document's blocking semantics rather than inventing a substitute or claiming the route passed.

Do not duplicate capability-specific policy in this protocol.

## 3. Bootstrap loop

Repeat until the active gate passes or a hard blocker is reached:

1. **Inspect** — code, tests, docs, Git state, current failure/evidence.
2. **Activate route** — use only the required capabilities selected by `DEVELOPMENT_TOOLING.md`.
3. **Specify the slice** — smallest coherent change + acceptance evidence.
4. **Implement** — preserve frozen architecture and current milestone scope.
5. **Validate locally** — targeted tests/checks first.
6. **Review the real diff** — correctness, security, architecture, complexity, docs.
7. **Fix review findings** — do not only report them.
8. **Run the milestone gate** — wider validation/build/E2E as appropriate.
9. **Persist facts** — status, commands/results, decisions, blocker, next executable step.
10. **Continue** — do not stop merely because one task/commit is complete.

## 4. Decision policy

### Make autonomously

Routine reversible choices inside frozen boundaries, such as:

- internal names and small file composition;
- test placement;
- maintained library selection among compatible alternatives;
- state-management approach;
- exact schema/IPC/dependency-check tooling;
- small UX/component composition consistent with UX/UI contracts.

### Record as ADR

Use an ADR when a choice is cross-cutting, difficult to reverse, compatibility-sensitive, security-sensitive, introduces a new architectural owner/contract, or changes an accepted decision.

### Frozen architecture change

Do not implement a change to a FROZEN rule unless the `ARCHITECTURE.md` change protocol is satisfied. A proposed ADR alone is not permission to violate the current baseline.

## 5. Hard blockers

Stop only when the next required step cannot safely proceed because of one of these:

- platform/tooling requires user approval that the agent cannot provide;
- account/credential/external service action is genuinely required and no deterministic/local path exists;
- destructive or externally irreversible action requires user intent;
- material product requirement contradiction cannot be resolved from canonical docs;
- required external development Skill is unavailable at the point that work depends on it;
- a frozen architecture rule is demonstrably blocking and material change needs user approval;
- environment/runtime failure has no safe local fallback and prevents the active acceptance gate.

A routine library choice, naming choice, test organization question, or reversible implementation detail is not a blocker.

## 6. Research policy

Research only current external facts that can change correctness, compatibility, security, architecture, or implementation of the active slice.

Prefer primary sources. Record dated findings and their implementation consequence in `research.md`.

A research note cannot silently supersede a frozen or normative requirement. If external evidence requires architecture change, use the superseding-ADR path.

## 7. Milestone gate execution

`ROADMAP.md` is the **single canonical owner** of phase deliverables and acceptance criteria. This protocol defines how to execute those gates, not a second copy of them.

For the bootstrap run:

1. finish and prove `ROADMAP.md` Phase 0 before treating the foundation as complete;
2. then prove the deterministic Phase 1 chat acceptance slice using `TEST_STRATEGY.md`;
3. use deterministic/local evidence for required gates; paid APIs, personal credentials, and live-provider access are never prerequisites;
4. do not advance with an unresolved foundational security/build/architecture-fitness failure;
5. record exact evidence in `IMPLEMENTATION_STATUS.md`.

A live/local provider smoke is supplemental when already authorized/configured. Never request secrets merely to pass a bootstrap gate.

## 8. Root command contract

For a fresh repository expose root scripts, or equivalent documented commands for an established project:

- `format`
- `format:check`
- `lint`
- `typecheck`
- `test`
- `test:integration`
- `test:e2e`
- `test:architecture` (or clearly equivalent architecture-fitness command)
- `build`

Before claiming the bootstrap gate, run applicable formatting/check, lint, typecheck, unit, integration, architecture, deterministic E2E, and production build commands. Record exactly what ran and its result.

## 9. Long-run/context compaction

Use `IMPLEMENTATION_STATUS.md` as durable session memory. Before context compaction or a natural long-run checkpoint, persist:

- current milestone/gate status;
- verified repository facts;
- selected capability route and required-capability evidence;
- accepted implementation decisions/ADRs;
- commands and results;
- current blocker, if any;
- important changed files/subsystems;
- exact next executable step.

Do not repeatedly reread unchanged large docs when targeted context is enough.

## 10. Self-review before gate completion

Inspect the actual diff/code and prove:

- frozen architecture edges/ownership are preserved;
- architecture fitness checks cover real forbidden paths;
- provider payloads did not leak into application/UI/agent contracts;
- renderer cannot access secrets/DB/unrestricted filesystem/shell/MCP transports;
- Tool Runtime/Policy Core cannot be bypassed by effectful agent/MCP/extension paths;
- migrations/restart persistence are tested;
- fake provider is isolated from production;
- cancellation/error paths exist;
- secrets are absent from normal persistence/log/prompt fixtures;
- required UI work satisfied the UI capability route and was rendered/reviewed where possible;
- docs/contract inventory match implementation reality;
- no later-phase system was accidentally built instead of the active gate.

Fix material findings when possible before declaring success.

## 11. Completion report

Report verified facts only:

- overall bootstrap status;
- Phase 0 result;
- deterministic Phase 1 E2E result;
- selected capability route and required-capability evidence;
- architecture-fitness result;
- commands/tests actually run;
- live-provider smoke separately, if any;
- important ADRs/implementation decisions;
- blocker/limitation, if any;
- exact next roadmap milestone/step.
