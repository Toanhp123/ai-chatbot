# Local AI Runtime System

## 1. Strategy

Early local AI support integrates maintained inference runtimes/endpoints instead of embedding a custom inference engine into the desktop application.

Initial runtime families may include:

- Ollama;
- llama.cpp server;
- LM Studio;
- vLLM / compatible servers;
- user-configured OpenAI-/Anthropic-compatible endpoints.

A runtime family name is a compatibility hint, not a security or capability guarantee.

## 2. Two independent layers

### Provider-compatible generation

If a local runtime exposes a supported inference protocol, Provider Core treats it as a configured Provider endpoint. All user-visible generation still uses the normal Agent Core → Prompt Runtime → Provider Core spine.

### Runtime management

Optional runtime-specific adapters may support:

- discover installed/loaded models;
- load/unload;
- inspect context/quantization/size/runtime version;
- download/delete model artifacts through the runtime's supported API;
- runtime health/status.

Chat must not depend on management support. A runtime can be a valid generation endpoint even when the app cannot manage its process/models.

## 3. Runtime ownership

Represent ownership explicitly:

- **external** — user/another app owns the runtime process; this app only connects;
- **app-managed** — the app intentionally launched the process and owns that child lifecycle;
- **unknown** — discovered endpoint without reliable ownership evidence.

The app must not stop/kill an external or unknown runtime merely because a project/provider is removed. App-managed cleanup acts only on the exact process identity it created.

Automatic port scanning or LAN-wide discovery is not a default requirement. Prefer explicit configuration and bounded loopback discovery offered by the runtime itself.

## 4. Endpoint trust class

Store a normalized endpoint classification derived from the actual canonical destination, not only from the user's label:

- `loopback`;
- `lan`;
- `remote`;
- `unknown`.

A URL containing `localhost` is not itself proof of a security property; canonicalization/resolution/redirect policy still applies.

Rules:

- default discovery/configuration to loopback;
- clearly label LAN/remote endpoints;
- bind auth secrets to the canonical endpoint/origin;
- do not forward credentials across an untrusted redirect;
- do not assume loopback endpoints are authenticated;
- never expose/rebind a runtime to LAN as a side effect of connecting it;
- runtime-native CORS/network exposure remains the runtime owner's setting and must be surfaced when detectable.

## 5. Capability truth

“OpenAI-compatible” means wire similarity, not complete behavioral equivalence.

Every local model/runtime capability therefore carries provenance/freshness such as:

- runtime-advertised;
- model metadata;
- tested/probed;
- user override;
- unknown.

Track independently where relevant:

- text/chat;
- vision/audio modalities;
- tool calling;
- parallel tools;
- structured output/schema support;
- reasoning/thinking controls;
- max context/output limits;
- tokenizer/chat-template requirements;
- streaming/cancellation semantics.

Unknown is preferable to invented support.

## 6. Local runtime entity

Conceptually:

```ts
interface LocalRuntime {
  id: string;
  kind: 'ollama' | 'llamacpp' | 'lmstudio' | 'vllm' | 'custom';
  endpoint: string;
  endpointClass: 'loopback' | 'lan' | 'remote' | 'unknown';
  ownership: 'external' | 'app-managed' | 'unknown';
  authRef?: string;
  managementCapabilities: string[];
  runtimeRevision?: string;
  capabilitySnapshotHash?: string;
  health: RuntimeHealth;
}
```

Concrete types may evolve, but endpoint/ownership/capability provenance must remain explicit.

## 7. Local model identity and metadata

A local model record is scoped to its runtime/source revision. Track where known:

- runtime/external model ID;
- source repository/artifact + immutable revision/digest;
- family/architecture;
- parameter count;
- quantization/format;
- disk size;
- context length;
- modality/tool/structured-output capabilities;
- tokenizer/chat-template metadata;
- license/source;
- loaded state;
- estimated RAM/VRAM/unified-memory requirement.

Do not identify a model only by a mutable display name such as `latest`.

## 8. Model artifact trust

Downloaded model repositories may contain executable or unsafe serialized content.

Policy:

- prefer data-only formats and maintained runtime loaders;
- prefer content-addressed/checksummed artifacts and immutable source revisions when available;
- prefer `safetensors`, GGUF or another data-oriented format over pickle-based weights when the selected runtime supports it;
- never enable `trust_remote_code`/arbitrary repository code silently;
- custom model/tokenizer/helper code is an explicit high-risk capability and must run only in an isolated worker/runtime boundary, never inside Electron renderer/preload/main;
- signatures/scanners/source reputation are evidence, not proof of safety;
- preserve license/source/revision/integrity metadata with downloaded artifacts.

A model update/re-download that changes artifact bytes/revision creates a new model revision rather than mutating trusted metadata invisibly.

Model Lab outputs enter Local Models only through the promotion contract in `MODEL_LAB.md`: registration references an immutable `ModelArtifactRevision`, appends an immutable Model Promotion Record, preserves the exact base-model dependency for adapters, and carries TrainingPlan/DatasetRevision/EvaluationRun lineage. Registration is distinct from runtime load/activation state. Training completion or the existence of a checkpoint is not sufficient to register or load a model.

## 9. Provider-hosted/runtime-hosted tools

Some local runtimes can invoke tools/MCP or execute server-side capabilities themselves. That can bypass the app's per-operation policy if enabled opaquely.

Therefore:

- runtime/provider-hosted tools are disabled by default unless an explicit product feature models them;
- do not send local filesystem/shell/Git/credential tools to a runtime that will execute them outside Tool Runtime + Policy Core;
- if a runtime can call its own configured MCP servers, treat that as an external opaque capability, not as equivalent to the app's MCP Host;
- the UI must not claim local per-call approval guarantees for actions executed inside an opaque runtime/provider.

## 10. Runtime-management effects

Management operations such as model download/delete, load/unload, process start/stop or changing network exposure are effectful application operations.

- explicit user UI actions may be coordinated by Application through reviewed adapters;
- agent-initiated management actions, if ever exposed as tools, must go through Tool Runtime + Policy Core;
- destructive delete distinguishes registry metadata removal from deleting artifact bytes;
- app-managed process launch uses structured executable/args/env/cwd, not shell interpolation;
- secret-bearing environment state is allowlisted, not inherited wholesale.

## 11. Resource admission and responsiveness

Local inference can exhaust RAM/VRAM/disk and freeze the desktop.

Before heavy load/download where data is available:

- estimate model + runtime + context/KV-cache overhead conservatively;
- compare with current free/total resources;
- warn or block clearly impossible configurations;
- limit concurrent heavyweight load/download/management operations;
- keep renderer work non-blocking and expose progress/cancel/error state.

Fit estimates are advisory because runtime overhead and model behavior vary.

## 12. Hardware inventory

Collect only hardware facts needed for fit guidance:

- CPU architecture/cores;
- system RAM;
- GPU vendor/model;
- VRAM where queryable;
- Apple unified memory;
- accelerator/runtime features where practical.

Hardware inventory is local diagnostic/product data; do not transmit it remotely by default.

## 13. Model Hub — later

A model browsing layer may integrate registries such as Hugging Face, but must show at least:

- source/publisher;
- immutable revision when selected;
- license;
- format/architecture;
- quantization;
- size/fit estimate;
- custom-code requirement;
- compatible runtimes;
- integrity metadata where available.

Downloading a repository is not authorization to execute its code.

## 14. Phase ownership

This document owns the Local AI subsystem contract. Phase 7 deliverables and acceptance are owned only by `ROADMAP.md`; tests that prove those requirements are owned by `TEST_STRATEGY.md`.
