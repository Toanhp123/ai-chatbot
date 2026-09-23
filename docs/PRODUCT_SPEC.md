# Product Specification

## 1. Product definition

`[APP_NAME]` is a desktop-first, local-first AI workspace that combines general AI chat, project-aware coding assistance, safe local tooling, multi-provider model access, extensibility, local inference, and later practical personal-model post-training.

The product should feel like one coherent workspace, not separate “chat”, “IDE”, “MCP”, and “training” applications stapled together.

## 2. Primary users

### Independent developer / power user

Needs one desktop application to use multiple commercial and local models, work on repositories, run tools safely, and retain project context without locking into one provider.

### Small technical team member

Needs reproducible project instructions, model/provider configuration, auditable code changes, and portable extension definitions. Team/cloud collaboration is not an early product scope, but local projects must be structured so sharing can be designed later.

### Local-AI enthusiast

Needs straightforward connection to local runtimes and honest hardware/capability information without requiring the desktop app to own an inference engine.

### Model experimenter

Later needs a guided workflow for validating datasets, launching practical LoRA/QLoRA/SFT jobs, inspecting metrics/checkpoints, evaluating outcomes, and registering the resulting model locally.

## 3. Core jobs-to-be-done

1. **Chat with the right model** — configure providers/endpoints, discover/select models, stream responses, retain history, and understand usage/cost.
2. **Understand a project** — attach/open a repository and ask questions using targeted code context rather than whole-repo dumping.
3. **Change code safely** — inspect a plan, permit scoped operations, review patches/diffs, run validation, and restore checkpoints.
4. **Connect capabilities** — add MCP servers and Skills without permanently injecting every tool/schema into every prompt.
5. **Build reusable agents/workflows** — configure tools, model route, Skills, permission profile, and bounded budgets without hard-coded personas in core.
6. **Use local AI** — connect existing local inference servers and understand model/hardware fit.
7. **Fine-tune compatible open-weight models** — later run local post-training with explicit datasets, configuration, evaluation, and artifacts.

## 4. Product principles

- Local-first storage and privacy by default.
- Provider-independent core with explicit capabilities.
- Security before autonomy.
- Progressive disclosure of context/tools/Skills.
- Observable and cancellable agent work.
- Real vertical workflows over decorative UI shells.
- Extension points around known variability: providers, tools, MCP, storage, sandboxing, local runtimes, training backends.
- No speculative abstraction around hypothetical features with no near-term contract.

## 5. Major product areas

### Conversations

- streamed messages;
- Markdown/code/tables/math where supported by renderer;
- attachments and citations;
- tool-activity cards;
- retry/regenerate/edit/branch semantics defined by conversation model;
- stop/cancel;
- model/route and project association;
- usage visibility.

### Projects

A Project is a durable scope containing:

- title/description;
- project instructions;
- chats;
- artifacts;
- project memory;
- optional one-or-more filesystem workspace roots/repositories;
- enabled Skills/MCP servers;
- preferred model/route;
- project-scoped permissions.

### Coding workflows

Product-facing operation modes may present read-only investigation, planning, and authorized action, but the underlying runtime is one task engine with policy-constrained tools.

Read-only workflows can inspect/search/explain. Planning can produce affected areas, implementation plan, risk and verification. Authorized agent workflows can edit, execute, validate and iterate within permissions. Suitable coding tasks may run in an isolated Git worktree/workspace so parallel or risky changes do not silently contaminate the user's active tree.

### Providers and routes

Users can configure direct providers and compatible custom endpoints. A model's capabilities are explicit and may be discovered, declared by preset, or manually overridden.

A Route is an ordered policy over candidate models/providers. V1 prioritizes deterministic behavior and clear fallback reasons.

### MCP / Skills / plugins

- MCP exposes external tools/resources/prompts through a protocol adapter and permission boundary.
- Skills are focused instruction packages loaded progressively.
- Plugins bundle reusable capabilities but installation does not imply execution permission.
- Marketplace is a registry/distribution abstraction, not a trust signal.

### Artifacts

Artifacts are durable versioned outputs separate from ordinary messages. Initial useful types: Markdown/text/code/JSON and isolated previewable HTML.

### Memory

Memory is explicit durable context, not a synonym for conversation history. Users can inspect, edit, disable and delete entries. Automatic suggestions may come later, but persistence must be understandable.

### Local AI

Prefer connecting to existing runtimes/endpoints first. Product value is unified discovery/configuration, capability representation, model management hooks, and hardware-fit guidance.

### Model Lab

A later isolated subsystem for practical post-training of supported open models. It is not “train your own frontier model”.

### Operations and privacy

The product needs explicit data/profile isolation, backup/export/import boundaries, crash recovery, redacted diagnostics, update trust, storage-pressure handling, and transparent remote network behavior. Portable exports exclude secret values by default.

## 6. V1 boundary

V1 must provide a coherent path across Phases 0–4 plus basic custom-agent configuration:

- cross-platform desktop shell;
- secure local persistence/migrations;
- secure secret abstraction;
- multiple API protocols/providers and compatible endpoints;
- real streaming chat + persistence;
- model registry/capabilities;
- attachments foundation;
- Projects;
- repository inventory/search/structural context;
- read/plan/authorized edit coding workflows;
- patch-based filesystem changes;
- terminal/process execution through permissions;
- Git diff/checkpoints;
- centralized Tool Runtime + Policy Core authorization path;
- MCP core integration;
- Skills;
- basic configurable agents;
- normalized usage/cost;
- profile/data-root isolation suitable for tests and recovery;
- operational boundaries for backup/export/redacted diagnostics even if their full UI ships later.

## 7. Later scope

After a stable V1 core:

- richer plugins/marketplace;
- parallel/subagent orchestration;
- lifecycle hooks;
- web research/browser automation;
- richer artifacts;
- deeper local-runtime management;
- Model Hub;
- Model Lab;
- selected collaboration/cloud features only after an explicit architecture phase.

## 8. Non-goals for early versions

- exact clone of Claude/Cursor/etc.;
- provider credential interception, cookie theft, MITM, or subscription bypass;
- proprietary foundation model training;
- distributed agent clusters;
- custom browser engine;
- custom vector DB from scratch;
- custom inference engine from scratch;
- hundreds of hard-coded provider integrations;
- social network/team billing/mobile/cloud sync before core desktop value is proven.

## 9. Success criteria

The product is succeeding when a user can:

1. configure a provider securely;
2. have a persisted streamed chat;
3. attach/open a project and get useful code answers from bounded context;
4. request a code change, approve only the needed actions, inspect the diff, run tests, and restore if needed;
5. connect an MCP server or Skill without losing visibility over permissions/context;
6. switch to a compatible local runtime without changing the rest of their workflow.

The key quality signal is not feature count; it is whether these end-to-end workflows remain predictable, fast, inspectable, and provider-independent.
