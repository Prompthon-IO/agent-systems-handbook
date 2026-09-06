import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";
const scriptPath = fileURLToPath(new URL("./prompthon-track-guard.mjs", import.meta.url));
const selected = "## Repository track\n- [x] `practitioner`\n## Work kind\n- [x] `skill-package`";
const classification = ["track: practitioner", "kind: skill-package"];
function runGuard(t, { labels=[], files=["skills/course-support/README.md"], body="", live=false,
  issues={123:{labels:classification}}, denyComments=false, denyLabels=false, dropLabels=false,
  current=null, changeDuringRun=false, base="develop", head="feature", oldComment=false }={}) {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"track-guard-test-"));
  t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  const event={repository:{full_name:"example/handbook"},pull_request:{number:1,labels,body,state:"open",base:{ref:base},head:{ref:head,repo:{full_name:"example/handbook"}}},changed_files:files};
  const eventPath=path.join(dir,"event.json"),summaryPath=path.join(dir,"summary.md"),calls=path.join(dir,"calls.jsonl"),mock=path.join(dir,"mock.mjs");
  fs.writeFileSync(eventPath,JSON.stringify(event));
  fs.writeFileSync(mock, `import fs from "node:fs";
    const pr=${JSON.stringify(current || event.pull_request)};
    let labels=pr.labels;
    let reads=0;
    globalThis.fetch=async(url, options={})=>{
      fs.appendFileSync(${JSON.stringify(calls)},JSON.stringify({url,...options})+"\\n");
      if(url.endsWith("/pulls/1")) {
        reads++;
        return Response.json({...pr,labels,...(${changeDuringRun} && reads > 1 ? {body:"edited during validation"}: {})});
      }
      const issues=${JSON.stringify(issues)};
      const issue=url.match(/\\/issues\\/(\\d+)$/);
      if(issue && issues[issue[1]]) return Response.json(issues[issue[1]]);
      if(url.includes("/pulls/1/files?")) return Response.json(${JSON.stringify(files.map(filename=>({filename})))});
      if(url.endsWith("/issues/1/labels")) {
        if(options.method==="POST") {
          if(${denyLabels}) return Response.json({message:"denied"},{status:403});
          if(!${dropLabels}) labels=[...labels,...JSON.parse(options.body).labels];
        }
        return Response.json(labels);
      }
      if(url.includes("/comments?")) return Response.json(${JSON.stringify(oldComment?[{id:99,body:"<!-- prompthon-track-guard -->\nold failure"}]:[])});
      if(options.method==="POST" || options.method==="PATCH") {
        return ${denyComments}?Response.json({message:"denied"},{status:403}):Response.json({id:99});
      }
      throw new Error("Unexpected network request: "+url);
    };`);
  const result=spawnSync(process.execPath,["--import",mock,scriptPath,...(live?[]:["--dry-run"])],{
    env:{...process.env,GITHUB_TOKEN:"test-only",GITHUB_EVENT_PATH:eventPath,GITHUB_STEP_SUMMARY:summaryPath},encoding:"utf8",timeout:10000});
  assert.ifError(result.error);
  return {...result,summary:fs.existsSync(summaryPath)?fs.readFileSync(summaryPath,"utf8"):"",calls:fs.existsSync(calls)?fs.readFileSync(calls,"utf8").trim().split("\n").map(JSON.parse):[]};
}
test("missing metadata explains how contributors can edit their own PR",t=>{
  const r=runGuard(t);assert.equal(r.status,1);assert.match(r.summary,/Missing track/);assert.match(r.summary,/Closes #123/);assert.match(r.summary,/permission/);
});
test("direct PR choices add both labels and pass in the same run",t=>{
  const r=runGuard(t,{body:selected,live:true});assert.equal(r.status,0,r.stderr);
  const writes=r.calls.filter(c=>c.url.endsWith("/labels")&&c.method==="POST");
  assert.equal(writes.length,1);assert.deepEqual(JSON.parse(writes[0].body).labels,classification);
  assert.equal(JSON.parse(r.stdout).status,"passed");
});
test("existing labels and labeled Issues both support inheritance",t=>{
  for(const options of [{labels:classification},{body:"Closes #123"}]) {
    const r=runGuard(t,{...options,live:true});assert.equal(r.status,0,r.stderr);
  }
});
test("a selected practitioner track cannot change the guard or grant itself access",t=>{
  const r=runGuard(t,{body:selected,live:true,files:["skills/index.mdx",".github/scripts/prompthon-track-guard.mjs"]});
  assert.equal(r.status,1);assert.match(r.summary,/Invalid files/);
  assert.equal(r.calls.filter(c=>c.url.endsWith("/labels")&&c.method==="POST").length,0);
});
test("bilingual practitioner navigation paths remain allowed",t=>{
  const r=runGuard(t,{labels:classification,files:["docs.json","specializations/ai-native-internship.mdx","zh-Hans/skills/index.mdx"]});assert.equal(r.status,0,r.stderr);
});
test("Issue conflicts block instead of silently taking precedence",t=>{
  const r=runGuard(t,{body:"Closes #123",labels:["track: builder","kind: ci"],live:true});assert.equal(r.status,1);assert.match(r.summary,/track conflict/);
});
test("every linked Issue is checked and PR references cannot supply Issue labels",t=>{
  const r=runGuard(t,{body:"Closes #123, fixes #124",issues:{123:{labels:classification},124:{labels:["track: builder"]}}});assert.equal(r.status,1);assert.match(r.summary,/Issue #124/);
  const pr=runGuard(t,{body:"Closes #123",issues:{123:{labels:classification,pull_request:{}}}});assert.equal(pr.status,1);assert.match(pr.stderr,/is a PR/);
});
test("comment permission failure does not hide the validation failure",t=>{
  const r=runGuard(t,{live:true,denyComments:true});assert.equal(r.status,1);assert.match(r.stderr,/Missing track/);assert.match(r.stderr,/403/);
});
test("failed label writes and missing readback cannot report success",t=>{
  for(const options of [{denyLabels:true},{dropLabels:true}]) {
    const r=runGuard(t,{body:selected,live:true,...options});assert.equal(r.status,1);assert.doesNotMatch(r.stdout,/"passed"/);
  }
});
test("repeat runs do not rewrite labels and replace stale failure comments",t=>{
  const r=runGuard(t,{body:selected,labels:classification,live:true,oldComment:true});assert.equal(r.status,0,r.stderr);
  assert.equal(r.calls.filter(c=>c.url.endsWith("/labels")&&c.method==="POST").length,0);
  assert.ok(r.calls.some(c=>c.method==="PATCH"&&JSON.parse(c.body).body.includes("checks passed")));
});
test("live PR metadata replaces stale event payload after edits",t=>{
  const current={number:1,labels:[],body:selected,state:"open",base:{ref:"develop"},head:{ref:"feature"}};
  const r=runGuard(t,{live:true,current});assert.equal(r.status,0,r.stderr);
});
test("same-repository develop-to-main release remains exempt",t=>{
  const r=runGuard(t,{base:"main",head:"develop",live:true});assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/develop_to_main_release_pr/);
  assert.equal(r.calls.filter(c=>c.method).length,0);
});

test("a concurrent description edit prevents stale classification writes",t=>{
  const r=runGuard(t,{body:selected,live:true,changeDuringRun:true});
  assert.equal(r.status,1);assert.match(r.stderr,/PR changed during classification/);
  assert.equal(r.calls.filter(c=>c.url.endsWith("/labels")&&c.method==="POST").length,0);
});
