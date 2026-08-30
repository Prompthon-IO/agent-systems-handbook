// Synthetic contract harness only. Every fetch is intercepted; no network or social send.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const nodeCrypto = require("node:crypto");
if (!globalThis.crypto) globalThis.crypto = {
  subtle: nodeCrypto.webcrypto.subtle,
  getRandomValues: nodeCrypto.webcrypto.getRandomValues.bind(nodeCrypto.webcrypto),
  randomUUID: nodeCrypto.randomUUID
};
const adapter = require("../scripts/course_browser.js");
const plan = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));

class FakeHost {
  constructor(options = {}) {
    this.options = options;
    this.calls = [];
    this.campaigns = [];
    this.posts = new Map();
    this.replays = new Map();
    this.context = { organization_id: plan.organization_id, workspace_id: plan.workspace_id, environment: "demo", delivery_mode: "simulation", isolated_demo: true, application_id: "prompthon.social-media-manager", capabilities: ["social:draft", "social:schedule", "social:publish"], host_workspace_id: "00000000-0000-4000-8000-000000000002", expires_at: "2099-01-01T00:00:00Z", channels: [
      { id: "channel-linkedin", provider: "linkedin", delivery_mode: "simulation" },
      { id: "channel-facebook", provider: "facebook", delivery_mode: "simulation" }
    ], ...options.context };
    this.fetch = this.fetch.bind(this);
  }
  response(value, status = 200) { return new Response(JSON.stringify(value), { status }); }
  async fetch(url, init) {
    assert.ok(url.startsWith(plan.origin + "/api/"));
    assert.equal(init.credentials, "include");
    assert.equal(init.redirect, "error");
    assert.equal(init.headers.Authorization, undefined);
    assert.equal(init.headers["x-prompthon-local-bridge-token"], undefined);
    const path = new URL(url).pathname;
    const input = init.body ? JSON.parse(init.body) : null;
    this.calls.push({ path, input });
    if (path.endsWith("/social-context")) return this.response(this.context, this.options.missing ? 404 : 200);
    if (path.includes("/records/content_strategies/")) return this.response({ organization_id: plan.organization_id, workspace_id: plan.workspace_id, revision: plan.strategy_revision + (this.options.stale ? 1 : 0) });
    if (path.endsWith("/social/record-receipts")) {
      assert.equal(input.plan_sha256, plan.plan_sha256);
      assert.ok(input.receipt_ids.length);
      return this.response({ run_id: "synthetic-social-run" });
    }
    if (path.includes("/records/skill_runs/")) return this.response({ organization_id: plan.organization_id, workspace_id: plan.workspace_id, data: { status: "succeeded", metadata: { plan_sha256: plan.plan_sha256 } } });
    assert.equal(path, "/api/agent-applications/workspaces/" + this.context.host_workspace_id + "/operations");
    assert.equal(input.organizationId, plan.organization_id);
    assert.equal(input.input.organizationId, plan.organization_id);
    const op = input.input;
    assert.equal(input.operationId, op.method === "GET" ? "social.http.read" : "social.http.write");
    if (op.method !== "GET" && this.replays.has(input.idempotencyKey)) return this.response(clone(this.replays.get(input.idempotencyKey)));
    let data;
    if (op.path === "channels") {
      data = { channels: this.context.channels.map(c => ({ id: c.id, provider: c.provider, connectionStatus: "connected" })) };
      if (this.options.realChannel) data.channels.push({ id: "real-channel", provider: "linkedin", connectionStatus: "connected" });
    } else if (op.path === "campaigns" && op.method === "POST") {
      data = { id: "campaign-1", ...op.body };
      this.campaigns.push(clone(data));
    } else if (op.path === "campaigns") data = { items: this.campaigns };
    else if (op.path === "posts") {
      data = { id: "post-" + (this.posts.size + 1), ...op.body, postState: "draft", status: "draft", schedules: [], deliveries: [] };
      this.posts.set(data.id, data);
    } else {
      const [, id, action] = op.path.split("/");
      const post = this.posts.get(id);
      assert.ok(post);
      if (op.method === "PATCH") {
        Object.assign(post, op.body);
        data = post;
      } else if (op.method === "GET") {
        data = clone(post);
        if (this.options.wrongCopy) data.rawIdea = "wrong canonical content";
      } else if (action === "schedule") {
        post.postState = "active";
        post.status = "scheduled";
        const providers = this.options.partialSchedule ? op.body.settings.targetChannels.slice(0, 1) : op.body.settings.targetChannels;
        post.schedules = providers.map(provider => ({ provider, status: "scheduled", scheduledAt: new Date(op.body.publishAt).toISOString() }));
        data = { schedules: post.schedules, rejected: [], post };
      } else if (action === "publish") {
        post.deliveries = op.body.settings.targetChannels.map(provider => ({ provider, status: "simulated", postUrl: null }));
        data = { deliveries: post.deliveries, rejected: [], post };
      } else assert.fail("Unexpected operation");
    }
    const response = { success: true, receipt: { receiptId: "receipt-" + this.calls.length, operationId: input.operationId, idempotencyKey: input.idempotencyKey, outcome: "completed" }, data: { status: 200, body: { success: true, data } } };
    if (op.method !== "GET") this.replays.set(input.idempotencyKey, clone(response));
    return this.response(response);
  }
  writes() { return this.calls.filter(c => c.input?.operationId === "social.http.write"); }
  run(action = "draft", override) { return adapter.execute(plan, { action, planSha256: plan.plan_sha256, confirm: action.toUpperCase(), ...override }, { origin: plan.origin, fetch: this.fetch }); }
}

(async () => {
  const checks = [];
  const host = new FakeHost();
  assert.equal((await host.run()).status, "canonical_drafts_saved");
  assert.equal(host.campaigns.length, 1);
  assert.equal(host.posts.size, plan.posts.length);
  assert.equal(host.writes().some(c => /schedule|publish/.test(c.input.input.path)), false);
  for (const post of host.posts.values()) assert.ok(post.metadata.course.strategyId);
  checks.push("canonical-draft-readback");
  assert.equal((await host.run("schedule")).status, "demo_scheduled");
  checks.push("approved-demo-schedule");
  assert.equal((await host.run("publish")).status, "demo_simulated");
  assert.equal(host.campaigns.length, 1, "Same plan does not create a new campaign when progressing from draft to schedule");
  assert.equal(host.posts.size, plan.posts.length);
  checks.push("simulated-publish-reuses-canonical-objects");
  for (const [options, code] of [
    [{ missing: true }, "BACKEND_DEPENDENCY_UNAVAILABLE"],
    [{ context: { environment: "production" } }, "DEMO_CAPABILITY_REQUIRED"],
    [{ context: { expires_at: "2000-01-01T00:00:00Z" } }, "DEMO_CAPABILITY_REQUIRED"],
    [{ realChannel: true }, "PRODUCTION_CHANNEL_PRESENT"],
    [{ stale: true }, "STALE_STRATEGY"]
  ]) {
    const blocked = new FakeHost(options);
    await assert.rejects(() => blocked.run(), e => e.code === code);
    assert.equal(blocked.writes().length, 0);
    checks.push(code);
  }
  const noApproval = new FakeHost();
  await assert.rejects(() => noApproval.run("schedule", { confirm: "DRAFT" }), e => e.code === "APPROVAL_REQUIRED");
  assert.equal(noApproval.calls.length, 0);
  checks.push("explicit-action-approval");
  const mismatch = new FakeHost({ wrongCopy: true });
  assert.equal((await mismatch.run("schedule")).status, "partial_or_unknown");
  assert.equal(mismatch.writes().some(c => c.input.input.path.endsWith("/schedule")), false);
  checks.push("canonical-copy-mismatch-stops-scheduling");
  const partial = new FakeHost({ partialSchedule: true });
  const partialResult = await partial.run("schedule");
  assert.equal(partialResult.error, "SCHEDULE_READBACK_MISMATCH");
  assert.equal(partialResult.actual_external_delivery, null);
  checks.push("every-provider-schedule-readback");
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, "crypto");
  try {
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: {
      subtle: nodeCrypto.webcrypto.subtle,
      getRandomValues: nodeCrypto.webcrypto.getRandomValues.bind(nodeCrypto.webcrypto)
    } });
    const compatible = new FakeHost();
    assert.equal((await compatible.run()).status, "canonical_drafts_saved");
    assert.equal((await compatible.run()).status, "canonical_drafts_saved");
    const readKeys = compatible.calls.filter(c => c.input?.operationId === "social.http.read").map(c => c.input.idempotencyKey);
    assert.equal(new Set(readKeys).size, readKeys.length, "Read keys stay fresh without randomUUID");
    checks.push("webcrypto-without-randomUUID");
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: { subtle: nodeCrypto.webcrypto.subtle } });
    const noRandom = new FakeHost();
    await assert.rejects(() => noRandom.run(), e => e.code === "SECURE_RANDOM_REQUIRED");
    assert.equal(noRandom.writes().length, 0);
    checks.push("missing-secure-random-refused");
  } finally {
    Object.defineProperty(globalThis, "crypto", descriptor);
  }
  console.log(JSON.stringify({ status: "passed", synthetic_only: true, real_network_requests: 0, cases: checks.length, checks }));
})().catch(error => { console.error(error); process.exitCode = 1; });
