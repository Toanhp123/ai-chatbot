import assert from "node:assert/strict";
import test from "node:test";

import { generationConfigToSamplingParams } from "../src/features/generate/model/configMapping.ts";

test("canonical generation config hydrates playground sampling controls", () => {
  assert.deepEqual(
    generationConfigToSamplingParams({
      max_new_tokens: 77,
      temperature: 0.23,
      top_k: 7,
      top_p: 0.81,
      min_p: 0.12,
      repetition_penalty: 1.17,
      do_sample: false,
      use_cache: false,
    }),
    {
      temperature: 0.23,
      topK: 7,
      topP: 0.81,
      minP: 0.12,
      repetitionPenalty: 1.17,
      maxNewTokens: 77,
      doSample: false,
      useCache: false,
      stopWords: "",
    },
  );
});

import { buildGenerationSamplingOverrides } from "../src/features/generate/model/configMapping.ts";

test("unhydrated playground never leaks visual fallback sampling defaults into backend request", () => {
  const params = {
    temperature: 0.8,
    topK: 40,
    topP: 0.9,
    minP: 0.05,
    repetitionPenalty: 1.1,
    maxNewTokens: 128,
    doSample: true,
    useCache: true,
    stopWords: "",
  };

  assert.deepEqual(buildGenerationSamplingOverrides(params, false, new Set()), {});
  assert.deepEqual(
    buildGenerationSamplingOverrides(params, false, new Set(["temperature"])),
    { temperature: 0.8 },
  );

  assert.deepEqual(buildGenerationSamplingOverrides(params, true, new Set()), {
    temperature: 0.8,
    top_k: 40,
    top_p: 0.9,
    min_p: 0.05,
    repetition_penalty: 1.1,
    max_new_tokens: 128,
    greedy: false,
    use_cache: true,
  });
});
