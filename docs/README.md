# Documentation Index

`docs/` is the detailed source of truth behind `../PROMPT.md`. The set is organized by canonical ownership so Antigravity can load the smallest relevant context instead of one giant prompt.

## First-read path

For a new/bootstrap session:

1. `../AGENTS.md`
2. `../PROMPT.md`
3. `IMPLEMENTATION_STATUS.md`
4. active `ROADMAP.md` phase
5. `DECISIONS.md` + applicable ADRs
6. `DEVELOPMENT_TOOLING.md` to classify the task and determine the minimum sufficient Skill/tool route
7. only the subsystem docs required for the next executable step

For any structural change, add `ARCHITECTURE.md`, `CONTRACT_INVENTORY.md`, and relevant `GLOSSARY.md` terms.

The repository has no project-local development Skills. `DEVELOPMENT_TOOLING.md` exclusively owns external development-capability routing, REQUIRED/OPTIONAL status, blocking, privacy, freshness, and evidence policy. Product Skills/extensions in `MCP_AND_EXTENSIONS.md` are application features and must not be confused with development tooling.

## Authority model

| Authority | Meaning |
| --- | --- |
| **charter** | mission/scope/top-level target |
| **normative** | implementation must conform; architecture/security/contracts may require ADR to change |
| **operational** | how the agent/team executes and validates work |
| **ledger** | factual progress/evidence; code/tests override stale entries |
| **research** | dated external facts; never silently overrides normative docs |

`ARCHITECTURE.md` is additionally marked **FROZEN V1**: its ownership/dependency/trust rules are not implementation suggestions.

### Architecture-documentation coverage

Use arc42-style coverage as a **completeness lens, not another file hierarchy**. The canonical docs already cover the major architecture concerns:

| Architecture concern | Canonical owner(s) |
| --- | --- |
| goals and stakeholders | `PRODUCT_SPEC.md`, `UX_SPEC.md` |
| constraints | `ARCHITECTURE.md`, `SECURITY.md`, accepted ADRs |
| system scope/context | `ARCHITECTURE.md`, `PRODUCT_SPEC.md` |
| solution strategy | `ARCHITECTURE.md`, `DECISIONS.md` |
| building-block/static view | `ARCHITECTURE.md`, `CONTRACT_INVENTORY.md` |
| runtime scenarios | `ARCHITECTURE.md`, subsystem runtime docs, `ROADMAP.md` acceptance paths |
| deployment/process/operations view | `ARCHITECTURE.md`, `OPERATIONS_AND_PRIVACY.md`, `LOCAL_AI.md`, `MODEL_LAB.md` |
| cross-cutting concepts | `SECURITY.md`, `PROMPT_RUNTIME.md`, `TOOL_RUNTIME.md`, `DATA_MODEL.md` |
| architecture decisions | `DECISIONS.md`, `adr/` |
| quality requirements / fitness | `TEST_STRATEGY.md`, architecture fitness rules, performance guardrails |
| risks / deliberate debt | `SECURITY.md`, `TECH_DEBT.md` |
| terminology | `GLOSSARY.md` |

Do not add a duplicate arc42 chapter merely because a topic exists above. Add or split a canonical document only when its current owner becomes materially hard to navigate or validate.

## Canonical owners

| Document | Authority | Owns |
| --- | --- | --- |
| `PRODUCT_SPEC.md` | charter/normative | users, jobs, product areas, scope/non-goals, product principles |
| `UX_SPEC.md` | normative | desktop information architecture and user interaction flows |
| `UI_SYSTEM.md` | normative | UI implementation/design/accessibility/state/validation contract |
| `COMMANDS_AND_WORKFLOWS.md` | normative | slash commands, structured app actions, user-facing modes |
| `ARCHITECTURE.md` | **normative / FROZEN V1** | process/module ownership, dependency DAG, trust boundaries, fitness checks |
| `CONTRACT_INVENTORY.md` | normative | cross-boundary contract owners/stability/change rules |
| `GLOSSARY.md` | normative | canonical terminology and disambiguation |
| `PROMPT_RUNTIME.md` | normative | trusted instruction layers, prompt/context/tool assembly, provenance/compaction |
| `SECURITY.md` | normative | threat model, trust boundaries, permissions, secret handling |
| `DATA_MODEL.md` | normative | persistent entities, ownership, lifecycle, migrations |
| `AGENT_RUNTIME.md` | normative | Task/Run/Turn/Attempt identity, orchestration, cancellation, concurrency, events/recovery |
| `TOOL_RUNTIME.md` | normative | tool invocation/operation identity, permission binding, side-effect/retry semantics, execution/audit/sandbox seam |
| `PROVIDER_SYSTEM.md` | normative | provider/model registry, capability truth, attempt/stream/retry normalization, usage/errors/routing |
| `CONTEXT_ENGINE.md` | normative | repository indexing, retrieval, context planning and compaction inputs |
| `MCP_AND_EXTENSIONS.md` | normative | MCP compatibility plus product Skills/plugins/hooks/trust lifecycle |
| `RESEARCH_AND_BROWSER.md` | normative | search/fetch research and later isolated browser automation |
| `FILES_ARTIFACTS_MEMORY.md` | normative | attachments, artifact lifecycle/versioning, explicit memory |
| `LOCAL_AI.md` | normative | local inference runtimes, model metadata, hardware fit/serving boundaries |
| `MODEL_LAB.md` | normative | immutable dataset/plan/attempt lineage, worker, SFT/LoRA/QLoRA, checkpoints/evaluation/promotion |
| `OPERATIONS_AND_PRIVACY.md` | normative | app data, backup/export, recovery, updates, telemetry/privacy/support bundles |
| `TEST_STRATEGY.md` | operational/normative gates | unit/integration/E2E/evals + architecture fitness strategy |
| `DEVELOPMENT_TOOLING.md` | operational | task-to-capability routing, external development Skills/tools, Graphify privacy/freshness/evidence policy |
| `EXECUTION_PROTOCOL.md` | operational | autonomous bootstrap loop, stop conditions, milestone-gate execution/reporting |
| `IMPLEMENTATION_STATUS.md` | ledger | durable factual progress/resume/evidence |
| `ROADMAP.md` | operational / canonical milestone owner | vertical phase deliverables and acceptance criteria |
| `DECISIONS.md` | normative index | FROZEN/operating/implementation/deferred decisions and ADR linkage |
| `TECH_DEBT.md` | ledger | deliberate compromises and correction triggers |
| `research.md` | research | dated external facts, source links, implementation implications |

## Typical task bundles

Load the smallest useful set:

- **desktop shell/UI:** `UX_SPEC.md`, `UI_SYSTEM.md`, `ARCHITECTURE.md`, `CONTRACT_INVENTORY.md`, relevant `SECURITY.md` section;
- **chat/provider:** `PROVIDER_SYSTEM.md`, `PROMPT_RUNTIME.md`, `CONTRACT_INVENTORY.md`, `DATA_MODEL.md`, `TEST_STRATEGY.md`;
- **coding agent/tools:** `AGENT_RUNTIME.md`, `TOOL_RUNTIME.md`, `SECURITY.md`, `CONTEXT_ENGINE.md`, `ARCHITECTURE.md`;
- **repository context:** `DEVELOPMENT_TOOLING.md`, `CONTEXT_ENGINE.md`, `PROMPT_RUNTIME.md`, `FILES_ARTIFACTS_MEMORY.md`;
- **MCP/extensions:** `MCP_AND_EXTENSIONS.md`, `SECURITY.md`, `TOOL_RUNTIME.md`, `PROMPT_RUNTIME.md`, `CONTRACT_INVENTORY.md`;
- **persistence/migration:** `DATA_MODEL.md`, `ARCHITECTURE.md`, `OPERATIONS_AND_PRIVACY.md`, `TEST_STRATEGY.md`;
- **local inference:** `LOCAL_AI.md`, `PROVIDER_SYSTEM.md`, `SECURITY.md`, `OPERATIONS_AND_PRIVACY.md`;
- **Model Lab:** `MODEL_LAB.md`, `DATA_MODEL.md`, `CONTRACT_INVENTORY.md`, `LOCAL_AI.md`, `SECURITY.md`, `OPERATIONS_AND_PRIVACY.md`;
- **release/recovery/privacy:** `OPERATIONS_AND_PRIVACY.md`, `SECURITY.md`, `DATA_MODEL.md`.

## Source-of-truth rules

- `../PROMPT.md` owns mission/bootstrap target, not subsystem detail.
- `../AGENTS.md` owns always-on agent behavior/authority; `DEVELOPMENT_TOOLING.md` owns capability status, task routing, blocking semantics, freshness/privacy, and route evidence.
- `ARCHITECTURE.md` owns frozen architecture; `CONTRACT_INVENTORY.md` owns cross-boundary contract identity/stability.
- `ROADMAP.md` owns phase deliverables/acceptance; execution/status/test docs reference those criteria rather than redefining them.
- Accepted ADRs explain/supersede decisions, but a frozen change is not current until the canonical owner and tests are updated.
- `research.md` records evidence; it never overrides canonical requirements by itself.
- Code/tests prove implementation reality. Docs must not claim unimplemented behavior works.

## Update discipline

Update the canonical owner in the same change whenever behavior changes a public/internal stable contract, schema, trust boundary, architecture edge, prompt/context behavior, provider semantics, extension contract, UX contract, operational behavior, or roadmap acceptance criterion.

Prefer references to canonical owners over copying the same rule into many files. Where a rule can be tested mechanically, add/maintain a fitness test rather than relying on prose alone.
