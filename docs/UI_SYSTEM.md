# UI System and Frontend Implementation Contract

> **Authority:** normative UI implementation contract
> **Required development Skill:** external **`ui-ux-pro-max`** for substantial UI work
> **Architecture owner:** `ARCHITECTURE.md` remains authoritative for renderer/application/runtime boundaries.

## 1. Purpose

This document turns `UX_SPEC.md` into repeatable frontend implementation rules. `ui-ux-pro-max` supplies UI/UX design intelligence and stack-specific guidance; this document supplies product-specific constraints, states, architecture, accessibility, and validation gates. Optional `frontend-design` may add a visual/taste refinement pass, but it never replaces the required UI/UX workflow.

Substantial UI work is blocked if the required `ui-ux-pro-max` Skill is unavailable. Tiny local fixes such as copy correction or an obvious one-line style defect do not need a full design pass.

## 2. Design intent

The app should feel like a serious desktop AI workspace: dense enough for developers, calm enough for long chat/research sessions, and explicit about agent/tool state.

Do not clone another product's brand, shell, typography, palette, or component styling. Build an intentional visual identity grounded in this product's job: reasoning, building, inspecting, and controlling AI work over long sessions.

Avoid generic generated-UI tells: decorative gradient/glow by default, identical rounded cards for every hierarchy, excessive pill controls, meaningless eyebrow labels, animation on every surface, and placeholder copy that does not match real workflows.

## 3. Required design workflow

For a new shell, screen, major flow, redesign, or design-system change:

1. use `ui-ux-pro-max` and follow its current design-system/UX workflow;
2. read the relevant UX/product/runtime states before drawing the screen;
3. define a short design direction for this product surface: audience/job, hierarchy, layout idea, typography, semantic color intent, density, and the one distinctive visual idea worth spending emphasis on;
4. use realistic product content/states, not lorem ipsum or generic SaaS metrics;
5. implement within the frozen renderer/application/runtime boundaries;
6. if the surface benefits from an additional visual/taste pass, optionally use `frontend-design` to refine the chosen direction without replacing product/UX constraints;
7. render and inspect at multiple realistic desktop sizes;
8. use screenshot/visual critique when the environment supports it, then simplify/refine visible problems;
9. validate keyboard/focus, reduced motion, contrast, error/empty/loading/approval states;
10. run applicable behavioral tests and fix findings before completion.

The Skill may propose design choices but cannot rewrite `UX_SPEC.md`, application information architecture, security requirements, or runtime ownership without the normal decision process. Generated design-system reports are working inputs, not a parallel source of truth: durable decisions belong in this document/`UX_SPEC.md` and implemented semantic tokens.

## 4. Design system foundation

Use reusable semantic tokens for:

- typography roles/scale/line-height;
- spacing/density;
- radius only where it communicates component/surface character;
- surface/background/border hierarchy;
- text emphasis and muted content;
- semantic intent/status;
- focus/selection;
- elevation where needed;
- motion duration/easing;
- icon sizing;
- code/editor typography.

Prefer semantic tokens over page-specific hard-coded values. Do not build a general theming/plugin framework in Phase 0; establish light/dark support only to the level required by product scope and chosen shell direction.

## 5. Application shell

As features arrive, the shell should support:

- primary navigation/project/workspace switching;
- conversation/project list with search/filter;
- central working surface for chat/editor/artifact/research/model-lab modes;
- contextual inspector/details surface when useful;
- task/activity surface for agent/tool/run state without dominating the workspace;
- command palette/keyboard entry points;
- settings for providers/models, MCP/extensions, permissions, local AI, data/privacy.

Navigation must not reconstruct runtime state inside each page. The UI consumes application state through typed boundaries.

## 6. Frontend architecture

React components consume presentation-safe application contracts through the typed preload/IPC path. They must not:

- construct provider vendor payloads;
- import provider/storage/tool/MCP runtime packages;
- read secret values directly;
- access SQLite or raw filesystem/shell/process APIs;
- speak MCP transports;
- encode runtime permission policy inside component state;
- duplicate canonical runtime state machines with divergent UI-only semantics.

Renderer state distinguishes durable domain data from ephemeral view state. Prefer feature-oriented modules; extract shared primitives after real reuse rather than building a speculative component framework.

## 7. Required interaction states

Design the states that actually exist, not only the happy screenshot:

- initial/empty;
- loading/indexing/connecting;
- streaming/in-progress;
- queued/waiting approval;
- success/completed;
- cancelled;
- retryable failure;
- non-retryable failure;
- offline/provider unavailable;
- degraded security/missing capability;
- permission denied;
- stale/conflicted workspace state.

State transitions come from typed domain/runtime events, not arbitrary component timers.

## 8. Agent/tool UX

Users must be able to answer: **what is happening, why, what will happen if I approve, what changed, and how do I stop it?**

Represent agent work with typed status, current action, meaningful elapsed/progress information, cancellation, relevant tool calls, approval requests, concise outcomes, and an inspectable event/audit view.

Approval UI names the concrete operation, target, scope/risk, and whether the decision can be remembered. Avoid vague text such as “allow action” when the runtime knows the command/path/network target.

Diff/edit UX makes files/hunks/conflicts reviewable before destructive consequences where policy requires review.

## 9. Chat/content UX

Streaming updates incrementally without destabilizing scroll/focus. Long histories/logs/lists use windowing/pagination or another bounded strategy.

Messages may render text, code, tool state, attachments, citations/source references, artifacts, and errors through typed safe renderers. Sanitize Markdown/HTML and treat model content as untrusted.

Model/route controls communicate capability, locality/privacy, and cost implications without turning the main chat surface into a provider configuration dashboard.

## 10. Accessibility and keyboard behavior

Target practical WCAG 2.2 AA behavior for core workflows:

- semantic controls and accessible names;
- visible focus and logical focus restoration;
- keyboard operation for navigation, dialogs, command palette, tool approvals, and critical actions;
- no color-only state communication;
- appropriate contrast;
- reduced-motion support;
- screen-reader announcements for important task/stream state without excessive noise.

Intentional temporary exceptions belong in `TECH_DEBT.md` with correction triggers.

## 11. Performance

Do not render unbounded logs, conversations, file trees, model lists, or tool events. Use stable keys and bounded rendering.

Keep expensive Markdown/code highlighting, diff work, parsing, embeddings, Git, model inference, and process work off the renderer critical path. Avoid global subscriptions that rerender the whole shell on every streaming token/event.

## 12. Error presentation

Project domain errors into actionable user language while retaining a safe developer-details affordance/correlation ID.

Differentiate when known: configuration/authentication, rate limit, capability mismatch, network/offline, permission denial, tool failure, storage failure, degraded security, and internal fault. Never display raw secrets, authorization headers, or unsafe process output by default.

## 13. UI validation gate

For every meaningful UI change validate:

- at least two realistic desktop viewport sizes;
- changed workflow via keyboard/focus;
- applicable empty/loading/streaming/error/approval/degraded states;
- no uncaught renderer errors;
- no forbidden renderer imports/runtime shortcuts;
- behavioral component/integration coverage where deterministic;
- rendered screenshot/visual critique for high-value screens when tooling supports it;
- screenshot regression only after a screen/system is stable enough for it to add signal.

A visually polished screen that violates accessibility, runtime boundaries, or required states does not pass.

## 14. Phase 0/1 UI minimum

Phase 0/1 must establish:

- intentional app-shell direction created with `ui-ux-pro-max`;
- semantic tokens/primitives;
- secure typed preload/application access pattern;
- keyboard/focus foundation;
- real empty/loading/streaming/error/degraded states needed by the deterministic chat slice;
- bounded conversation rendering strategy;
- validation at multiple desktop sizes.

It does not need the final marketplace, Model Lab, advanced editor, or every later product surface.
