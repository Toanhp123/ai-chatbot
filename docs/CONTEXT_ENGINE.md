# Context Engine

## 1. Goal

Provide Prompt Runtime with the smallest high-value evidence package needed for the current task. The context system is not “vector search over every file” and does not itself serialize provider requests.

Every returned package is an immutable evidence snapshot with provenance/version identity so the model request can be explained later and stale workspace evidence can be detected before mutation.

## 2. Pipeline

### Layer 1 — Repository inventory

Track:

- workspace/root identity;
- path;
- language/type/encoding where known;
- size/hash/mtime;
- Git status/revision where available;
- ignored/generated/vendor/binary classification.

Respect:

- `.gitignore`;
- app-specific ignore config;
- user exclusions;
- secret-sensitive patterns.

Default exclusions include dependency trees, build outputs, binary blobs, obvious secret stores, and oversized files not explicitly requested.

Multi-root projects preserve root identity on every path/evidence item; identical relative paths in different roots never collapse into one identity.

### Layer 2 — Structural parsing

Use Tree-sitter for supported grammars to extract useful syntactic structure:

- functions/methods/classes;
- interfaces/types;
- imports/exports;
- symbol ranges;
- rough dependency edges.

Tree-sitter supports incremental reparsing by editing/reusing previous trees. Use this for changed files rather than reparsing the entire workspace.

Do not pretend Tree-sitter provides full type-aware semantics. LSP/compiler adapters can later augment definition/reference/diagnostics.

### Layer 3 — Lexical search

Use fast exact/text search for names, errors, literals and references. Lexical search is often superior to embeddings for coding tasks with concrete identifiers.

### Layer 4 — Optional semantic retrieval

Embeddings are an optional recall enhancer, not the first source for every request. The embedding provider is configurable and may be local.

### Layer 5 — Task-aware planner

Inputs:

- task/query;
- project instructions/path rules;
- relevant conversation state;
- workspace/repository snapshot;
- repo map;
- lexical/structural/semantic candidates;
- relevant Product Skill resource/context descriptors when selected; activated Skill instruction bodies themselves are assembled by Prompt Runtime through the Extension Core contract;
- content budget from the current RoutePlan request/context envelope, passed by Agent Core/Application; Prompt Runtime owns final instruction/tool/output headroom and request packing.

Output is an ordered immutable evidence/context package with provenance, versions/hashes and token estimate. Context Engine may select records that already carry trusted-instruction metadata from an approved source contract, but it must not promote ordinary retrieved content into trusted instructions. `PROMPT_RUNTIME.md` owns final trust/preference layering and combines the package with recent messages and relevant tool schemas.

## 3. Context package contract

Conceptually:

```ts
interface ContextPackage {
  id: string;
  contentHash: string;
  workspaceSnapshot: WorkspaceSnapshotRef[];
  createdAt: string;
  queryFingerprint: string;
  items: ContextEvidence[];
  estimatedTokens: number;
}

interface ContextEvidence {
  sourceKind: string;
  rootId?: string;
  sourceRef: string;
  contentHash?: string;
  range?: { start: number; end: number };
  trust: 'trusted-instruction' | 'user-selected' | 'untrusted';
  selectionReason: string;
  estimatedTokens: number;
}
```

The package is immutable once Prompt Runtime prepares a model request. A later filesystem/index change creates a new package/version; it does not mutate evidence already used by an in-flight attempt.

Context hashes are diagnostics/cache identities, not trust assertions.

## 4. Context categories

Track the delegated content budget by category, for example:

- explicit user-selected files/attachments;
- project instructions and selected product-Skill material;
- relevant memory/conversation evidence;
- repository map;
- files/snippets;
- prior tool-result evidence when retrieval needs it.

Prompt Runtime separately accounts for trusted application instructions, tool schemas and output reserve. Together these budgets make context pressure diagnosable.

## 5. Selection principles

Prioritize:

1. explicit user-provided/current-task content;
2. applicable trusted instructions;
3. exact referenced files/symbols;
4. files directly connected by imports/calls/tests;
5. high-confidence lexical/structural matches;
6. semantic matches for fuzzy conceptual retrieval.

Avoid diversity-for-diversity's-sake when exact code evidence exists.

Record why an item was selected so retrieval failures can be debugged without relying on chain-of-thought.

## 6. Repository map

Maintain a compact representation of:

- top-level structure;
- key packages/modules;
- symbols and signatures;
- dependency relationships;
- selected docs/entrypoints.

Map generation is incremental and size-bounded. It is advisory evidence, not a replacement for exact source reads before sensitive changes.

## 7. File chunking

Code chunks prefer semantic boundaries (function/class/module region) over arbitrary fixed token windows. Preserve root/path/range/content-hash provenance.

For very large files, retrieve targeted ranges first. Preserve enough boundary context to avoid presenting a snippet as a complete file/module when it is not.

## 8. Freshness and stale-evidence handling

Workspace evidence is versioned by content hashes and, where available, Git/worktree revision plus root identity.

A model may reason from a context package that becomes stale while the turn is running; this is not automatically an error. Safety is enforced before effects:

- mutating tools validate their own current resource preconditions;
- a stale file hash/revision produces conflict/replan rather than overwrite;
- a later turn refreshes affected context after meaningful workspace changes;
- long-running tasks should not reuse one package indefinitely after tool mutations.

Never infer that “retrieved earlier” means “still current”.

## 9. Context compaction inputs

When conversation/task history grows, Context Engine may help select source evidence for compaction.

Preserve:

- current user goal;
- constraints and accepted decisions;
- unresolved questions;
- changed-file list/current diff references;
- important identifiers/errors;
- permissions/approval outcomes relevant to current task.

Candidates for Prompt Runtime to summarize/compact, or for the request planner to evict:

- verbose terminal output that can be re-read;
- repeated tool schemas;
- superseded plans;
- old low-relevance conversation;
- transient search noise.

Prompt Runtime owns the resulting compaction representation and trust framing. Raw durable history is not destroyed merely because a compacted request view exists.

## 10. Index lifecycle and content addressing

Use file content hashes to avoid reprocessing unchanged content. Debounce watcher events. Index jobs run outside renderer UI thread and are cancellable.

Maintain index version keyed by:

- parser/indexer version;
- grammar version;
- workspace/root identity;
- relevant ignore/config version;
- artifact/index kind.

Rebuild only the affected layer when possible. Branch/worktree switching should reuse content-addressed artifacts when the content is identical while keeping workspace snapshot identity separate.

An index/cache may be dropped and rebuilt without losing user-authored durable state.

## 11. Security

- Never intentionally index `.env`, credential stores, private keys or known secret paths by default.
- Retrieval content is untrusted data and cannot override app/system permissions.
- Context diagnostics must redact secrets.
- Semantic index persistence must not silently upload code to a cloud embedding provider; require explicit provider configuration and clear data-flow disclosure.
- Symlink/path handling follows the same canonical workspace-root rules as filesystem tools; indexing may not escape an approved root by traversing links unexpectedly.

## 12. Evaluation

Build offline retrieval fixtures with real/synthetic repositories to measure:

- exact-symbol recall;
- test/implementation relationship recall;
- relevant-file precision;
- token efficiency;
- behavior after incremental edits/branch changes;
- stale-evidence conflict behavior;
- multi-root path disambiguation;
- ignored/secret path exclusion.

Do not optimize only for embedding benchmark scores; evaluate real coding tasks.
