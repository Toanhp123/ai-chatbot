# Test Strategy

## 1. Goal

The application crosses unreliable and trust-sensitive boundaries: providers, streaming, tools, filesystem/processes, MCP, extensions, SQLite/migrations, local runtimes, and training workers. Tests must make core behavior deterministic enough for CI to run without paid APIs or personal credentials.

Testing also enforces architecture. A documented boundary without a fitness check is weaker than intended for this agent-built project.

## 2. Test layers

### Unit tests

Focus on deterministic logic:

- capability resolution and route eligibility;
- normalized errors/usage/cost;
- Policy Core evaluation;
- path canonicalization;
- manifest/schema parsing;
- context ranking/token allocation;
- prompt instruction precedence/provenance;
- tool-catalog relevance selection;
- migration helper logic;
- dataset validation.

### Contract/integration tests

Test subsystem boundaries:

- Prompt Runtime → normalized request contract;
- Provider Core adapter ↔ fake server;
- streaming/event/error normalization;
- Tool Runtime ↔ Policy Core ↔ execution adapter;
- SQLite migrations/repositories;
- application/IPC serialization + validation;
- Context Engine inventory/parsing/search;
- MCP Host ↔ fixture server;
- extension install/activation/permission separation;
- checkpoint/restore;
- Model Lab controller ↔ fake worker.

### E2E tests

Critical desktop workflows use an isolated profile and deterministic fake provider through the real application/agent/prompt/provider/persistence path. Core E2E never requires a paid API or secret.

Initial deterministic gate:

1. launch desktop app in isolated profile;
2. select deterministic fake provider/model through normal seams;
3. create chat and submit message;
4. stream normalized events and render final output;
5. persist conversation/messages/usage;
6. close and relaunch same profile;
7. verify persisted state;
8. cover cancellation and representative provider failure.

Later E2E layers add project/code-edit/approval/checkpoint, MCP/product Skills, local AI, and Model Lab flows as their phases arrive.

## 3. Architecture fitness tests

Phase 0 must create a dedicated automated architecture gate, exposed as `test:architecture` or a clearly equivalent root command.

It must fail on at least:

- React/Electron imports in core packages;
- renderer imports of provider/storage/tool/MCP/application internals outside allowed contracts/client adapters;
- package edges/cycles forbidden by `ARCHITECTURE.md`;
- provider vendor SDK/HTTP transport use outside Provider Core;
- SQLite driver/raw SQL use outside Storage;
- raw filesystem/shell/Git mutation paths bypassing Tool Runtime/Policy Core;
- preload exposing raw Node/Electron primitives;
- fake-provider production import/registration leakage.

The checker implementation is flexible. Prefer deterministic source/dependency analysis over LLM judgment for CI.

When a new FROZEN architecture rule is added, add a corresponding fitness test where mechanically possible.

## 4. Fake provider server

Simulate deterministically:

- successful stream and non-stream response;
- one and parallel tool calls;
- structured output;
- usage only at end / usage increments;
- malformed frame;
- disconnect;
- timeout;
- rate limit;
- auth failure;
- context overflow;
- unsupported capability;
- cancellation;
- deterministic fallback-chain cases.

Golden fixtures belong at the normalized internal boundary, not as vendor payload snapshots embedded in UI tests.

## 5. MCP fixture server

Provide controlled profiles for:

- stdio basic tools/resources/prompts;
- current Streamable HTTP profile;
- selected legacy profile only if intentionally supported;
- authorization required/insufficient scope;
- tool list changes;
- malformed schema;
- tool error vs protocol error;
- cancellation/timeout;
- name collision across servers.

## 6. Security tests

Automate where feasible:

- renderer cannot access Node primitives/raw runtime modules;
- unauthorized/invalid IPC rejected;
- secrets absent from logs/snapshots/DB fields;
- workspace path traversal/symlink escape denied;
- permission grant scoping;
- destructive operation requires approval under policy;
- extension install has no executable side effect;
- malicious MCP/tool/web/file text cannot mutate trusted policy/instruction layers;
- auth token is not sent to the wrong resource;
- degraded SecretStore state is surfaced.

## 7. Migration/recovery tests

For supported migration paths:

- create DB at previous schema;
- seed representative data;
- migrate;
- verify constraints/indexes/data;
- reopen storage/application;
- test failure rollback/backup policy.

As recovery features arrive, test interrupted-task reconciliation, export-without-secrets, import validation, redacted diagnostics, and download/model cleanup.

## 8. Context/prompt tests

Fixture repositories verify:

- ignore/secret exclusions;
- incremental changed-file indexing;
- exact-symbol and related-test retrieval;
- token-budget truncation;
- provenance preservation;
- untrusted prompt injection cannot override trusted instructions/policy;
- compaction preserves active objective/constraints/next step;
- relevant tool schema selection is bounded.

## 9. Deterministic agent/runtime evals

Use provider-independent scenario fixtures where exact unit assertions are insufficient:

- correct relevant file/tool selection;
- deterministic route fallback;
- coding task stops for required approval;
- bounded loop/cancellation terminates cleanly;
- subagent context is scoped;
- compacted state preserves active constraints.

Do not make core CI depend on stochastic remote-model quality scores. Optional live-model evals run separately.

## 10. UI tests and design verification

Use component/integration tests for deterministic interaction state and targeted Electron E2E for critical workflows.

For substantial UI changes, validation evidence includes:

- `ui-ux-pro-max` was invoked;
- keyboard/focus path works;
- applicable empty/loading/streaming/error/approval/degraded states are covered;
- at least two realistic desktop viewport sizes were inspected;
- screenshots/rendered surfaces were self-critiqued when tooling supports it;
- no forbidden renderer imports were introduced;
- screenshot regression is added only for stable/high-value screens.

Visual attractiveness does not compensate for broken accessibility or runtime architecture.

## 11. Model Lab tests

Core CI uses fake/small jobs, not expensive GPU training.

Test dataset validation/conversion, config resolution, worker protocol, progress events, cancellation/kill, checkpoint metadata, failed environment setup, and output registration. Hardware-specific tiny training smokes are supplemental.

## 12. Phase gate

Every phase exit requires the applicable subset of:

- format/check;
- lint;
- typecheck;
- unit tests;
- integration/contract tests;
- architecture fitness;
- production build;
- deterministic E2E acceptance flow;
- UI/accessibility/rendered review when UI changed substantially.

Never report a gate passed unless the commands/evidence actually ran successfully.
