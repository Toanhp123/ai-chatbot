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
The product's own bounded unit of agent orchestration with state, events, cancellation, budgets, tool calls, and result. Do not conflate with MCP Tasks.

**MCP Task**
A task primitive defined by an MCP extension/profile when supported. It is external-protocol semantics, not the internal `AgentTask` model.

**Provider**
A configured inference transport/service integration such as a vendor API, compatible gateway, router, or local runtime endpoint.

**Model**
A selectable model/capability record exposed by a Provider.

**Route**
An ordered/policy-constrained set of eligible provider/model candidates used by the runtime.

**Provider Core**
The sole boundary for provider-specific transport, payload translation, stream/error/usage normalization, model metadata, and routing behavior.

**Prompt Runtime**
Trusted instruction precedence, provenance framing, context/tool packing, compaction representation, and provider-neutral model-request assembly.

**Context Engine**
Repository/workspace evidence discovery, parsing, indexing, retrieval, ranking, token budgeting, and context-plan generation.

**Tool**
A callable capability with a typed schema and normalized invocation/result lifecycle. Effectful tools execute through Tool Runtime + Policy Core.

**Tool Runtime**
Central registry/execution lifecycle for tools, including validation, permission mediation, timeout/cancel, output normalization, and audit.

**Policy Core**
Pure authorization/policy decision boundary for effectful operations. Policy decides; Tool Runtime executes.

**Product Skill**
An application extension that contributes focused instructions/resources through progressive disclosure. Product Skills never grant runtime permission.

**Extension**
Installable/configurable product contribution such as Skills, agent configs, MCP definitions, hooks, or future plugin bundles, governed by Extension Core.

**MCP Host**
Boundary that speaks supported MCP protocol profiles/transports and converts remote primitives into internal descriptors/adapters.

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

**Model Lab Job**
A durable training/evaluation job controlled by the desktop app and executed by the isolated Model Lab worker.

## Trust vocabulary

**Trusted instruction**
Instruction originating from platform/user/project/product-Skill layers with explicit precedence defined by `PROMPT_RUNTIME.md`.

**Untrusted content**
Retrieved files, web pages, MCP resources, tool output, extension-provided data, or model-generated text that may contain instructions but cannot elevate itself into trusted policy/instruction layers.

**Permission**
A runtime authorization decision for a concrete operation/scope. Installing or activating an extension is not permission.

**Degraded security state**
A detectable condition where the platform cannot provide the intended security property (for example a weak secret-storage backend). It must be surfaced rather than silently treated as healthy.
