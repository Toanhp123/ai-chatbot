# AGENTS.md — AI-Train / My-AI V2

## 0. Role

This is an **agent operating guide**, not an architecture specification.

Its purpose is to keep Codex/agents aligned with V2 while minimizing unnecessary context, broad refactors, and architecture drift.

Authoritative order:

```text
1. v2-architecture-baseline-r1.md        # frozen architecture law
2. v2-architecture-development-map-r1.md # living branch/slice navigation
3. selected Capability Spec
4. selected Slice Plan
5. current code/tests
```

If lower-level material conflicts with higher-level material, the higher-level source wins.

`AGENTS.md` must never redefine architecture already owned by those documents.

---

## 1. Project Mission

V2 is a **clean-slate backend architecture**.

Legacy `src/` is **architecture archaeology only**.

Legacy code may provide:

- proven behavior;
- algorithms/mechanics;
- edge cases;
- tests;
- useful artifact/data formats.

Legacy code must not define V2:

- topology;
- class hierarchy;
- service/facade graph;
- dependency direction;
- compatibility surface;
- application architecture.

Do not "refactor V1 until it becomes V2".

---

## 2. Context Loading — Optimize First

**Never start by reading the whole repository.**

Before opening implementation files, determine:

```text
1. requested product outcome
2. owning branch
3. owning slice
4. blocking architecture questions
5. required dependency contracts
```

Then load context in this order:

```text
Baseline
→ Development Map
→ selected branch/slice docs
→ direct public dependency contracts
→ targeted implementation files
→ targeted tests
→ legacy archaeology only if needed
```

Expand outward only when blocked by an unclear contract, failing boundary, or missing dependency.

Do not recursively inspect unrelated capabilities.

---

## 3. Branch / Slice Protocol

Work must map to a concrete capability branch and vertical slice.

Examples:

```text
FND-Sx
GEN-Sx
CONV-Sx
MOD-Sx
DATA-Sx
TOK-Sx
TRN-Sx
EVAL-Sx
```

Do not implement vague scopes such as:

```text
finish Training
improve Generation
clean Models
refactor backend
```

Convert them to the smallest real end-to-end slice.

If a requested behavior does not fit an existing slice, define the smallest new slice consistent with the Development Map.

---

## 4. Question Protocol

Use branch-local questions such as:

```text
GEN-Qxx
MOD-Qxx
DATA-Qxx
TRN-Qxx
EVAL-Qxx
```

Do not create `Q121+` unless implementation exposes a genuine architecture-level contradiction requiring Baseline revision.

For the selected slice, classify questions:

```text
LOCKED
OPEN-BLOCKER
OPEN-LATER
DEFERRED
INVALID
```

Resolve only `OPEN-BLOCKER` questions before implementation.

Do not design the entire future branch in advance.

---

## 5. Hard Architecture Guardrails

These are non-negotiable unless the Baseline is formally revised.

### Ownership

Each capability owns its:

- semantics;
- state machine;
- lifecycle/recovery policy;
- persistence meaning;
- public contracts.

Cross-capability interaction uses explicit public contracts.

Never import another capability's internals.

### DAG

The dependency graph must remain acyclic statically **and** at runtime orchestration level.

Do not hide cycles through callbacks, global registries, event loops, facade chains, or runtime lookup.

### Platform

`platform/` contains only genuinely cross-domain mechanics.

Do not recreate a dumping ground such as `core/`, `common/`, `utils/`, `helpers/`, `services/`, or `managers/` without one clear owner/responsibility.

### Application

Use application orchestration only for real use-case/cross-capability policy.

Avoid 1:1 forwarding services and facade chains.

### Composition

Only the Composition Root knows concrete implementations.

No Service Locator or hidden dependency construction.

### Persistence

- SQLite is V2's official DB.
- DB owns durable domain state/metadata truth.
- ArtifactStore owns large-byte mechanics.
- runtime state is ephemeral.
- no dual source of truth.

### Workers

Workers receive resolved typed input and return typed events/results/failures.

Workers never own business DB/state and never receive ORM entities, DB connections, arbitrary callables, or pickle-coupled business objects.

Workers may write staged bytes only; coordinator/domain validation must precede durable artifact references.

### API / boundaries

Do not leak across business/API boundaries:

- ORM models;
- provider SDK objects;
- raw exception strings as business contracts;
- raw filesystem paths;
- plaintext secrets.

### Generation / Training

Generation must work independently from Training.

Correct product flow:

```text
Training Output
→ Model Registry
→ explicit Publication
→ GenerationTarget
→ Generation
```

Generation must never depend back on Training internals.

---

## 6. No Speculative Architecture

Do not create architecture for hypothetical future needs.

Avoid:

- empty future capability packages;
- placeholder interfaces;
- generic Base classes;
- GenericRepository / RepositoryManager;
- generic job queues;
- global managers;
- capability/service registries;
- speculative plugin frameworks;
- abstractions with only hypothetical consumers.

A new abstraction must be justified by the selected real slice.

---

## 7. Dependency Gate Rule

Before implementing a slice, verify its dependency gates from the Development Map.

If blocked by another capability:

```text
DO NOT:
refactor or implement the entire adjacent capability.

DO:
add/freeze the smallest dependency contract or dependency slice required.
```

Keep adjacent changes minimal and explicit.

---

## 8. Scope Control

While implementing one slice:

- do not improve unrelated modules;
- do not rename/restructure neighbors for aesthetics;
- do not port unrelated legacy code;
- do not implement future slices opportunistically;
- do not mass-format unrelated files.

Touch another capability only when the selected slice is blocked by its public contract.

Prefer small, reviewable patches.

---

## 9. Vertical Slice Standard

A slice is not complete because a class exists or unit tests are green.

Where relevant, a real slice covers:

```text
product/user input
→ stable capability entry point
→ semantic validation
→ reference resolution
→ submitted intent
→ resolved execution decision
→ explicit state transition
→ execution
→ persistence/artifacts
→ events
→ typed terminal result/failure
→ API/frontend-observable behavior
```

Every slice must remain runnable and testable end to end.

---

## 10. Execution / Historical Truth

Preserve these distinctions:

```text
Operation != ExecutionAttempt
Deadline != QueueDeadline != ProviderTimeout != WorkerHeartbeatTimeout != Cancellation
submitted intent != resolved execution snapshot != terminal outcome
partial output != completed result
```

Semantic execution intent is frozen before queueing.

Only volatile runtime/resource feasibility may be revalidated later.

Terminal historical truth must not drift when live resources/settings change.

---

## 11. Validation / Transactions / Resources

Validation ownership:

```text
API     → shape/transport
Domain  → semantic invariants
Planner → feasibility/resources
Driver  → provider/runtime compatibility
```

Keep SQLite transactions short.

Never hold a DB transaction while waiting for provider calls, workers, model loading, or long I/O.

Scarce resources must be admitted through explicit planning + `ResourceLease`/reservation semantics.

Workers must not self-claim scarce GPU/RAM.

---

## 12. Archaeology Protocol

When inspecting old `src/`, classify findings explicitly:

```text
MUST KEEP
KEEP + REDESIGN
FUTURE
DELETE
```

Prefer reuse of behavior/tests/algorithms, not topology.

Common redesign/delete candidates include:

- CLI-only product flow;
- debug/explorer internals that are not real product inspection;
- god config objects;
- generic service/repository patterns;
- compatibility wrappers preserving old topology;
- hidden global runtime state.

---

## 13. Code Style for Architecture

Prefer:

- explicit names;
- narrow public surfaces;
- immutable refs where reproducibility requires them;
- constructor injection;
- capability-owned types;
- typed failures;
- deterministic pure logic;
- synchronous pure domain logic;
- async only for I/O/realtime.

Avoid generic `Service`, `Manager`, `Helper`, or `Utils` names unless responsibility is explicit and justified.

---

## 14. Testing Strategy

Run the smallest tests that can falsify the change first:

```text
1. targeted unit/contract tests
2. selected capability tests
3. architecture/boundary tests
4. persistence/recovery tests when relevant
5. API/transport tests when relevant
6. selected slice E2E
7. broader suite only when impact justifies it
```

A green suite does not override an architecture violation.

Tests must prove behavior **and** boundaries.

---

## 15. Mandatory Self-Review Before Completion

Inspect the final diff before claiming completion.

Check:

### Ownership
- one clear capability owner per behavior?
- business policy leaked outward?
- `platform/` gained domain semantics?

### Dependencies
- reverse dependency introduced?
- another capability's internals imported?
- cycle hidden by callback/registry/facade?

### Scope
- unrelated files changed?
- future work implemented?
- speculative abstraction introduced?

### Persistence / execution
- dual source of truth created?
- historical truth can drift?
- worker gained business-DB authority?
- staged output referenced before validation?
- deadline/timeout/cancellation collapsed?

### Contracts
- SDK/ORM/raw-path details leaked?
- failures typed?
- public surface kept minimal?

### Tests
- happy path covered?
- important failures covered?
- state transitions covered?
- recovery/restart covered when relevant?
- architecture boundary executable?
- selected slice E2E proven?

Fix discovered issues before reporting completion.

---

## 16. Documentation Update Rule

Update the narrowest correct source of truth:

```text
architecture-level contradiction
→ explicit architecture review / Baseline revision

branch roadmap or question status
→ Development Map / branch doc

public capability semantics
→ Capability Spec

selected implementation steps
→ Slice Plan

performance/tuning detail
→ policy or benchmark notes
```

Do not silently mutate the frozen Baseline.

Do not duplicate the same decision across multiple docs without a clear owner.

---

## 17. Status Vocabulary

Branch:

```text
MAPPED | QUESTIONS_OPEN | SPEC_READY | ACTIVE | STABLE | DEFERRED
```

Slice:

```text
PROPOSED | BLOCKED | READY | IMPLEMENTING | VERIFYING | DONE
```

Question:

```text
OPEN-BLOCKER | OPEN-LATER | LOCKED | DEFERRED | INVALID
```

Do not report `DONE` unless required verification actually ran successfully.

---

## 18. Working Discipline

Do not commit, push, merge, rewrite history, or discard user changes unless explicitly requested.

Do not add temporary/generated repository files unless required by the selected slice.

For large tasks, work slice-by-slice rather than performing a broad rewrite.

Default architecture direction when no more specific plan exists:

```text
FND minimum
→ Remote Generation
→ Conversation
→ Local Models / Runtime
→ Dataset
→ Training
→ Evaluation
→ real future Knowledge / Tools / Agents slices
```

A branch may advance out of this order only when its dependency gates are satisfied and the DAG remains valid.

---

## 19. Completion Report

For implementation work, report concisely:

```text
Branch / Slice
Implemented
Architecture decisions locked
Files changed
Verification commands + results
Self-review findings fixed
Remaining blockers / OPEN-LATER
```

If verification was not run, say so explicitly.

---

## 20. Final Agent Check

At all times be able to answer:

```text
WHERE am I in the capability graph?
WHICH branch owns this behavior?
WHICH slice am I implementing?
WHICH questions block this slice?
WHICH stable contracts does it consume?
WHAT evidence proves it complete?
```

If these answers are unclear, do not broaden implementation.

Return to the Baseline + Development Map, narrow the scope, and proceed from the smallest valid vertical slice.
