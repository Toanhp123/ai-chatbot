# Provider and Model System

## 1. Goal

Expose one provider-independent model contract while preserving differences that matter. “Compatible API” means transport compatibility, not identical model capabilities or error/stream semantics.

## 2. Provider registry

A provider instance conceptually contains:

```ts
interface ProviderConfig {
  id: string;
  displayName: string;
  protocol: 'openai' | 'anthropic' | 'gemini' | string;
  baseUrl: string;
  auth: AuthConfigRef;
  headers?: Record<string, SecretAwareValue>;
  discovery: ModelDiscoveryStrategy;
  enabled: boolean;
}
```

Provider presets are convenience configuration, not branches throughout the core.

## 3. Model registry

A model entry contains external ID plus a normalized capability snapshot:

```ts
interface ModelCapabilities {
  textInput: boolean;
  visionInput?: boolean;
  audioInput?: boolean;
  toolCalling?: boolean;
  parallelToolCalls?: boolean;
  structuredOutput?: 'none' | 'json' | 'json-schema';
  reasoningControl?: boolean;
  promptCaching?: boolean;
  embeddings?: boolean;
  imageGeneration?: boolean;
  maxContextTokens?: number;
  maxOutputTokens?: number;
}
```

Every capability should carry provenance where practical: provider-declared, preset, probed, inferred, or user override.

## 4. Adapter contract

Each protocol adapter owns:

- request serialization;
- stream parsing;
- tool-call conversion;
- structured-output configuration;
- usage extraction;
- provider error translation;
- cancellation/timeout behavior;
- model discovery mapping;
- provider-specific compatibility options.

It does not execute local tools.

## 5. Normalized request

`PROMPT_RUNTIME.md` owns assembly of this provider-neutral request; Provider Core validates capabilities and adapters serialize it. Conceptually:

```ts
interface ModelRequest {
  model: ModelRef;
  messages: NormalizedMessage[];
  tools?: NormalizedToolSchema[];
  responseSchema?: JsonSchema;
  attachments?: NormalizedAttachmentRef[];
  sampling?: SamplingOptions;
  reasoning?: ReasoningOptions;
  maxOutputTokens?: number;
  metadata?: RequestMetadata;
}
```

Adapters must reject or degrade unsupported options explicitly. Silent behavior changes should be avoided.

## 6. Stream events

Normalize provider streams into stable app events such as:

- response/message started;
- text delta;
- reasoning/activity metadata only when provider legitimately exposes a user-visible form;
- tool call started/argument delta/completed;
- citation/source metadata;
- usage update;
- completion/stop reason;
- normalized error.

Do not leak raw provider event types into React.

## 7. Error model

At minimum:

- `AuthenticationError`
- `RateLimitError`
- `ProviderUnavailableError`
- `TimeoutError`
- `ContextLimitError`
- `CapabilityUnsupportedError`
- `InvalidRequestError`
- `ModelUnavailableError`
- `ProtocolError`

Preserve provider details in a safe diagnostic payload while UI receives an actionable normalized message.

## 8. Routing

### V1 route

A route is an ordered list of candidate model/provider pairs plus eligibility rules.

Resolution:

1. filter disabled/unhealthy candidates according to explicit policy;
2. filter capability mismatch;
3. try primary candidate;
4. apply bounded retry policy for transient errors;
5. if fallback-triggering error occurs, move to next candidate;
6. record actual model/provider used.

Do not hide moderation/refusal behavior by automatically routing around it unless the user-defined route explicitly permits that behavior and policy allows it.

### Later

Potential conditions: context size, cost ceiling, latency, rate limit, local/cloud preference. Do not implement adaptive scoring before observability and test coverage exist.

## 9. Usage and cost

Normalize where available:

- input tokens;
- cached input tokens;
- output tokens;
- reasoning tokens if provider explicitly reports them;
- request duration;
- TTFT;
- monetary cost;
- model/provider/route/project/conversation/task.

Unknown fields stay unknown, not zero. Pricing may come from provider metadata or user overrides, with effective date/source recorded.

## 10. Provider-specific notes

### OpenAI-family

Support modern Responses-style workflows where useful, but keep compatibility endpoints behind the same adapter family. Strict function schemas have provider-specific constraints; validate before request.

### Anthropic

Map content blocks/tool-use/tool-result semantics into normalized events. Distinguish provider-executed server tools from application-executed tools.

### Gemini

Map function calls and structured output separately; validate supported schema subset/capabilities.

### Compatible gateways

OpenRouter, LiteLLM, LM Studio, vLLM, llama.cpp, 9Router-like gateways may expose OpenAI-/Anthropic-shaped APIs with different extensions and gaps. Store compatibility settings per provider instance and do not assume upstream parity.

## 11. Provider test harness

Create a local fake provider capable of deterministic scenarios:

- normal streaming;
- non-streaming;
- one/multiple tool calls;
- malformed stream chunk;
- delayed first token;
- timeout;
- disconnect mid-stream;
- auth error;
- rate limit with retry metadata;
- context overflow;
- capability rejection;
- usage update variations;
- duplicate/out-of-order edge cases where protocol permits malformed input.

Core CI must not require paid APIs.
