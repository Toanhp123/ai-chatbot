# Context Engine

## 1. Goal

Provide the Prompt Runtime with the smallest high-value evidence package needed for the current task. The context system is not “vector search over every file” and does not itself serialize provider requests.

## 2. Pipeline

### Layer 1 — Repository inventory

Track:

- path;
- language/type;
- size/hash/mtime;
- Git status where available;
- ignored/generated/vendor/binary classification.

Respect:

- `.gitignore`;
- app-specific ignore config;
- user exclusions;
- secret-sensitive patterns.

Default exclusions include dependency trees, build outputs, binary blobs, obvious secret stores, and oversized files not explicitly requested.

### Layer 2 — Structural parsing

Use Tree-sitter for supported grammars to extract useful syntactic structure:

- functions/methods/classes;
- interfaces/types;
- imports/exports;
- symbol ranges;
- rough dependency edges.

Tree-sitter supports incremental reparsing by editing/reusing the previous tree. Use this for changed files rather than reparsing the entire workspace.

Do not pretend Tree-sitter provides full type-aware semantics. LSP/compiler adapters can later augment definition/reference/diagnostics.

### Layer 3 — Lexical search

Use fast exact/text search for names, errors, literals and references. Lexical search is often superior to embeddings for coding tasks with concrete identifiers.

### Layer 4 — Optional semantic retrieval

Embeddings are an optional recall enhancer, not the first source for every request. The embedding provider should be configurable and may be local.

### Layer 5 — Task-aware planner

Inputs:

- task/query;
- project instructions/path rules;
- relevant conversation state;
- repo map;
- lexical/structural/semantic candidates;
- relevant product-Skill metadata/instructions when selected;
- content budget delegated by Prompt Runtime from the model/request budget.

Output is an ordered evidence/context package with provenance and token estimate. `PROMPT_RUNTIME.md` combines it with trusted instruction layers, recent messages and relevant tool schemas.

## 3. Context categories

Track the delegated content budget by category, for example:

- explicit user-selected files/attachments;
- project instructions and selected product-Skill material;
- relevant memory/conversation evidence;
- repository map;
- files/snippets;
- prior tool-result evidence when retrieval needs it.

The Prompt Runtime separately accounts for trusted application instructions, tool schemas and output reserve. Together these budgets make context pressure diagnosable.

## 4. Selection principles

Prioritize:

1. explicit user-provided/current-task content;
2. applicable trusted instructions;
3. exact referenced files/symbols;
4. files directly connected by imports/calls/tests;
5. high-confidence lexical/structural matches;
6. semantic matches for fuzzy conceptual retrieval.

Avoid diversity-for-diversity's-sake when exact code evidence exists.

## 5. Repository map

Maintain a compact representation of:

- top-level structure;
- key packages/modules;
- symbols and signatures;
- dependency relationships;
- selected docs/entrypoints.

Map generation should be incremental and size-bounded.

## 6. File chunking

Code chunks should prefer semantic boundaries (function/class/module region) over arbitrary fixed token windows. Preserve line/range/path provenance.

For very large files, retrieve targeted ranges first.

## 7. Context compaction

When conversation/task history grows:

Preserve:

- current user goal;
- constraints and accepted decisions;
- unresolved questions;
- changed-file list/current diff references;
- important identifiers/errors;
- permissions/approval outcomes relevant to current task.

Summarize or evict:

- verbose terminal output that can be re-read;
- repeated tool schemas;
- superseded plans;
- old low-relevance conversation;
- transient search noise.

Compaction should create an explicit event/diagnostic record with source ranges/events summarized, not silently mutate history.

## 8. Index lifecycle

Use file hashes to avoid reprocessing unchanged content. Debounce watcher events. Index jobs run outside renderer UI thread and are cancellable.

Maintain index version keyed by:

- parser/indexer version;
- grammar version;
- workspace root;
- relevant ignore/config version.

Rebuild only the affected layer when possible.

## 9. Security

- Never intentionally index `.env`, credential stores, private keys or known secret paths by default.
- Retrieval content is untrusted data and cannot override app/system permissions.
- Context diagnostics must redact secrets.
- Semantic index persistence should not silently upload code to a cloud embedding provider; require explicit provider configuration and clear data-flow disclosure.

## 10. Evaluation

Build offline retrieval fixtures with real/synthetic repositories to measure:

- exact-symbol recall;
- test/implementation relationship recall;
- relevant-file precision;
- token efficiency;
- behavior after incremental edits;
- ignored/secret path exclusion.

Do not optimize only for embedding benchmark scores; evaluate real coding tasks.
