import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  extractTrackFromLabels,
  extractWorkKindFromLabels,
  findLinkedIssueNumbers,
  labelsForIssueBody,
  validateChangedFilesForTrack,
} from "./prompthon-activity-policy.mjs";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const issueTemplateDir = path.join(repoRoot, ".github", "ISSUE_TEMPLATE");
const issueTemplateFiles = [
  "bug-report.yml",
  "content-proposal.yml",
  "meta-process.yml",
  "practitioner-skill-package.yml",
  "source-project-proposal.yml",
];

test("extracts track and work kind labels", () => {
  const labels = [
    { name: "track: builder" },
    { name: "kind: feature" },
    { name: "status: pending-review" },
  ];
  assert.equal(extractTrackFromLabels(labels), "builder");
  assert.equal(extractWorkKindFromLabels(labels), "feature");
});

test("maps issue-form fields to activity labels", () => {
  const body = [
    "### Repository track",
    "",
    "Explorer",
    "",
    "### Work kind",
    "",
    "Radar note",
    "",
    "### Proposed content change",
    "",
    "Add a radar note.",
  ].join("\n");

  assert.deepEqual(labelsForIssueBody(body), [
    "status: pending-review",
    "track: explorer",
    "kind: radar-note",
  ]);
});

test("keeps legacy Contribution track issue bodies labelable", () => {
  const body = [
    "### Contribution track",
    "",
    "Builder",
    "",
    "### Work kind",
    "",
    "Feature",
  ].join("\n");

  assert.deepEqual(labelsForIssueBody(body), [
    "status: pending-review",
    "track: builder",
    "kind: feature",
  ]);
});

test("issue templates include visible Skill Compass score fields", () => {
  for (const fileName of issueTemplateFiles) {
    const source = fs.readFileSync(path.join(issueTemplateDir, fileName), "utf8");
    assert.match(source, /label: Repository track/, fileName);
    assert.match(source, /## Skill Compass score proposal/, fileName);
    assert.match(source, /- type: dropdown\n    id: vision_score/, fileName);
    assert.match(source, /label: Vision score/, fileName);
    assert.match(source, /- type: dropdown\n    id: harness_score/, fileName);
    assert.match(source, /label: Harness score/, fileName);
    assert.match(source, /- type: dropdown\n    id: craft_score/, fileName);
    assert.match(source, /label: Craft score/, fileName);
    assert.match(source, /- "0"\n        - "5"/, fileName);
    assert.match(source, /- "95"\n        - "100"/, fileName);
  }
});

test("finds linked issue numbers from closing keywords", () => {
  assert.deepEqual(
    findLinkedIssueNumbers("Closes #12\n\nFixes #13 and resolves #12."),
    [12, 13],
  );
});

test("validates explorer path policy", () => {
  assert.deepEqual(
    validateChangedFilesForTrack("explorer", [
      "foundations/the-agent-system.mdx",
      "scripts/check_filename_casing.py",
    ]),
    {
      allowedPaths: [
        "foundations/",
        "patterns/",
        "ecosystem/",
        "case-studies/",
        "radar/",
        "reading-paths/",
        "contributor-kit/reference-notes/",
        "publications/",
        "zh-Hans/",
      ],
      invalidFiles: ["scripts/check_filename_casing.py"],
      valid: false,
    },
  );
});

test("validates practitioner and builder path policy", () => {
  assert.equal(
    validateChangedFilesForTrack("practitioner", [
      "skills/daily-news-watcher/SKILL.md",
      "workshops/index.mdx",
    ]).valid,
    true,
  );
  assert.equal(
    validateChangedFilesForTrack("builder", [
      ".github/workflows/prompthon-track-guard.yml",
      "patterns/examples/deep-research-agent-starter/README.md",
      "systems/context-engineering.mdx",
    ]).valid,
    true,
  );
});

test("accepts a bilingual course specialization with its navigation and setup guides", () => {
  const validation = validateChangedFilesForTrack("practitioner", [
    "docs.json",
    "reading-paths/environment-setup.mdx",
    "reading-paths/sample-projects.mdx",
    "skills/course-support/README.md",
    "skills/index.mdx",
    "skills/professional-ai-agent-course.mdx",
    "specializations/ai-native-internship.mdx",
    "zh-Hans/reading-paths/environment-setup.mdx",
    "zh-Hans/reading-paths/sample-projects.mdx",
    "zh-Hans/skills/index.mdx",
    "zh-Hans/skills/professional-ai-agent-course.mdx",
    "zh-Hans/specializations/ai-native-internship.mdx",
  ]);
  assert.equal(validation.valid, true);
  assert.deepEqual(validation.invalidFiles, []);
});

test("course support paths do not allow unrelated content, CI, or lookalike filenames", () => {
  const invalidFiles = [
    ".github/workflows/prompthon-track-guard.yml",
    "scripts/check_filename_casing.py",
    "foundations/the-agent-system.mdx",
    "zh-Hans/foundations/the-agent-system.mdx",
    "reading-paths/advanced-agents.mdx",
    "docs.json.backup",
    "reading-paths/environment-setup.mdx.bak",
    "zh-Hans/reading-paths/sample-projects.mdx/other.md",
    "specializations-private/notes.md",
  ];
  const validation = validateChangedFilesForTrack("practitioner", [
    "skills/course-support/README.md",
    ...invalidFiles,
  ]);
  assert.equal(validation.valid, false);
  assert.deepEqual(validation.invalidFiles, invalidFiles);
});
