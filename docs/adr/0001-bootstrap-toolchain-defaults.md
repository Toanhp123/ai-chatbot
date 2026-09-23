# ADR-0001 — Fresh-repository bootstrap defaults

- Status: accepted
- Date: 2026-09-23

## Context

A single-command bootstrap should not stall on routine foundational choices when the repository is fresh. At the same time, an existing repository may already contain valid tooling that should not be replaced unnecessarily.

Current primary-source checks show Node 24 is an LTS line and current stable Electron releases use Node 24. Electron continues to recommend secure main/preload/renderer boundaries. Vitest aligns with Vite-based TypeScript projects. Playwright exposes Electron automation suitable for a narrow deterministic desktop E2E, while its Electron API remains explicitly experimental and must therefore stay behind a test adapter rather than becoming a product dependency.

## Decision

For a **fresh/effectively empty repository**, use these defaults unless current research reveals an incompatibility:

- Node.js 24 LTS as the development baseline;
- `pnpm` workspaces as package manager/workspace mechanism;
- no Nx/Turborepo initially;
- TypeScript in strict mode for application/core packages;
- Electron + React for desktop;
- Vite-based renderer/build tooling, with the exact Electron/Vite integration selected during Phase 0 based on current maintenance/security/packaging constraints;
- Vitest for unit/integration tests where appropriate;
- a thin Electron E2E adapter around Playwright for the bootstrap acceptance flow;
- SQLite behind a repository/storage abstraction with reproducible migrations;
- choose the exact SQLite driver/migration integration during Phase 0 after verifying compatibility with the selected Electron runtime; prefer avoiding unnecessary native-addon packaging complexity;
- structured schema validation at external/IPC/config boundaries using a maintained library chosen during scaffold.

Expose stable root scripts: `format`, `format:check`, `lint`, `typecheck`, `test`, `test:integration`, `test:e2e`, and `build`.

For an **existing repository**, preserve established compatible choices and record an ADR only if a foundational replacement is required.

## Consequences

- The agent can scaffold without asking routine tooling questions.
- The architecture avoids an unnecessary monorepo task orchestrator at the beginning.
- Electron/Vite and SQLite driver details remain evidence-based Phase 0 decisions because their compatibility/maintenance status can change.
- Playwright Electron automation is isolated behind test helpers so its experimental status does not leak into product architecture.

## Alternatives considered

- npm workspaces: viable, but pnpm is the fresh-repo default for workspace ergonomics and deterministic package layout.
- Nx/Turborepo: unnecessary for the first few packages and can be added later if build graph complexity justifies it.
- hard-pinning one SQLite native addon before scaffold: rejected because Electron/native-module packaging constraints should be validated against the actual runtime first.
- paid-provider E2E: rejected as a core gate because CI and bootstrap must be credential independent.

## Verification / revisit trigger

Revisit when:

- the existing repository already uses a different coherent stack;
- an Electron/Vite integration becomes unsuitable or unmaintained;
- Node/Electron runtime compatibility changes;
- the chosen SQLite integration causes packaging, migration, or performance problems;
- Playwright Electron automation is insufficient for a required release-critical E2E.
