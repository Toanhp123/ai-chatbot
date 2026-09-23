# UX Specification

## 1. Experience goal

The desktop app should feel calm, fast, technical, premium, and information-dense without becoming a dashboard of permanent chrome.

The user should always understand four things during agent work:

- what task is active;
- what the agent/model is doing at a useful level;
- what needs approval;
- what changed.

Avoid exposing private reasoning traces or raw protocol noise.

## 2. Primary information architecture

### Left navigation

Candidate destinations:

- New chat
- Search
- Projects
- Agents
- Artifacts
- Local Models
- Model Lab
- Marketplace
- recent/pinned chats

Early phases should show only implemented destinations. Do not ship dead navigation for future features.

### Main conversation/task surface

Support progressively:

- streaming assistant content;
- Markdown and syntax-highlighted code;
- tables/math where renderer support is robust;
- attachments;
- citations/source chips;
- tool activity cards;
- approval prompts;
- errors with actionable recovery;
- stop/cancel;
- retry/regenerate;
- conversation branch/edit only after semantics are defined and tested.

### Composer

The composer should expose only decisions relevant before send:

- model or route;
- project/workspace;
- attachments;
- current operation mode when the product uses read/plan/act modes;
- active tools/Skills/MCP summary;
- context-budget indicator;
- optional reasoning/effort control only when supported by selected model;
- send/stop.

Provider selection should not become a second model selector when a route/model already determines it. Prefer progressive details.

### Contextual side panel

Open only when useful for:

- file/artifact preview;
- diff/change set;
- plan;
- terminal/process output;
- citations/evidence;
- running task timeline.

Do not permanently reserve space for empty panels.

## 3. Agent task UX

Represent an agent task with a compact state header:

- task title;
- status;
- selected model/route;
- elapsed time;
- cancellation control;
- approval state;
- changed-file count;
- cost/usage when known.

Detailed event timeline may show tool name, high-level purpose, result/error, and files changed. It should not dump raw internal prompts by default.

## 4. Permission UX

Approval dialogs must answer:

- **what** operation is requested;
- **why** it is needed;
- **where** it applies (workspace/path/host/service);
- **risk class**;
- **scope of approval** (once/session/project policy);
- material arguments such as command/path/domain while redacting secrets.

Dangerous operations require stronger friction than ordinary workspace writes.

Never use a generic “Allow everything” control that silently expands to filesystem + shell + network + credentials.

## 5. Diff/checkpoint UX

For agent-driven edits:

- group changes by task/checkpoint;
- show added/modified/deleted files;
- show unified diff with syntax-aware presentation where feasible;
- let user restore the whole checkpoint;
- hunk-level accept/reject can be later if it does not compromise checkpoint correctness.

## 6. Provider/model UX

Model picker should communicate capability and source, not only model name:

- provider/runtime;
- context limit if known;
- vision/tools/structured-output badges;
- local/cloud indicator;
- pricing if known;
- compatibility warning when capabilities are overridden or inferred.

Custom endpoints need a “test connection” path that reports authentication, model-list, streaming, and capability-probe outcomes separately.

## 7. MCP / Skills / plugins UX

Installation and activation are distinct.

MCP connection detail should show:

- source/URL/command;
- transport/protocol profile;
- auth state;
- tools/resources/prompts discovered;
- permission policy;
- last error/health;
- provenance.

Plugin install review should show declared executable hooks/commands/MCP definitions and requested permissions before activation.

## 8. Local AI UX

Local model/runtime screens should emphasize practical fit:

- runtime;
- model ID/family;
- quantization;
- size;
- context;
- loaded state;
- estimated RAM/VRAM/unified-memory fit;
- supported capabilities;
- warnings where capability is model/template dependent.

Avoid presenting estimated “quality scores” as universal truth.

## 9. Accessibility and productivity

- full keyboard navigation for core chat/project/model flows;
- command palette for discoverability and power use;
- visible focus states;
- screen-reader labels for controls/status;
- reduced-motion support;
- virtualize long chat/log/model lists;
- preserve readable density at common laptop widths.

## 10. Visual principles

Use design tokens from Phase 0. Provide high-quality light/dark themes. Favor typography, spacing, hierarchy, and state clarity over gradients or decorative cards.

Do not copy another AI product's proprietary visual identity or wording.
