import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/pages/explorer/ExplorerPage.tsx", import.meta.url);

test("Explorer UI never claims a hardcoded dataset path", async () => {
  const source = await readFile(pageUrl, "utf8");
  assert.equal(source.includes("data/input.txt"), false);
});

const explorerHookUrl = new URL("../src/pages/explorer/model/useExplorer.ts", import.meta.url);
const appUrl = new URL("../src/app/App.tsx", import.meta.url);

test("Explorer refreshes canonical dataset state after config save", async () => {
  const [pageSource, hookSource, appSource] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(explorerHookUrl, "utf8"),
    readFile(appUrl, "utf8"),
  ]);
  assert.equal(pageSource.includes("configRevision?: number"), true);
  assert.equal(pageSource.includes("useExplorer(configRevision)"), true);
  assert.equal(hookSource.includes("export function useExplorer(configRevision = 0)"), true);
  assert.equal(hookSource.includes("}, [configRevision]);"), true);
  assert.equal(appSource.includes("<ExplorerPage configRevision={configRevision} />"), true);
});
