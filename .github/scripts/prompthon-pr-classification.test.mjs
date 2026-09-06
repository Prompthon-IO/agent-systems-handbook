import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { classificationChoices, resolveClassification } from "./prompthon-pr-classification.mjs";
import { TRACKS, WORK_KINDS, findLinkedIssueNumbers } from "./prompthon-activity-policy.mjs";
const body = "## Repository track\n- [x] `practitioner` — Skills\n## Work kind\n- [x] `skill-package`";
const labels = ["track: practitioner", "kind: skill-package"];

test("explicit bilingual choices map deterministically", () => {
  assert.deepEqual(resolveClassification({body}), {track:"practitioner",kind:"skill-package",labels});
  assert.deepEqual(resolveClassification({body:body.replace(/\n/g,"\r\n")}).labels,labels);
});
test("Issue inheritance and existing PR labels need no repeated selection", () => {
  assert.deepEqual(resolveClassification({issues:[{number:3,labels}]}).labels,labels);
  assert.deepEqual(resolveClassification({labels}).labels,labels);
  assert.deepEqual(resolveClassification({body,labels,issues:[{number:3,labels}]}).labels,labels);
});
test("unchecked template is not an implicit classification", () => {
  const template=fs.readFileSync(new URL("../PULL_REQUEST_TEMPLATE.md",import.meta.url),"utf8");
  assert.throws(()=>resolveClassification({body:template}), /Missing track/);
  assert.deepEqual(findLinkedIssueNumbers(template), []);
  for(const [heading,values] of [["Repository track",TRACKS],["Work kind",WORK_KINDS]]) {
    for(const value of values) {
      assert.deepEqual(classificationChoices(template.replace(`- [ ] \`${value}\``,`- [x] \`${value}\``),heading),[value]);
    }
  }
});
test("prose, examples and hidden comments cannot select a classification", () => {
  assert.throws(()=>resolveClassification({body:`Intended labels: track: practitioner, kind: skill-package\n<!--\n${body}\n-->\n\`\`\`md\n${body}\n\`\`\``}),/Missing track/);
});
test("missing, unknown and multiple choices have actionable failures", () => {
  assert.throws(()=>resolveClassification({body:body.split("## Work kind")[0]}),/Missing kind/);
  assert.throws(()=>resolveClassification({body:body.replace("practitioner","admin")}),/unknown track/);
  assert.throws(()=>resolveClassification({body:body.replace("## Work kind","- [x] `builder`\n## Work kind")}),/exactly one track/);
  assert.throws(()=>resolveClassification({body:body.replace("`practitioner`","practitioner")}),/backtick/);
  assert.throws(()=>resolveClassification({body:body+"\n## Work kind\n- [x] `docs`"}),/only one/);
});
test("conflicting PR, Issue and body values are rejected rather than overridden", () => {
  assert.throws(()=>resolveClassification({body,labels:["track: builder"]}),/track conflict/);
  assert.throws(()=>resolveClassification({body,issues:[{number:3,labels:["kind: docs"]}]}),/kind conflict/);
  assert.throws(()=>resolveClassification({issues:[{number:3,labels},{number:4,labels:["track: builder"]}]}),/track conflict/);
  assert.throws(()=>resolveClassification({body,labels:[...labels,"track: builder"]}),/exactly one track/);
});
