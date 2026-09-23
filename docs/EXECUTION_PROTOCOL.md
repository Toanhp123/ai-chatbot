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

Classify the current task using the routing matrix in `DEVELOPMENT_TOOLING.md`. Use the **minimum sufficient route**; available capabilities are not all mandatory on every task.

Before non-trivial code work, use the relevant **Superpowers** Skill(s). Record the workflow/skills actually used in `IMPLEMENTATION_STATUS.md`. Accepted/FROZEN canonical docs are already-approved design input: a Skill workflow must not cause the agent to re-ask the user to approve settled baseline decisions. Only net-new material choices or hard blockers require user input.

Before substantial UI work, also use **`ui-ux-pro-max`**. Record its use. Use `frontend-design` only when a distinct visual-refinement pass adds value. Ponytail is optional and limited to simplicity/YAGNI review.

Once substantive source exists, use Graphify when the route requires broad structural knowledge. For repository-wide architecture/dependency/impact work, use a current local code-structure graph before broad raw search. Graph queries narrow where to inspect; consequential conclusions still require source/tests and, where applicable, architecture-fitness evidence.

The repository must not create project-local Skill copies or generated Graphify rule/workflow files as a fallback.

Missing capability behavior:

- missing Superpowers blocks non-trivial implementation/refactor/debug/review work;
- missing `ui-ux-pro-max` blocks substantial UI work only; continue independent backend/docs/research work when possible;
- missing Graphify does not block demonstrably narrow local implementation, but broad repository architecture/impact assertions require equivalent explicit evidence and the Graphify-specific gate must not be claimed as passed;
- missing optional refinement capabilities never blocks the active gate;
- record the blocker precisely instead of pretending compliance.

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

## 7. Phase 0 foundation gate

Phase 0 is complete only when executable evidence proves:

- workspace/package setup installs/builds on the primary development OS;
- frozen logical boundaries are reflected in the scaffold as responsibilities become real;
- secure Electron main/preload/renderer split exists;
- renderer cannot directly use Node/filesystem/provider/storage/tool/MCP internals;
- typed versioned IPC/application boundary exists for implemented flows;
- React/Electron-independent core packages build/test independently;
- SQLite migrations create and reopen storage deterministically;
- `SecretStore` abstraction exists with detectable degraded-security state;
- structured logging/redaction foundation exists;
- Prompt Runtime and normalized provider request/event contracts exist;
- deterministic fake-provider harness exists behind Provider Core;
- architecture fitness tests enforce the frozen dependency/trust rules;
- root validation commands are stable/documented;
- the initial shell UI was designed/implemented using `ui-ux-pro-max` and satisfies the UI contract;
- foundational docs/ADRs match the actual scaffold.

Do not advance with an unresolved foundational security/build/architecture-fitness failure.

## 8. Phase 1 deterministic E2E gate

The mandatory acceptance path requires no paid API, personal credential, or internet dependency.

Use a local deterministic fake provider through the **same normalized Provider Core seam** used by real providers. It is development/test-only and must be structurally unable to register in normal production configuration/runtime.

Mandatory flow:

1. launch the desktop app in an isolated test profile/data root;
2. configure/select the fake provider through normal application/runtime seams where practical;
3. select a deterministic fake model;
4. create a conversation;
5. submit a message;
6. stream normalized events through the real application/agent/prompt/provider path;
7. render final assistant content;
8. persist conversation, messages, and usage metadata;
9. close cleanly;
10. relaunch with the same isolated profile;
11. verify persisted conversation/usage is still available;
12. cover cancellation and at least one normalized provider failure in integration/E2E evidence.

A live/local provider smoke is supplemental when already authorized/configured. Never request secrets merely to pass the bootstrap gate.

## 9. Root command contract

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

## 10. Long-run/context compaction

Use `IMPLEMENTATION_STATUS.md` as durable session memory. Before context compaction or a natural long-run checkpoint, persist:

- current milestone/gate status;
- verified repository facts;
- external Skill availability/use;
- accepted implementation decisions/ADRs;
- commands and results;
- current blocker, if any;
- important changed files/subsystems;
- exact next executable step.

Do not repeatedly reread unchanged large docs when targeted context is enough.

## 11. Self-review before gate completion

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
- required UI work used `ui-ux-pro-max` and was rendered/reviewed where possible;
- docs/contract inventory match implementation reality;
- no later-phase system was accidentally built instead of the active gate.

Fix material findings when possible before declaring success.

## 12. Completion report

Report verified facts only:

- overall bootstrap status;
- Phase 0 result;
- deterministic Phase 1 E2E result;
- required capability route and external Skills/tools actually used;
- architecture-fitness result;
- commands/tests actually run;
- live-provider smoke separately, if any;
- important ADRs/implementation decisions;
- blocker/limitation, if any;
- exact next roadmap milestone/step.
