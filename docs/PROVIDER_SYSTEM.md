# Provider and Model System

## 1. Goal

Expose one provider-independent model contract while preserving differences that matter. “Compatible API” means transport compatibility, not identical model capabilities, retry behavior, hosted tools, state handles, errors or stream semantics.

Provider Core is the only owner of vendor transport/protocol behavior. The application transcript/task state remains canonical even when a provider offers server-side conversation/session state. Provider registry/discovery/health APIs may serve Application directly, but user-visible generation attempts are started by the Agent Core execution spine rather than a second chat-specific loop.

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

## 3. Model registry and capability truth

A model entry contains external ID plus a normalized capability snapshot:

```ts
interface ModelCapabilities {
  textInput: CapabilitySupport;
  visionInput: CapabilitySupport;
  audioInput: CapabilitySupport;
  toolCalling: CapabilitySupport;
  parallelToolCalls: CapabilitySupport;
  structuredOutput: 'none' | 'json' | 'json-schema' | 'unknown';
  reasoningControl: CapabilitySupport;
  promptCaching: CapabilitySupport;
  embeddings: CapabilitySupport;
  imageGeneration: CapabilitySupport;
  maxContextTokens?: number;
  maxOutputTokens?: number;
}

type CapabilitySupport = 'supported' | 'unsupported' | 'unknown';
```

Capability facts carry provenance/freshness where practical: provider-declared, maintained preset, probed, inferred, or user override, plus `observedAt`/version and optional expiry. **Unknown is not false.** A route that requires a capability must not assume support from a model name or compatible transport shape.

Discovery failure does not silently delete user-configured models or convert previously known facts to unsupported. Stale/unknown data is surfaced and may make a candidate ineligible when the requested feature requires positive support.

## 4. Adapter contract

Each protocol adapter owns:

- request serialization;
- stream parsing and stream-state validation;
- application-tool-call conversion;
- structured-output configuration;
- usage extraction;
- provider error translation;
- cancellation/timeout behavior;
- model discovery mapping;
- provider-specific compatibility options;
- provider request/response/session IDs as diagnostics/continuation metadata.

It does not execute local tools or decide local permissions.

## 5. Prepared request and attempt binding

`PROMPT_RUNTIME.md` owns the canonical provider-neutral `PreparedModelRequest`; Provider Core must not define a second semantic-request contract. A concrete provider call binds that immutable request to one route candidate:

```ts
interface ProviderAttemptSpec {
  modelAttemptId: string;
  candidate: RouteCandidateRef;
  semanticRequestId: string;
  requestFingerprint: string;
  continuation?: ProviderContinuationRef;
}
```

Provider Core first resolves the per-turn `RoutePlan`; Prompt Runtime prepares one request inside that plan's shared envelope; each `modelAttemptId` then binds that same immutable request to exactly one eligible candidate. Provider/model selection is attempt metadata, not mutable prompt content.

Adapters may derive wire-only fields/caching hints, but they must not alter logical instruction order, tool meaning, required modality/schema semantics, or application policy. Unsupported options are rejected or degraded only through an explicit recorded capability decision; silent behavior changes are forbidden.

## 6. Attempt model, retries and commit boundary

Each concrete provider call has a `modelAttemptId` linked to `taskId`/`runId`/`turnId`, provider/model candidate and `PreparedModelRequest.requestFingerprint`. Retries and fallbacks create new attempt records; they never overwrite the failed attempt.

Retry only failures classified as transient and safe at the current commit boundary. Respect provider retry metadata such as `Retry-After` when valid, use bounded backoff/jitter, and cap total attempt/time/cost budgets.

Automatic retry/fallback is normally safe only before the attempt has committed user-visible output or generated a tool request that has been persisted/acted on. **Commit** means normalized semantic output/tool intent has crossed the adapter boundary and has been emitted into the user-facing runtime stream, persisted, or acted upon; transport headers, provider request IDs, keepalives, cache metadata, or usage-only frames do not by themselves commit a user-visible attempt. After that point:

- do not concatenate a restarted attempt as if it were the same stream;
- do not replay already committed tool side effects;
- use provider-native continuation only when its semantics are understood and recorded;
- otherwise end the attempt and let Agent Core surface/recover explicitly.

Provider idempotency/request keys, when supported, are an optimization/safety aid and are scoped to the vendor call. They do not replace application `modelAttemptId` or Tool Runtime side-effect controls.

## 7. Stream events and accumulator invariants

Normalize provider streams into stable app events such as:

- response/message started;
- text delta;
- reasoning/activity metadata only when provider legitimately exposes a user-visible form;
- tool call started/argument delta/completed;
- citation/source metadata;
- usage update;
- completion/stop reason;
- normalized error.

The adapter maintains an explicit per-attempt stream state machine. It must handle partial tool arguments, duplicate/late terminal frames, malformed ordering, disconnects and usage-only frames without leaking vendor event names into Agent Core/React.

A normalized terminal outcome is emitted once per attempt. The adapter/accumulator also produces a canonical final normalized message/tool-request snapshot from the accepted stream state; durable history/restart uses that final snapshot rather than requiring replay of every delta. If a stream ends ambiguously without a valid terminal frame, preserve any already-committed partial-output evidence that can be safely finalized, but classify the attempt as interrupted/protocol failure rather than inventing completion. V1 may lose the final unpersisted transient tail that was visible immediately before a process crash; that tail must never be reconstructed as completed content.

Provider-native tool-use identifiers are transport metadata. When an adapter accepts a provider tool request, it assigns/correlates an application `toolCallId` and stores the provider-native tool reference under the originating `modelAttemptId`. Canonical normalized history relates tool request/result using the application ID; an adapter may map that relation back to the vendor-required identifier when continuing the same provider protocol.

## 8. Error model

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
- `StreamInterruptedError`

Normalized errors include safe retryability/fallback metadata where known, while preserving provider details in a redacted diagnostic payload. UI receives an actionable normalized message, not raw vendor bodies.

## 9. Routing and RoutePlan

### V1 route

A route is an ordered list of candidate model/provider pairs plus eligibility rules. Before Context/Prompt assembly, Provider Core resolves it into an immutable `RoutePlan` for the turn.

Conceptually the plan contains:

- ordered eligible candidate snapshots with provider/model IDs and capability-fact versions;
- primary candidate;
- the subset eligible for **transparent automatic fallback**;
- a shared request envelope: required modalities/tool/schema features, conservative context/output budget and relevant provider constraints;
- retry/fallback policy snapshot.

Resolution:

1. filter disabled/unhealthy candidates according to explicit policy;
2. require positive support for capabilities the task actually needs;
3. compute a request/context envelope that every transparent-fallback candidate can honor;
4. select the first eligible candidate as primary;
5. Prompt/Context prepare one immutable request within that envelope;
6. apply bounded retry policy for eligible pre-commit transient failures;
7. on an explicit fallback-triggering failure, create an attempt for the next candidate **only if it remains compatible with the prepared envelope**;
8. record every attempted and actual model/provider used.

Do not silently truncate/repack the in-flight prepared request to fit a smaller fallback candidate. A candidate requiring different context/tool/schema semantics is not a transparent fallback for that RoutePlan; recovery requires explicit re-preparation/new turn semantics.

Do not hide moderation/refusal behavior by automatically routing around it unless the user-defined route explicitly permits that behavior and policy allows it.

### Later

Potential conditions: context size, cost ceiling, latency, rate limit, local/cloud preference. Do not implement adaptive scoring before observability and test coverage exist.

## 10. Application tools vs provider-hosted capabilities

Application/local/MCP/extension tools exposed as `NormalizedToolSchema` are executed through Tool Runtime + Policy Core.

Provider-hosted/server-executed capabilities are **not** ordinary application tools because the provider may execute them remotely without Tool Runtime seeing each inner side effect. Therefore V1 rules are:

- do not disguise a provider-hosted capability as a local Tool Runtime tool;
- keep provider-hosted capabilities disabled unless a feature explicitly models them;
- enabling one requires declared data/side-effect class, user-visible provider attribution and an explicit policy/config decision before the request;
- never rely on a hosted capability for filesystem/shell/Git/credential mutations of the local workspace;
- if per-invocation authorization cannot be enforced, its permission scope must be conservative enough for the whole hosted capability.

A future hosted-capability abstraction may expand this, but it must not weaken D-005 Tool Runtime + Policy Core mediation for local effectful actions.

## 11. Provider-owned continuation state

Some providers expose response/session/conversation IDs or require opaque replay-safe continuation blocks/tokens for features such as provider-managed state, tool turns or protected reasoning metadata. Store these as bounded provider-scoped continuation metadata linked to the canonical application conversation/turn/attempt. Prompt Runtime does not interpret vendor-private state.

Each attempt records the continuation strategy it used, for example `canonical_replay` or `provider_handle`. Do not accidentally combine a server-managed continuation handle with duplicated locally replayed history when that provider would count/process both.

Rules:

- local normalized messages/events remain sufficient to explain user-visible conversation semantics and application tool intent/results;
- opaque vendor state may be required to continue a specific provider feature, but deleting/expiring it must not destroy local product history;
- provider continuation state is never shared across incompatible provider instances/accounts/models unless the adapter explicitly proves compatibility;
- a resumed vendor continuation must still obey current local policy/tool exposure and record the effective request/config snapshot;
- continuation metadata never authorizes local side effects and never replaces `taskId`/`runId`/`turnId`/`modelAttemptId`;
- if provider-side state cannot be safely reconciled after crash, end that continuation path and re-prepare from canonical local state rather than guessing what the provider retained;
- if canonical replay cannot reproduce semantics required by a provider-only opaque state feature, surface that limitation instead of fabricating equivalence.

## 12. Usage and cost

Normalize where available:

- input tokens;
- cached input tokens;
- output tokens;
- reasoning tokens if provider explicitly reports them;
- request duration;
- TTFT;
- monetary cost;
- provider/model/route/project/conversation/task/run/turn/attempt.

Usage belongs first to the concrete `modelAttemptId`; aggregate upward deliberately. Failed/retried attempts may still incur tokens/cost and must not disappear from totals. Unknown fields stay unknown, not zero. Pricing may come from provider metadata or user overrides, with effective date/source recorded.

## 13. Provider-specific notes

### OpenAI-family

Support modern Responses-style workflows where useful, but keep compatibility endpoints behind the same adapter family. Strict function schemas have provider-specific constraints; validate before request. Response/session IDs remain adapter metadata, not canonical application state.

### Anthropic

Map content blocks/tool-use/tool-result semantics into normalized events. Preserve any provider-required opaque replay-safe thinking/tool continuation material exactly when the protocol requires it, without promoting private reasoning into product-visible history. Distinguish provider-executed server capabilities from application-executed tools.

### Gemini

Map function calls and structured output separately; validate supported schema subset/capabilities.

### Compatible gateways

OpenRouter, LiteLLM, LM Studio, vLLM, llama.cpp, 9Router-like gateways may expose OpenAI-/Anthropic-shaped APIs with different extensions and gaps. Store compatibility settings per provider instance and do not assume upstream parity.

## 14. Provider test harness

Create a local fake provider capable of deterministic scenarios:

- normal streaming;
- non-streaming;
- one/multiple tool calls;
- partial tool arguments;
- malformed/out-of-order/duplicate terminal frames;
- delayed first token;
- timeout/disconnect before first committed output;
- disconnect after partial committed output;
- auth error;
- rate limit with retry metadata;
- context overflow;
- capability unknown/rejection;
- usage update variations, including failed-attempt cost;
- retry/fallback attempt correlation;
- cancellation;
- provider continuation handle/opaque-state expiry or mismatch;
- application `toolCallId` ↔ provider-native tool-use ID correlation across tool-result continuation.

Core CI must not require paid APIs.
