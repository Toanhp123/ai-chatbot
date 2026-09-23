# ADR-0004 — Workspace, MCP, extension, and local-runtime trust boundaries

- Status: accepted
- Date: 2026-09-23
- Class: FROZEN cross-cutting security/trust contract
- Supersedes: none
- Superseded by: none

## Context

The frozen architecture separates MCP Host, Extension Core, Prompt Runtime, Tool Runtime/Policy Core, Provider Core, Application and Electron processes, but V1 still needs one explicit trust model for repository-controlled instructions, MCP-delivered Skills, plugin lifecycle/code execution and local inference. Without it, read access can become instruction authority, install can become execution, remote Skill bytes can gain excessive precedence, or “local” runtimes can be assumed safe without evidence.

## Decision

Freeze these V1 invariants:

1. **Workspace trust is explicit and scoped** — opening/reading/indexing a root does not trust repository-controlled behavior. Only designated sources admitted by workspace/source trust enter the trusted Project instruction layer. Trust is revocable and is never operation permission.
2. **One extension lifecycle** — discovery, installation, review, activation and concrete runtime authorization are distinct. Installation is inert; activation binds an immutable reviewed revision/scope; effects still use normal policy.
3. **Security-relevant changes create revisions** — package/source bytes, endpoint/stdio definition, executable components, requested capabilities, Skill manifest/content binding or other authority-relevant identity changes require new review/activation.
4. **MCP identity is app-owned** — local server/revision identity binds the canonical connection definition and scope. Server names/versions, cache hints and authentication are not application trust or permission.
5. **MCP authorization is not local permission** — effectful operations still use Tool Runtime + Policy Core; MRTR/elicitation answers are input, not approval; remote MCP Tasks remain distinct from local Agent Task/Run.
6. **stdio activation is process execution** — import/install never spawns. Activation uses reviewed structured executable/args/cwd, minimal environment/secret references and app-owned process supervision.
7. **MCP Skills converge without trust promotion** — `io.modelcontextprotocol/skills` is distribution/discovery, not a second instruction runtime. Activated MCP Skills normalize into Extension-Core-owned Product Skill revisions while retaining origin-tagged remote-untrusted instruction provenance; same-name origins cannot silently shadow one another.
8. **MCP Skill activation is per-Skill and content-bound** — approval binds server revision + Skill URI + held manifest/frontmatter/content revision. Supporting reads stay origin-scoped/lazy/bounded; changed content invalidates prior activation; nested Skills require separate activation; dynamic/not-content-bindable Skills are not persistently activated in V1. Digests bind content, not trust.
9. **Skill metadata cannot grant capability** — `allowed-tools`, hooks/scripts and similar metadata never authorize host effects. Discovery/fetch/activation never executes bundled code. Skill-caused host execution requires Skill-revision-scoped authorization plus the normal concrete Tool Runtime/Policy Core decision, with causal provenance retained.
10. **No arbitrary in-process third-party extension code** — installed plugin/Skill code never dynamically executes inside Electron renderer/preload/main or core packages. Future executable extensions require an isolated worker/runtime and a narrow versioned capability bridge with no ambient DB/SecretStore/Electron/Node/full-environment/filesystem/network authority.
11. **Extension UI is host-controlled or sandboxed** — no arbitrary privileged-renderer React/DOM injection. Rich extension UI requires host-rendered declarative components or a sandboxed view boundary with explicit bridge/network/navigation permissions and no direct Electron/Node/secrets/storage access.
12. **Local inference has explicit trust facts** — endpoint class, process ownership, capability provenance/freshness and model source/revision/integrity are explicit where known. Connecting never widens runtime network exposure; cleanup terminates only exact app-owned process identity.
13. **Model artifacts are data unless explicitly elevated** — unsafe/custom repository code or pickle-like loading is never enabled silently and never runs in Electron host processes; use an explicit isolated worker/runtime boundary.
14. **Opaque hosted capabilities stay opaque** — provider/local-runtime hosted tools or runtime-managed MCP cannot masquerade as Tool Runtime tools or inherit per-call local approval guarantees.

These rules refine existing ownership and do not require speculative marketplace/executable-extension packages before their roadmap phase.

## Consequences

- Untrusted repositories remain readable without automatically becoming behavioral authority.
- Extension UX and persistence must preserve exact source/revision/capability/trust provenance.
- Executable third-party plugins require real isolation/capability mediation, not a convenient dynamic import.
- Local-model support needs endpoint/process/artifact metadata beyond ordinary provider configuration.
- Ecosystem features that cannot be represented without misleading authorization claims remain disabled or explicitly opaque.

## Alternatives considered

- Trust repository behavior on folder open: rejected because read access is not behavioral authority.
- Treat installed/signed plugins as trusted app code: rejected because provenance/signatures do not provide least privilege.
- Give MCP Skills a parallel runtime: rejected because it duplicates precedence, revision and permission semantics.
- Treat Skill digests as trust: rejected because origin supplies both manifest and bytes; hashes prove consistency only.
- Treat loopback/local models as inherently trusted: rejected because endpoint/process/model/tool execution can still be unsafe or externally owned.

## Verification / revisit

`TEST_STRATEGY.md` owns deterministic verification for these invariants, including workspace trust, inert install/update, stdio activation, MCP identity/auth/MRTR/Tasks, Skills-over-MCP origin/content binding, plugin isolation/UI boundaries, local-runtime ownership/exposure, model-code isolation and opaque hosted capabilities. Architecture fitness must reject third-party extension loading into privileged host packages.

Any weakening of these trust boundaries, or any future Phase 5 executable-extension model, requires concrete implementation/security evidence, a superseding ADR where architecture changes, and corresponding canonical contract/tests.
