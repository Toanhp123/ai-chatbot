# Local AI Runtime System

## 1. Strategy

Early local AI support integrates existing inference runtimes instead of embedding a new inference engine into the desktop application.

Supported direction:

- Ollama;
- llama.cpp server;
- LM Studio;
- vLLM / compatible servers;
- other user-configured OpenAI-/Anthropic-compatible local endpoints.

## 2. Two layers

### Provider-compatible layer

If a local runtime exposes a supported provider protocol, configure it through Provider Core with a localhost/custom base URL.

### Runtime-management layer

Optional adapters can expose runtime-specific operations such as:

- discover installed/loaded models;
- load/unload;
- inspect quantization/context/size;
- download model via runtime API;
- health/version.

Do not make chat depend on runtime-management support.

## 3. Compatibility reality

“OpenAI-compatible” is not equivalent to complete OpenAI behavior.

Examples from current docs:

- llama.cpp explicitly describes practical compatibility and model/template-dependent tool behavior;
- vLLM documents unsupported/ignored parameters and model-dependent parallel tool behavior;
- LM Studio exposes both compatibility endpoints and richer native APIs;
- Ollama capabilities depend on model support.

Therefore every local model has explicit capability metadata and compatibility notes.

## 4. Local runtime entity

```ts
interface LocalRuntime {
  id: string;
  kind: 'ollama' | 'llamacpp' | 'lmstudio' | 'vllm' | 'custom';
  endpoint: string;
  authRef?: string;
  managementCapability: string[];
  health: RuntimeHealth;
}
```

## 5. Local model metadata

Track where known:

- runtime/external model ID;
- family/architecture;
- parameter count;
- quantization;
- disk size;
- context length;
- vision/tool/structured-output capabilities;
- tokenizer/template metadata where exposed;
- license/source;
- loaded state;
- estimated RAM/VRAM/unified-memory requirement.

Unknown is preferable to invented precision.

## 6. Hardware inventory

Collect non-sensitive local hardware facts:

- CPU architecture/cores;
- system RAM;
- GPU vendor/model;
- VRAM where queryable;
- Apple unified memory;
- supported accelerator/runtime features where practical.

Hardware-fit estimates are guidance, not guarantees. Model/runtime overhead, context length and KV cache can materially change memory use.

## 7. Network exposure

Local servers may bind to localhost or LAN interfaces. The app should:

- default to localhost discovery/configuration;
- clearly label non-local endpoints;
- not assume local endpoints are authenticated;
- never expose a runtime to the network as a side effect of adding it;
- document runtime-specific auth limitations.

## 8. Model Hub — later

A model browsing layer may integrate registries such as Hugging Face, but must show:

- source/publisher;
- license;
- format/architecture;
- quantization;
- size/fit estimate;
- custom-code requirement;
- compatible runtimes.

Never automatically execute arbitrary model repository code. Any remote/custom-code requirement is an explicit advanced action.

## 9. Acceptance criteria for Local AI phase

- detect/configure at least one supported local runtime;
- list or manually configure a model;
- stream chat through normal Provider Core;
- accurately mark provider/runtime used;
- capability mismatch is surfaced, not silently ignored;
- app remains functional if runtime is stopped/restarted;
- no local-runtime code leaks into generic chat UI.
