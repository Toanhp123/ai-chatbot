import assert from "node:assert/strict";
import test from "node:test";

import { loadCheckpointThenCommit } from "../src/entities/checkpoint/model/checkpointActions.ts";

test("checkpoint selection commits only after backend load succeeds", async () => {
  const commits: string[] = [];
  let resolveLoad: ((value: { current_checkpoint: string }) => void) | undefined;
  const load = () => new Promise<{ current_checkpoint: string }>((resolve) => {
    resolveLoad = resolve;
  });

  const pending = loadCheckpointThenCommit(load, "checkpoints/new.pt", (path) => commits.push(path));
  assert.deepEqual(commits, []);
  resolveLoad?.({ current_checkpoint: "checkpoints/new.pt" });
  await pending;
  assert.deepEqual(commits, ["checkpoints/new.pt"]);
});

test("checkpoint selection never commits when backend load fails", async () => {
  const commits: string[] = [];
  await assert.rejects(
    loadCheckpointThenCommit(
      async () => { throw new Error("corrupt checkpoint"); },
      "checkpoints/bad.pt",
      (path) => commits.push(path),
    ),
    /corrupt checkpoint/,
  );
  assert.deepEqual(commits, []);
});

const playgroundHookUrl = new URL("../src/pages/playground/model/usePlayground.ts", import.meta.url);

test("Playground checkpoint load commits the authoritative backend path", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(playgroundHookUrl, "utf8");
  assert.equal(source.includes("loadCheckpointThenCommit"), true);
  assert.equal(source.includes("onCheckpointLoaded?.(selectedCheckpoint)"), false);
});

test("Playground does not override backend before inference state is authoritative", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(playgroundHookUrl, "utf8");
  assert.equal(
    source.includes("backendAuthoritative ? selectedGenerator : undefined"),
    true,
  );
  assert.equal(source.includes("setSelectedGenerator(result.current_backend)"), true);
});

const checkpointHubHookUrl = new URL("../src/widgets/checkpoint-hub/model/useCheckpointHub.ts", import.meta.url);
const trainingPageUrl = new URL("../src/pages/training/TrainingPage.tsx", import.meta.url);

test("checkpoint surfaces refresh when canonical config revision changes", async () => {
  const { readFile } = await import("node:fs/promises");
  const [playgroundSource, hubSource, trainingSource] = await Promise.all([
    readFile(playgroundHookUrl, "utf8"),
    readFile(checkpointHubHookUrl, "utf8"),
    readFile(trainingPageUrl, "utf8"),
  ]);
  assert.equal(playgroundSource.includes("checkpointListRequestRef"), true);
  assert.equal(hubSource.includes("configRevision?: number"), true);
  assert.equal(hubSource.includes("requestId !== requestRef.current"), true);
  assert.equal(trainingSource.includes("configRevision={configRevision}"), true);
});
