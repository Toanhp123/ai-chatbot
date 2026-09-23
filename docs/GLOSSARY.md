# Canonical Glossary

> **Authority:** canonical terminology for project docs/code.
> **Rule:** reuse these terms rather than inventing near-synonyms for the same concept.

## Development terms

**Superpowers**
External development Skill methodology used by Antigravity for non-trivial engineering. It is not a feature of the product being built.

**`ui-ux-pro-max`**
External development Agent Skill required for substantial frontend/UI design, implementation, accessibility/interaction work, and UI review. It supplies design intelligence and stack-specific guidance but does not define this product's architecture or scope.

**`frontend-design`**
Optional external companion Skill for a second-pass visual/taste refinement. It never replaces the required `ui-ux-pro-max` workflow.

**Ponytail**
Optional external coding-simplicity/YAGNI Skill. It is not the project's UI-design Skill.

**Graphify**
External developer-only codebase intelligence tool/Skill used for broad dependency, path, impact, and unfamiliar-subsystem analysis after substantive source exists. Its graph is advisory evidence, not product runtime state or architectural authority.

**Development capability route**
The minimum set of external Skills/tools required for a specific engineering task under `DEVELOPMENT_TOOLING.md`; available capabilities are not all used by default.

## Product/runtime terms

**App Host / Composition Root**
Electron main-side wiring layer that owns desktop lifecycle and binds concrete adapters to application/core interfaces. It is not the business-logic layer.

**Application / Use Case**
User-facing orchestration boundary between presentation and core/runtime services.

**Agent Task**
Durable user goal/work item. A Task can have multiple execution Runs across interruption/resume; it is not the same thing as one process lifetime or one provider request. Do not conflate with MCP Tasks.

**Agent Run**
One concrete execution/resume of an Agent Task. A crashed/interrupted Run is not revived in place; resumption creates a new Run linked to prior evidence.

**Agent Turn**
One decision cycle within a Run: context/request preparation, one-or-more provider attempts as allowed, resulting assistant/tool decisions, and transition to the next cycle.

**Model Attempt**
One concrete call to a provider/model candidate. Retry and fallback attempts keep distinct identities, usage, errors and provider request metadata. Compatible attempts may bind the same immutable provider-neutral semantic request; the model/provider choice belongs to the attempt.

**Operation fingerprint**
Stable normalized identity of the effect-bearing semantics of a pending tool operation (tool/version, canonical resources, normalized argument identity, risks and relevant preconditions). Used to bind approval/re-evaluation; not a cryptographic authorization token.

**Workspace mutation lease**
Runtime ownership token indicating which Run may mutate a physical workspace root. It prevents concurrent application-managed V1 writers but never replaces Policy Core permission or file/revision preconditions against external edits.

**Tool Call**
One logical application-owned tool invocation requested by a model/agent. It has a stable `toolCallId` independent of any provider-native tool-use identifier.

**Tool Attempt**
One concrete dispatch/retry of a Tool Call, identified by `toolAttemptId`. Safe retries create new Tool Attempts under the same logical Tool Call; ambiguous dispatched attempts are preserved/reconciled rather than hidden by a new call.

**MCP Task**
A task primitive defined by an MCP extension/profile when supported. It is remote protocol/server execution state, not the internal Agent Task/Run model.

**Provider**
A configured inference transport/service integration such as a vendor API, compatible gateway, router, or local runtime endpoint.

**Model**
A selectable model/capability record exposed by a Provider.

**Route**
Configured ordered/policy-constrained set of provider/model candidates.

**RoutePlan**
Immutable per-turn resolution of a Route: eligible candidate snapshots plus the shared capability/context/output envelope that all transparent-fallback candidates must honor for one prepared request.

**Provider Core**
The sole boundary for provider-specific transport, payload translation, stream/error/usage normalization, model metadata, and routing behavior.

**Prompt Runtime**
Trusted instruction precedence, provenance framing, context/tool packing, compaction representation, and provider-neutral model-request assembly.

**PreparedModelRequest**
Immutable provider-neutral request snapshot produced by Prompt Runtime for one Agent Turn. Its semantic content/config fingerprint is stable across compatible transparent fallback attempts; provider/model choice belongs to each Model Attempt.

**Context Engine**
Repository/workspace evidence discovery, parsing, indexing, retrieval, ranking, token budgeting, and context-plan generation.

**ContextPackage**
Immutable provenance-aware evidence snapshot produced by Context Engine for one turn/request plan. It contains retrieved evidence, not authoritative instruction precedence.

**Tool**
A callable capability with a typed schema and normalized invocation/result lifecycle. Effectful tools execute through Tool Runtime + Policy Core.

**Tool Runtime**
Central registry/execution lifecycle for tools, including validation, permission mediation, timeout/cancel, output normalization, and audit.

**Policy Core**
Pure authorization/policy decision boundary for effectful operations. Policy decides; Tool Runtime executes.

**Product Skill**
An application extension that contributes focused instructions/resources through progressive disclosure from an immutable revision that is activated in an explicit scope. Local/package/MCP-delivered Skills converge on this one runtime **without erasing source trust class**; MCP-served Skill content remains remote-untrusted instructional input. Product Skills never grant runtime permission and bundled scripts never auto-execute.

**Extension revision**
Immutable reviewed snapshot of a plugin/Skill/MCP-server contribution source and its security-relevant metadata. Activation is a separate scoped association to this revision. Updating source bytes, endpoint/command, executable components or requested capabilities creates a new revision rather than silently inheriting trust.

**Workspace trust**
App-owned trust state for a canonical workspace/root. In restricted state, repository content remains usable as untrusted evidence but repository-controlled instructions, Skills/plugins/hooks/commands do not automatically gain trusted/executable authority.

**Extension**
Installable/configurable product contribution such as Skills, agent configs, MCP definitions, hooks, or future plugin bundles, governed by Extension Core.

**MCP Host**
Boundary that speaks supported MCP protocol profiles/transports and converts remote primitives/extensions into app-owned descriptors/adapters. Server self-reported identity and cache metadata are not authorization/trust evidence.

**Local runtime ownership**
Whether a local inference process is externally owned, explicitly app-managed, or unknown. Cleanup/stop operations act only on process identity the app actually owns.

**Project**
A durable product entity grouping one or more workspace roots plus project instructions/config/context state.

**Workspace root**
A user filesystem directory attached to a Project. A Project may contain multiple roots.

**Profile / data root**
Isolated application state namespace. Production, tests, and special runs must not accidentally share data/secrets.

**SecretStore**
Abstraction over platform secure secret storage. The DB stores opaque references/metadata, not secret values.

**Artifact**
A durable/versionable user-visible output such as generated document/code/research result, distinct from ephemeral model/tool stream events.

**Checkpoint**
A restorable representation of workspace mutation state used by coding-agent flows. It must preserve unrelated pre-existing user work.

**Fake Provider**
Deterministic development/test-only provider harness used through the same normalized provider boundary as real providers. It must be impossible to register in production runtime/configuration accidentally.

**TrainingJob**
A user-visible logical Model Lab experiment referencing one immutable TrainingPlan. One TrainingJob may have multiple TrainingAttempts; its displayed status is a projection over attempts, not a second execution state machine.

**DatasetRevision**
Immutable normalized dataset snapshot with content identity, stable record IDs, provenance, validation state, split lineage and explicit transformations.

**TrainingPlan**
Immutable resolved post-training plan binding base-model revision, dataset/preparation identity, backend/environment revision, training semantics, resource selection and privacy/checkpoint policy.

**TrainingAttempt**
One concrete Model Lab worker execution of a TrainingPlan. Retry/resume creates a new attempt rather than rewriting prior execution evidence.

**Training resource lease**
Scheduling ownership of an exact accelerator/device set by one app-managed TrainingAttempt. It prevents app-managed resource races but is not a security/permission grant.

**TrainingCheckpoint**
Finalized resumable trainer state tied to one TrainingAttempt and an explicit compatibility manifest. It is distinct from coding-workspace Checkpoints and from inference-ready adapter/model artifacts.

**ModelArtifactRevision**
Immutable adapter, merged model or other inference artifact produced/imported with integrity and lineage metadata. Training completion creates a candidate artifact; registration/promotion is separate.

**EvaluationSuiteRevision**
Immutable evaluation inputs, evaluator/metric revisions, generation/template parameters and determinism metadata.

**EvaluationRun**
One execution of an EvaluationSuiteRevision against concrete base/candidate model or artifact revisions, preserving bounded per-case evidence plus aggregate results.

**Model Promotion Record**
Immutable audit record that registers one ModelArtifactRevision into Local Models (and optionally updates a user-visible alias) with the evaluation/lineage evidence, actor and timestamp used for that decision. Promotion history is append-only; it is not a mutable flag on the artifact.

## Trust vocabulary

**Trusted instruction**
Instruction admitted into a trusted authority layer by the source-trust rules in `PROMPT_RUNTIME.md`. User/application policy and explicitly trusted project/local Product Skill sources may qualify; **MCP-served Product Skill content does not become trusted instruction merely because it was activated or content-verified**.

**Untrusted content**
Retrieved files, web pages, MCP resources, tool output, extension-provided data, or model-generated text that may contain instructions but cannot elevate itself into trusted policy/instruction layers.

**Permission**
A runtime authorization decision for a concrete operation/scope. Installing or activating an extension is not permission.

**Degraded security state**
A detectable condition where the platform cannot provide the intended security property (for example a weak secret-storage backend). It must be surfaced rather than silently treated as healthy.
