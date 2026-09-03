import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(new URL("./prompthon-track-guard.mjs", import.meta.url));

function runGuard(t, { labels = [], files = [], body = "", mockApi = false } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "track-guard-test-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const eventPath = path.join(dir, "event.json");
  const summaryPath = path.join(dir, "summary.md");
  fs.writeFileSync(eventPath, JSON.stringify({
    repository: { full_name: "example/handbook" },
    pull_request: { number: 1, labels, body },
    changed_files: files,
  }));
  const mockPath = path.join(dir, "mock-api.mjs");
  fs.writeFileSync(mockPath, `
    globalThis.fetch = async (url, options = {}) => {
      if (url.endsWith("/issues/123")) {
        return Response.json({ labels: [{ name: "track: practitioner" }] });
      }
      if (url.endsWith("/pulls/1/files?per_page=100&page=1")) {
        return Response.json([{ filename: "skills/course-support/README.md" }]);
      }
      if (url.endsWith("/issues/1/comments?per_page=100")) {
        return Response.json([]);
      }
      if (url.endsWith("/issues/1/comments") && options.method === "POST") {
        return Response.json({ message: "Resource not accessible by integration" }, { status: 403 });
      }
      throw new Error("Unexpected network request: " + url);
    };
  `);
  const result = spawnSync(process.execPath, [
    "--import", mockPath, scriptPath, ...(mockApi ? [] : ["--dry-run"]),
  ], {
    env: {
      ...process.env,
      GITHUB_TOKEN: "test-token-never-sent",
      GITHUB_EVENT_PATH: eventPath,
      GITHUB_STEP_SUMMARY: summaryPath,
    },
    encoding: "utf8",
    timeout: 10_000,
  });
  assert.ifError(result.error);
  return {
    ...result,
    summary: fs.existsSync(summaryPath) ? fs.readFileSync(summaryPath, "utf8") : "",
  };
}

test("an unlabeled direct PR fails with instructions in the log and summary", (t) => {
  const result = runGuard(t, { files: ["skills/course-support/README.md"] });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /could not determine a contribution track/);
  assert.match(result.summary, /track: practitioner/);
  assert.match(result.summary, /Closes #123/);
  assert.match(result.summary, /Linked issue: none/);
});

test("the PR label supports direct contributions without a linked issue", (t) => {
  const result = runGuard(t, {
    labels: [{ name: "track: practitioner" }],
    files: ["skills/course-support/examples/lesson-2-organizer-student-files/incoming/school-reading.md"],
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(JSON.parse(result.stdout).status, "passed");
});

test("a labeled PR can include bilingual specialization and navigation pages", (t) => {
  const result = runGuard(t, {
    labels: [{ name: "track: practitioner" }],
    files: ["docs.json", "specializations/ai-native-internship.mdx", "zh-Hans/skills/index.mdx"],
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(JSON.parse(result.stdout).track, "practitioner");
});

test("a practitioner label still rejects changes to the guard itself", (t) => {
  const result = runGuard(t, {
    labels: [{ name: "track: practitioner" }],
    files: ["skills/index.mdx", ".github/scripts/prompthon-track-guard.mjs"],
  });
  assert.equal(result.status, 1);
  assert.match(result.summary, /Invalid files:\n- `.github\/scripts\/prompthon-track-guard.mjs`/);
});

test("comment permission failures preserve the actionable validation error", (t) => {
  const result = runGuard(t, { mockApi: true });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /GitHub API 403/);
  assert.match(result.summary, /track: practitioner/);
  assert.ok(result.stderr.indexOf("could not determine") < result.stderr.indexOf("GitHub API 403"));
});

test("a linked issue track still takes precedence over the PR track", (t) => {
  const result = runGuard(t, {
    body: "Closes #123",
    labels: [{ name: "track: builder" }],
    mockApi: true,
  });
  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.equal(output.track, "practitioner");
  assert.equal(output.linkedIssueNumber, 123);
});
