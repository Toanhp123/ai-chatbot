import assert from "node:assert/strict";
import test from "node:test";

import {
  applyResumeToTrainingForm,
  buildTrainingOverrides,
  resolvedConfigToTrainingForm,
} from "../src/entities/training/model/configMapping.ts";

const resolved = {
  model: { name: "llama_nano" },
  training: {
    batch_size: 17,
    learning_rate: 0.00012,
    max_iters: 4321,
    precision: "bfloat16",
    optimizer_type: "8bit_adamw",
    gradient_accumulation_steps: 3,
    gradient_checkpointing: true,
  },
};

test("resolved config hydrates visible training form from canonical server values", () => {
  const form = resolvedConfigToTrainingForm(resolved, "checkpoints/resume.pt");

  assert.deepEqual(form, {
    config_path: "configs/truyen_kieu.yaml",
    model_name: "llama_nano",
    batch_size: 17,
    learning_rate: 0.00012,
    max_iters: 4321,
    precision: "bfloat16",
    optimizer_type: "8bit_adamw",
    gradient_accumulation_steps: 3,
    gradient_checkpointing: true,
    resume_checkpoint: "checkpoints/resume.pt",
  });
});

test("only explicitly dirty form fields become canonical dotted overrides", () => {
  const form = resolvedConfigToTrainingForm(resolved, "");
  const overrides = buildTrainingOverrides(form, ["batch_size", "optimizer_type"]);

  assert.deepEqual(overrides, {
    "training.batch_size": 17,
    "training.optimizer_type": "8bit_adamw",
  });
});

import { isLatestRequest, isNewerTrainingVersion } from "../src/entities/training/model/stateVersion.ts";

test("training version ordering rejects stale snapshots and accepts newer runs or sequences", () => {
  const current = { runId: 4, sequence: 10 };

  assert.equal(isNewerTrainingVersion({ runId: 3, sequence: 999 }, current), false);
  assert.equal(isNewerTrainingVersion({ runId: 4, sequence: 10 }, current), false);
  assert.equal(isNewerTrainingVersion({ runId: 4, sequence: 11 }, current), true);
  assert.equal(isNewerTrainingVersion({ runId: 5, sequence: 0 }, current), true);
});


test("reloading canonical config preserves resume and re-applies only required max-iter extension", () => {
  const base = resolvedConfigToTrainingForm(resolved, "");
  const result = applyResumeToTrainingForm(base, "checkpoints/step-5000.pt", 5000);

  assert.equal(result.form.resume_checkpoint, "checkpoints/step-5000.pt");
  assert.equal(result.form.max_iters, 6000);
  assert.deepEqual(result.overrideFields, ["max_iters"]);

  const alreadyLongEnough = applyResumeToTrainingForm(
    { ...base, max_iters: 7000 },
    "checkpoints/step-5000.pt",
    5000,
  );
  assert.equal(alreadyLongEnough.form.max_iters, 7000);
  assert.deepEqual(alreadyLongEnough.overrideFields, []);
});


test("only the latest async request may commit training UI state", () => {
  assert.equal(isLatestRequest(7, 8), false);
  assert.equal(isLatestRequest(8, 8), true);
});
