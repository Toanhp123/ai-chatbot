# Application and Adapter Gateway Cleanup Design

## Goal

Make Adapters and Application the stable communication gateway of the modular monolith before any deep core cleanup. Adapters own only transport/conversion/I/O. Application owns use-case orchestration and policy. Runtime mechanics, synchronization, resource ownership, model/trainer/session internals, filesystem mechanics, and algorithm implementation live behind Application-owned ports in inner capability/core modules.

## Non-goals

- Do not optimize model, generation, data, or training algorithms.
- Do not redesign HTTP payloads or frontend behavior.
- Do not move business/use-case policy into adapters.
- Do not expose new capability runtime types through Application public APIs.

## Target boundaries

1. `src/adapters/**` may import `src.application/**` contracts and standard/third-party I/O libraries, but must not import `src.core`, `src.data`, `src.models`, `src.training`, `src.inference`, `src.generation`, or `src.utils`.
2. `src/application/**` may depend on stable domain/config value types where necessary, but must not instantiate concrete capability runtimes or own thread/lock/event/file execution mechanics.
3. Application public `__init__.py` modules must not re-export concrete types from capability modules.
4. A single composition root owns concrete construction and is the only production location that knows Adapter + Application + inner concrete implementations together.
5. CLI and HTTP adapters call use cases through one typed `ApplicationServices` gateway rather than assembling service graphs or using many independent `app.state.*` service locators.
6. Outer adapters never receive `EngineConfig` or other inner runtime objects through the gateway. Configuration is exposed through Application-owned mappings/DTOs (`ConfigGateway`, `LoggingSettings`).

## Wave 1 — Stable Application boundary

- Introduce Application-owned runtime ports for inference, generation admission, accelerator ownership, background execution/events, training runtime, checkpoint resolution, and observer/control contracts.
- Introduce `ApplicationServices` typed gateway.
- Introduce public `ConfigGateway`; keep `ConfigurationService` internal to Application/composition and prevent `EngineConfig` from crossing into adapters.
- Stop exporting `GenerationSession`, `PreparedTrainingRun`, `TrainingRunFactory`, `TrainingObserver`, and `TrainingPreparationAborted` from Application public APIs.
- Keep existing externally observable HTTP/CLI semantics.

## Wave 2 — Adapter cleanup

- Change YAML adapter to return/parse raw mappings and perform atomic file I/O only. Application performs defaults, override application, canonical validation, activation, and snapshot policy.
- Move resume-checkpoint path resolution behind an Application-owned port injected from a filesystem adapter.
- Make CLI call one Application use case per action; interactive prompt rendering remains CLI-owned.
- Store one `ApplicationServices` object in FastAPI state and route all endpoint calls through it.

## Wave 3 — Remove mechanics from Application

- Move accelerator synchronization implementation from Application to core runtime mechanics.
- Move generation admission synchronization implementation from Application to inference capability.
- Application inference service receives runtime/admission/accelerator ports; it does not construct `InferenceRuntime`, expose model/tokenizer/generator, or expose runtime locks.
- Application training background coordinator receives background execution/event/accelerator ports. It does not import concrete training execution/event/runtime classes.
- Training runtime concrete construction remains in the training capability and is injected by composition.

## Wave 4 — Architecture ratchet

- Extend architecture tests to reject adapter inner-module imports, direct outer imports of Application implementation modules, capability concrete construction from Application, runtime re-exports from Application, and multiple FastAPI service-locator state entries.
- Add contract tests for composition root wiring and adapter/config ownership.
- Run focused tests, full Python suite, architecture gate, and available frontend verification.

## Compatibility

Internal tests that directly mutated `InferenceService.model/tokenizer/generator` or depended on Application-exported capability internals are implementation-coupled and will be migrated to injected fakes or capability-level tests. Public HTTP response shapes and CLI commands remain stable.

## Exit criteria

- No Adapter imports inner modules.
- No Application production file imports concrete `InferenceRuntime`, `TrainingRunFactory`, `BackgroundExecution`, `TrainingEventHub`, or `AcceleratorCoordinator`.
- No Application public API re-exports capability runtime classes.
- Concrete graph is built only by composition root.
- HTTP routes access `request.app.state.services` only for application operations.
- `ApplicationServices.config` is a `ConfigGateway`; CLI/UI cannot call `ConfigurationService.resolve/current` or consume `EngineConfig`.
- Outer adapters cannot import Application implementation modules such as `config.service`, `inference.service`, or `training.background/launch/service`.
- Full Python test suite passes and architecture checks encode the new rules.
