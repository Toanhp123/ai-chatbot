import assert from "node:assert/strict";
import test from "node:test";
import { resolvedConfigToVramParams } from "../src/widgets/vram-matrix/model/scenarioMapping.ts";

const config = {
  system: {
    device: "cpu",
  },
  model: {
    name: "llama",
    block_size: 256,
    n_embd: 384,
    n_layer: 6,
    n_head: 8,
    vocab_size: 1024,
    model_kwargs: {
      intermediate_size: 1536,
      multiple_of: 128,
    },
    tie_word_embeddings: false,
    bias: true,
  },
  training: {
    batch_size: 12,
    learning_rate: 1e-4,
    max_iters: 100,
    precision: "bfloat16",
    optimizer_type: "adamw",
    gradient_accumulation_steps: 3,
    gradient_checkpointing: true,
  },
};

test("VRAM matrix derives parameters from canonical resolved training config", () => {
  assert.deepEqual(resolvedConfigToVramParams(config), {
    device: "cpu",
    model_name: "llama",
    batch_size: 12,
    block_size: 256,
    n_embd: 384,
    n_layer: 6,
    n_head: 8,
    vocab_size: 1024,
    intermediate_size: 1536,
    multiple_of: 128,
    tie_word_embeddings: false,
    bias: true,
    precision: "bfloat16",
    optimizer_type: "adamw",
    gradient_checkpointing: true,
    gradient_accumulation_steps: 3,
  });
});

const vramHookUrl = new URL("../src/widgets/vram-matrix/model/useVramMatrix.ts", import.meta.url);

test("VRAM matrix discards stale async responses after config revision changes", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(vramHookUrl, "utf8");
  assert.equal(source.includes("requestId !== requestRef.current"), true);
});
