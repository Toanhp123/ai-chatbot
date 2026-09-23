# Roadmap

The roadmap is vertical: every phase ends in a real usable workflow and executable evidence. FROZEN architecture comes from `ARCHITECTURE.md`; roadmap phases do not authorize bypassing it.

## Phase 0 — Foundation

Deliver:

- workspace/package structure reflecting the frozen ownership model as responsibilities become real;
- Electron shell with secure main/preload/renderer separation;
- typed versioned IPC/application seam;
- `contracts`, `application`, `provider-core`, `prompt-runtime`, `storage`, and other Phase-0-required boundaries without forbidden reverse dependencies;
- SQLite storage + reproducible migrations;
- `SecretStore` abstraction with security-health/degraded state;
- structured logging/redaction foundation;
- semantic design tokens/basic shell UI designed with the required external `ui-ux-pro-max` Skill;
- normalized provider request/event types and Prompt Runtime boundary;
- explicit profile/data-root abstraction for production vs tests;
- deterministic fake-provider skeleton behind Provider Core;
- architecture fitness tests for frozen dependency/trust rules;
- developer-tooling setup consistent with `DEVELOPMENT_TOOLING.md`, including task routing and a local Graphify code-only repository graph for the final structural review once substantive source exists;
- stable root validation commands;
- canonical docs/ADRs/contract inventory aligned with scaffold.

Acceptance criteria:

- production build launches on the primary development OS;
- renderer has no direct Node/filesystem/provider/storage/tool/MCP/secret access;
- core packages do not import React/Electron;
- typed IPC/application seam is validated at runtime boundaries;
- DB migrates from empty schema and reopens cleanly;
- secret round-trip works on supported secure backend, with degraded state detectable;
- architecture-fitness command catches representative forbidden imports/edges;
- Graphify can provide local source-graph evidence for Phase 0 structural review without committed project-local skill/rule/workflow artifacts; if the capability is unavailable, the gate remains explicitly blocked rather than silently substituted;
- fake provider is reachable only through Provider Core and excluded from production registration;
- shell UI has real empty/loading/error/degraded states required by Phase 1, keyboard/focus basics, and validation at multiple desktop sizes;
- `format:check`, `lint`, `typecheck`, `test`, `test:integration`, `test:architecture`, `test:e2e`, and `build` (or documented equivalents) are available;
- foundational architecture/security/data/provider/UI docs match actual code.

## Phase 1 — Real chat core

Deliver:

- provider/model registry and capability model;
- OpenAI-family adapter;
- Anthropic adapter;
- Gemini adapter or explicit documented deferral after the first two if active scope requires;
- custom compatible endpoints;
- normalized prompt assembly + streaming/errors/usage;
- persisted conversations/messages;
- attachment metadata foundation;
- provider test harness;
- deterministic chat UI slice using real runtime/application contracts.

Acceptance criteria:

App launches in an isolated test profile → fake provider selected through normal application/provider seams → deterministic model streams through normalized runtime/events → UI renders final result → conversation/messages/usage persist → app restarts with same profile → persisted state remains.

Also:

- cancellation stops a stream;
- at least one provider failure is normalized and rendered safely;
- UI contains no vendor stream parsing/payload construction;
- fake-provider malformed/disconnect cases have integration coverage;
- fake provider cannot enter production configuration/runtime;
- architecture fitness remains green.

A live/local provider smoke is supplemental when already authorized/configured.

## Phase 2 — Projects and code intelligence

Deliver:

- Projects with one-or-more workspace roots;
- project instructions;
- ignore-aware repository inventory;
- Tree-sitter structural parsing for initial languages;
- repository/symbol map;
- lexical search;
- context planner + token budgeting;
- read-only code Q&A;
- incremental indexing.

Acceptance criteria:

Open a real repository → ask about a symbol/feature → diagnostics show a bounded provenance-aware context set → answer references correct files → ignored/secret paths are excluded by default → editing a file causes incremental refresh rather than full rebuild.

## Phase 3 — Coding agent

Deliver:

- `AgentTask` state/events;
- planning workflow;
- filesystem patch tools;
- command/process tools;
- read Git tools then scoped mutation tools;
- Policy Core + Tool Runtime approval path;
- diff/checkpoint UI;
- optional isolated worktree/workspace execution for suitable tasks;
- test/lint/fix loop;
- cancellation propagation.

Acceptance criteria:

Request a small code change → agent inspects first → plans where appropriate → requests only necessary approval → patches files through Tool Runtime → runs validation → displays diff → user can restore checkpoint without losing unrelated pre-existing work.

## Phase 4 — MCP + Product Skills

Deliver:

- MCP server registry;
- stdio + current Streamable HTTP implementation;
- version/profile compatibility layer;
- HTTP auth foundation;
- tool/resource/prompt discovery;
- relevance-based tool catalog exposure;
- global/project product Skills;
- progressive Skill loading.

Acceptance criteria:

Connect a fixture/real MCP server → inspect provenance/capabilities → expose only selected relevant tool schemas → invoke through Tool Runtime/Policy Core → disconnect/reconnect cleanly. A product Skill is discovered without loading all Skill bodies into every request.

## V1 release gate

V1 is the stable combination of Phases 0–4 plus basic configurable custom agents.

Release only when:

- architecture fitness is enforced in CI and green;
- data migrations have upgrade tests;
- secrets/permission boundaries have focused security review;
- core E2E runs without paid APIs;
- crash/restart preserves conversations/projects/settings and safely reconciles interrupted tasks;
- test/production profiles cannot accidentally share secrets/state;
- backup/export/diagnostic boundaries are secret-safe;
- contract inventory matches real cross-boundary APIs;
- no production path relies on mock data;
- known limitations are documented.

## Phase 5 — Plugins + marketplace

Deliver only after the product Skill/MCP trust model is proven:

- versioned plugin manifest;
- install/update/disable/enable/uninstall;
- install vs activation separation;
- trust/permission review;
- registry abstraction/UI;
- bundled product Skills/agents/MCP definitions;
- executable hooks only after sandbox/permission design is proven;
- public plugin SDK only when third-party compatibility requires it.

## Phase 6 — Advanced agent platform

Deliver selectively:

- richer custom agents;
- synchronous then parallel subagents;
- conflict-aware parallel tasks;
- lifecycle hooks;
- web research mode;
- isolated browser automation;
- richer artifacts/trace.

## Phase 7 — Local AI

Deliver:

- local runtime detection/configuration;
- Ollama;
- llama.cpp-compatible;
- LM Studio compatible;
- optional vLLM/custom runtime;
- hardware inventory/fit estimates;
- local model metadata/management hooks.

## Phase 8 — Model Lab

Deliver:

- dataset manager/validation;
- isolated worker environment;
- SFT/LoRA/QLoRA;
- NVIDIA backend path;
- Apple Silicon MLX-LM path;
- metrics/checkpoints;
- evaluations/base-vs-adapted comparison;
- export/register result.

## Phase discipline

Do not implement a later phase because its name/type appears in architecture. Reserve only the stable boundary required by known future integration; instantiate packages/services when their first real responsibility is implemented.
