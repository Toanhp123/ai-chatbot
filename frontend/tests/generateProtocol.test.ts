import assert from "node:assert/strict";
import test from "node:test";

import {
  parseSseDataLine,
  resolveDoneGeneratedText,
} from "../src/features/generate/model/protocol.ts";

test("generation protocol parses typed SSE data lines", () => {
  assert.deepEqual(
    parseSseDataLine('data: {"type":"token","token":"xin"}'),
    { type: "token", token: "xin" },
  );
  assert.equal(parseSseDataLine("event: token"), null);
});

test("done fallback never copies the prompt into the assistant response", () => {
  assert.equal(
    resolveDoneGeneratedText(
      { type: "done", full_text: "PromptAnswer" },
      "Prompt",
    ),
    "Answer",
  );
  assert.equal(
    resolveDoneGeneratedText(
      { type: "done", full_text: "PromptAnswer", generated_text: "Canonical" },
      "Prompt",
    ),
    "Canonical",
  );
});

test("done fallback rejects an unverifiable full_text payload", () => {
  assert.equal(
    resolveDoneGeneratedText(
      { type: "done", full_text: "DifferentPromptAnswer" },
      "Prompt",
    ),
    undefined,
  );
});
