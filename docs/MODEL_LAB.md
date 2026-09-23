# Model Lab

## 1. Product promise

Model Lab helps users perform practical post-training/fine-tuning of compatible open-weight models on hardware they control.

Primary methods:

- supervised fine-tuning (SFT);
- LoRA;
- QLoRA.

Later methods may include DPO or other preference optimization after dataset/evaluation foundations are mature.

Do not describe this as training frontier foundation models from scratch.

## 2. Isolation

Training never runs in Electron renderer.

Architecture:

- desktop controller validates inputs and records job;
- isolated Python environment contains ML dependencies;
- worker receives a resolved immutable config;
- worker emits structured progress/events;
- output files live in explicit local directories;
- stop/cancel is supported;
- worker crashes do not crash the desktop UI.

Use `uv` or equivalent reproducible environment management.

## 3. Backends

### NVIDIA / Linux / compatible accelerators

Prefer proven libraries/frameworks instead of custom training loops:

- Hugging Face Transformers;
- PEFT for adapters;
- TRL for SFT/preference workflows;
- Axolotl as a configuration-driven higher-level backend when appropriate.

Backend choice can depend on model family, hardware and requested method.

### Apple Silicon

MLX-LM is the preferred initial candidate for supported LoRA/QLoRA flows because it targets Apple Silicon and supports quantized-model fine-tuning.

### CPU

Allow only small experiments when technically reasonable. UI must warn that meaningful large-model fine-tuning on CPU is generally impractical.

## 4. Canonical workflow

1. Choose base model.
2. Choose/import local dataset.
3. Detect format and convert to canonical internal representation.
4. Validate and show statistics/warnings.
5. Create train/validation/test split or use provided split.
6. Choose backend/method.
7. Estimate hardware/disk requirements.
8. Configure parameters with safe presets.
9. Produce resolved config preview.
10. Launch job.
11. Stream metrics/log summaries.
12. Save checkpoints/adapters.
13. Evaluate.
14. Compare base vs adapted model.
15. Export adapter/merged model when backend supports it.
16. Register result with Local Models.

## 5. Dataset formats

Initial import formats:

- conversational `messages` JSONL;
- instruction/input/output;
- prompt/completion.

Canonical format should preserve roles/content and optional metadata without binding to one training backend's file schema.

## 6. Dataset validation

Detect/report:

- malformed records;
- unsupported/missing roles;
- empty content;
- extreme sequence outliers;
- duplicates/near-duplicates where feasible;
- train/validation leakage heuristics;
- obvious secret patterns;
- unsupported multimodal references;
- encoding problems.

Show statistics:

- record count;
- role distribution;
- length/token distribution using selected tokenizer when available;
- duplicate rate;
- split sizes;
- estimated packed/unpacked training tokens.

Warnings do not silently modify user data unless an explicit transformation is selected.

## 7. Training job config

Persist an immutable resolved snapshot containing:

- backend/version;
- base model/source/revision;
- tokenizer/template config;
- dataset hash/split;
- method;
- rank/alpha/target modules for LoRA where applicable;
- quantization config for QLoRA;
- learning rate/batch/accumulation/epochs or steps;
- max sequence length;
- optimizer/scheduler;
- seed;
- output/checkpoint policy;
- hardware snapshot.

## 8. Metrics/events

Structured events:

- environment preparing;
- model loading;
- dataset preprocessing;
- training started;
- step/epoch;
- train loss;
- validation loss;
- learning rate;
- throughput;
- memory stats when available;
- checkpoint saved;
- evaluation started/result;
- completed/failed/cancelled.

Keep raw logs accessible but avoid making them the only machine-readable status source.

## 9. Evaluation

Fine-tuning is not done at “loss decreased”.

Initial evaluation can include:

- backend validation loss;
- deterministic user-defined prompt suites;
- task-specific exact/structured metrics;
- side-by-side base vs adapter outputs.

Later model-as-judge evaluation must name/configure the judge model and should not produce a single universal quality score.

## 10. Safety/privacy

- Datasets remain local by default.
- No cloud upload without explicit action.
- Do not log raw private examples in global diagnostics by default.
- Downloaded models/custom code follow Local AI security policy.
- Output directory must be validated and disk usage estimated.
- Training cancellation and child-process cleanup are mandatory.

## 11. Backend notes from current research

- PEFT supports LoRA-family configuration including QLoRA-style targeting.
- TRL exposes SFT and DPO trainer abstractions, making it a suitable backend rather than something to reimplement.
- Axolotl supports LoRA/QLoRA/full fine-tuning plus broader advanced methods; use only the subset the product can validate/support.
- MLX-LM supports LoRA/QLoRA on Apple Silicon and adapter/fused export paths for supported models.

Backend feature existence does not mean the UI should expose every knob. Start with stable presets plus an advanced config escape hatch.
