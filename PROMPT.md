# Antigravity Project Bootstrap Prompt

## Mission

Build a production-oriented, desktop-first, local-first AI workspace that combines high-quality multi-model chat, coding-agent workflows, secure tools and MCP, installable product extensions/Skills, project-aware context, local model inference, and a later practical personal Model Lab for fine-tuning compatible open-weight models.

The product may borrow interaction principles from leading AI workspaces and coding agents, but must have its **own information architecture and visual identity**. Do not clone Claude, Cursor, Antigravity, ChatGPT, or another product pixel-for-pixel.

The repository already contains the product and architecture contract. Implement it; do not replace it with a new design exercise.

## Operating contract

1. Read and obey `AGENTS.md` first.
2. Classify the task with the **minimum sufficient capability route** in `docs/DEVELOPMENT_TOOLING.md`; do not invoke every Skill/tool by default.
3. For non-trivial coding work, **use the relevant Superpowers Skill(s)**. This is required, not optional process advice.
4. For substantial frontend/UI work, **use `ui-ux-pro-max`** in addition to Superpowers. `frontend-design` may be used as an optional visual-refinement pass; Ponytail is not a UI-design substitute.
5. Once substantive code exists, use **Graphify** for broad repository dependency/path/impact analysis according to `docs/DEVELOPMENT_TOOLING.md`; prefer local code-structure analysis and verify consequential graph conclusions in source/tests.
6. Do not create/vendor repository-local development Skills, Graphify rules/workflows, or copied Skill bodies to satisfy these requirements.
7. Read `docs/ARCHITECTURE.md` before structural changes. Its V1 baseline and dependency direction are **FROZEN** unless superseded by an approved ADR under the change protocol.
8. Read `docs/EXECUTION_PROTOCOL.md`, `docs/IMPLEMENTATION_STATUS.md`, the active roadmap phase, and only the subsystem docs needed for the next executable step.
9. Inspect actual code/Git/build/test state and resume existing work rather than restarting.
10. Research volatile external contracts only when they affect the active task; prefer primary sources and record material implications in `docs/research.md`.
11. Implement, validate, self-review, fix findings, update the status ledger, and continue until the active bootstrap gate passes or a protocol-defined hard blocker is reached.

Do not stop at a plan, scaffold, UI mock, or partial backend while the deterministic bootstrap acceptance path can still be completed locally.

## Product principles

- **Local-first:** conversations, projects, indexes, configuration, artifacts, and experiment metadata live locally by default.
- **Provider-independent:** cloud gateways, compatible APIs, routers, and local endpoints integrate behind normalized capability-driven adapters.
- **Agent core independent of UI:** orchestration runs without React/Electron dependencies.
- **Security by construction:** secrets, IPC, tools, MCP, extensions, web content, filesystem/shell access, downloads, and training cross explicit trust/permission boundaries.
- **Progressive context:** never dump the whole repository/tool catalog into a model; select relevant instructions, files, symbols, tools, memories, and history under budgets.
- **Observable and cancellable:** model requests, tools, indexing, downloads, inference, and training expose state, diagnostics, cancellation, and bounded retries.
- **Portable configuration:** safe configuration is exportable; secrets are excluded or securely referenced.
- **Deterministic core validation:** required CI/bootstrap gates do not depend on paid APIs or personal credentials.
- **Architecture by contract:** frozen ownership/dependency rules are tested, not merely documented.

## Product surface

The product direction includes:

- streaming conversations with edit/regenerate/branch, attachments, artifacts, search, model/route selection, usage/cost metadata, and explicit memory controls;
- Projects/workspaces with project instructions, repository context, code Q&A, editing, diffs, checkpoints, commands, and validation;
- provider/model registry with cloud, compatible, routed, and local endpoints;
- Agent Core with bounded tasks, planning, tools, permissions, cancellation, subagents, recovery, and observability;
- Context Engine with ignore-aware inventory, structural parsing, lexical search, optional semantic retrieval, repository maps, and token-budgeted packing;
- Prompt Runtime with trusted instruction layering, provenance-aware context/tool assembly, compaction, and provider-neutral normalized requests;
- Tool Runtime + Policy Core for filesystem, shell/process, Git, MCP, research/browser, and future tools;
- MCP client/host integration plus product Skills/extensions/plugins with validation, trust review, scoped permissions, lifecycle/versioning, and future marketplace support;
- local inference integrations through maintained runtimes rather than a custom inference engine;
- Model Lab as an isolated worker/control plane for dataset validation, SFT/LoRA/QLoRA, evaluation, checkpointing, and export;
- backup/export, crash recovery, updates, privacy controls, and redacted diagnostics.

Detailed behavior is owned by `docs/`; do not duplicate or reinterpret it here.

## Architecture baseline

Use `docs/ARCHITECTURE.md` as the normative system shape and `docs/CONTRACT_INVENTORY.md` as the stable boundary map.

Frozen V1 direction includes:

- Electron desktop shell with secure main/preload/renderer separation;
- React renderer as presentation only;
- typed application/use-case boundary between UI and runtime services;
- React/Electron-independent core packages;
- explicit `contracts`, `application`, `agent-core`, `prompt-runtime`, `context-engine`, `provider-core`, `policy-core`, `tool-runtime`, `storage`, `mcp-host`, and `extension-core` ownership;
- SQLite local persistence behind Storage;
- `SecretStore` outside ordinary DB fields;
- isolated external processes for training and sandboxed execution where introduced;
- deterministic fake-provider E2E through the same normalized runtime path as production providers;
- automated architecture fitness checks for forbidden imports/dependency edges.

Implementation choices explicitly left open may be selected autonomously when current evidence supports them.

## Bootstrap target

The initial autonomous run must complete:

### Phase 0 — Foundation

Establish the frozen architecture in executable form: workspace/package boundaries, secure Electron shell/preload, typed IPC/application seams, core packages without UI dependencies, SQLite migrations, `SecretStore`, structured redacted logging, design-system foundation, fake-provider harness, architecture fitness tests, and stable root validation commands.

### Phase 1 deterministic vertical slice

Prove: isolated test profile → fake provider selected through normal runtime seams → create conversation → submit message → normalized streaming response → render final result → persist conversation/messages/usage → close → relaunch same profile → persisted state remains. Also cover cancellation, at least one normalized provider failure, and isolation of fake-provider configuration from production.

A live/local provider smoke is supplemental only when already authorized/configured.

## Completion

Before declaring success, prove the active gates with actual commands/tests, self-review the diff, repair material findings, update `docs/IMPLEMENTATION_STATUS.md`, and report only verified outcomes plus the exact next roadmap milestone.
