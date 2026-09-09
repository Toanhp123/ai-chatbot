import assert from "node:assert/strict";
import test from "node:test";

import {
  applyResumeToTrainingForm,
  applyTrainingScenarioOverrides,
  applyTrainingScenarioUpdate,
  buildTrainingOverrides,
  resolvedConfigToTrainingForm,
  shouldApplyTrainingScenario,
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
    config_path: "",
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


test("VRAM scenario overrides become visible dirty training fields without touching unrelated values", () => {
  const base = resolvedConfigToTrainingForm(resolved, "checkpoints/resume.pt");
  const result = applyTrainingScenarioOverrides(base, {
    batch_size: 32,
    precision: "float16",
    gradient_accumulation_steps: 4,
    gradient_checkpointing: false,
    optimizer_type: "adamw",
  });

  assert.equal(result.form.batch_size, 32);
  assert.equal(result.form.precision, "float16");
  assert.equal(result.form.gradient_accumulation_steps, 4);
  assert.equal(result.form.gradient_checkpointing, false);
  assert.equal(result.form.optimizer_type, "adamw");
  assert.equal(result.form.resume_checkpoint, "checkpoints/resume.pt");
  assert.deepEqual(new Set(result.overrideFields), new Set([
    "batch_size",
    "precision",
    "gradient_accumulation_steps",
    "gradient_checkpointing",
    "optimizer_type",
  ]));
});

const trainingDashboardHookUrl = new URL(
  "../src/pages/training/model/useTrainingDashboard.ts",
  import.meta.url,
);

test("VRAM scenario feasibility uses the same overrides that Training will submit", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(trainingDashboardHookUrl, "utf8");
  assert.equal(
    source.includes("checkFeasibilityRaw(effective.form, effectiveOverrideFields)"),
    true,
  );
  assert.equal(source.includes("checkFeasibilityRaw(applied.form, nextFields)"), true);
});


test("VRAM scenario revision is consumed once and not re-applied after canonical reload", () => {
  assert.equal(shouldApplyTrainingScenario({ revision: 4 }, 3), true);
  assert.equal(shouldApplyTrainingScenario({ revision: 4 }, 4), false);
  assert.equal(shouldApplyTrainingScenario({ revision: 4 }, 5), false);
  assert.equal(shouldApplyTrainingScenario(null, 3), false);
});


test("VRAM scenario is consumed even when it initially changes no fields", () => {
  const base = resolvedConfigToTrainingForm(resolved, "");
  const scenario = { revision: 9, overrides: { batch_size: base.batch_size } };
  const first = applyTrainingScenarioUpdate(base, scenario, -1);
  assert.equal(first.appliedRevision, 9);
  assert.deepEqual(first.overrideFields, []);

  const reloaded = { ...base, batch_size: base.batch_size + 5 };
  const second = applyTrainingScenarioUpdate(reloaded, scenario, first.appliedRevision);
  assert.equal(second.form.batch_size, reloaded.batch_size);
  assert.deepEqual(second.overrideFields, []);
  assert.equal(second.appliedRevision, 9);
});

test("model inspector hydrates canonical model on config revisions before user overrides", async () => {
	const { readFile } = await import("node:fs/promises");
	const hook = await readFile(new URL("../src/widgets/model-inspector/model/useModelInspector.ts", import.meta.url), "utf8");
	const widget = await readFile(new URL("../src/widgets/model-inspector/ModelInspectorWidget.tsx", import.meta.url), "utf8");
	const page = await readFile(new URL("../src/pages/diagnostics/DiagnosticsPage.tsx", import.meta.url), "utf8");
	const api = await readFile(new URL("../src/entities/model/api/modelApi.ts", import.meta.url), "utf8");

	assert.equal(hook.includes("configRevision"), true);
	assert.equal(hook.includes("inspectModel()"), true);
	assert.equal(widget.includes("configRevision?: number"), true);
	assert.equal(page.includes("<ModelInspectorWidget configRevision={configRevision}"), true);
	assert.equal(api.includes("modelName?: string"), true);
});

test("training UI has no fabricated canonical form before hydration", async () => {
  const { readFile } = await import("node:fs/promises");
  const hook = await readFile(trainingDashboardHookUrl, "utf8");
  const widget = await readFile(
    new URL("../src/widgets/training-config-form/ui/TrainingConfigFormWidget.tsx", import.meta.url),
    "utf8",
  );

  assert.equal(hook.includes("FALLBACK_FORM"), false);
  assert.equal(hook.includes("useState<TrainingConfigForm | null>(null)"), true);
  assert.equal(widget.includes("|| 0.0003"), false);
  assert.equal(widget.includes("|| 3000"), false);
});
