/* No auto-execution. Load in the authorized signed-in Host browser only after review.
 * This adapter REQUIRES the not-yet-provisioned demo capability/receipt contract.
 * It never exports cookies, uses bridge tokens or talks directly to the app's signed endpoint.
 */
(function (root) {
  "use strict";
  const fail = code => { const error = new Error(code); error.code = code; throw error; };
  const readNonce = () => {
    if (typeof root.crypto?.randomUUID === "function") return root.crypto.randomUUID();
    if (typeof root.crypto?.getRandomValues !== "function") fail("SECURE_RANDOM_REQUIRED");
    return Array.from(root.crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, "0")).join("");
  };
  const canonical = value => JSON.stringify(value, (_, v) => v && !Array.isArray(v) && typeof v === "object" ? Object.fromEntries(Object.keys(v).sort().map(k => [k, v[k]])) : v);
  async function sha(value) {
    const bytes = await root.crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical(value)));
    return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, "0")).join("");
  }
  async function execute(plan, approval, environment = {}) {
    const origin = environment.origin ?? root.location?.origin;
    const request = environment.fetch ?? root.fetch.bind(root);
    const clock = environment.now ?? Date.now;
    if (!plan || plan.mode !== "classroom_demo_only" || !plan.origin || plan.origin !== origin || !origin.startsWith("https://")) fail("ORIGIN_MISMATCH");
    const core = { ...plan }; delete core.plan_sha256; delete core.prepared_run_id;
    if (await sha(core) !== plan.plan_sha256) fail("PLAN_CHANGED");
    const action = approval?.action;
    if (!["draft", "schedule", "publish"].includes(action) || approval.planSha256 !== plan.plan_sha256 || approval.confirm !== action.toUpperCase()) fail("APPROVAL_REQUIRED");
    const segment = value => {
      if (typeof value !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$/.test(value)) fail("INVALID_SCOPE");
      return encodeURIComponent(value);
    };
    const prefix = `/api/organizations/${segment(plan.organization_id)}/course/workspaces/${segment(plan.workspace_id)}`;
    const receipts = [], savedPosts = [];
    let campaignId = null;
    async function json(path, method = "GET", body) {
      let response;
      try {
        response = await request(origin + path, { method, credentials: "include", redirect: "error", headers: { "Content-Type": "application/json" }, ...(body ? { body: JSON.stringify(body) } : {}) });
      } catch (_) { fail("REQUEST_UNCONFIRMED"); }
      if (!response.ok) fail(response.status === 401 ? "SIGN_IN_REQUIRED" : "BACKEND_DEPENDENCY_UNAVAILABLE");
      const text = await response.text();
      if (text.length > 512000) fail("RESPONSE_TOO_LARGE");
      try { return JSON.parse(text); } catch (_) { fail("INVALID_RESPONSE"); }
    }
    // No Social mutation is possible before the server attests actual isolation and worker policy.
    const context = await json(prefix + `/social-context?preparedRunId=${segment(plan.prepared_run_id)}&planSha256=${plan.plan_sha256}`);
    if (context.organization_id !== plan.organization_id || context.workspace_id !== plan.workspace_id || context.environment !== "demo" || context.delivery_mode !== "simulation" || context.isolated_demo !== true || context.application_id !== "prompthon.social-media-manager" || !Array.isArray(context.capabilities) || !context.capabilities.includes("social:" + action) || !Array.isArray(context.channels) || !Number.isFinite(Date.parse(context.expires_at)) || Date.parse(context.expires_at) <= clock()) fail("DEMO_CAPABILITY_REQUIRED");
    const workspace = segment(context.host_workspace_id);
    const currentStrategy = await json(prefix + "/records/content_strategies/" + segment(plan.strategy_id));
    if (currentStrategy.organization_id !== plan.organization_id || currentStrategy.workspace_id !== plan.workspace_id || currentStrategy.revision !== plan.strategy_revision) fail("STALE_STRATEGY");
    async function operation(method, path, body, slot) {
      const operationId = method === "GET" ? "social.http.read" : "social.http.write";
      const key = `${plan.plan_sha256}:${slot}` + (method === "GET" ? ":" + readNonce() : "");
      const result = await json(`/api/agent-applications/workspaces/${workspace}/operations`, "POST", {
        operationId, organizationId: plan.organization_id, idempotencyKey: key,
        input: { organizationId: plan.organization_id, path, method, body: body ?? null }
      });
      if (!result.success || result.receipt?.outcome !== "completed" || result.receipt.operationId !== operationId || result.receipt.idempotencyKey !== key || !(result.data?.status >= 200 && result.data.status < 300) || result.data.body?.success !== true) fail("OPERATION_UNCONFIRMED");
      receipts.push(result.receipt.receiptId);
      return result.data.body.data;
    }
    const channels = await operation("GET", "channels", null, "channels-read");
    if (!Array.isArray(channels?.channels)) fail("INVALID_CHANNEL_READBACK");
    const allowed = new Map(context.channels.map(c => [c.id, c]));
    // Canonical targetChannels contains PROVIDER IDs, not connection UUIDs. Unknown IDs can
    // fall back to all channels, so refuse any connected channel outside the attested demo set.
    if (channels.channels.some(c => c.connectionStatus === "connected" && (!allowed.has(c.id) || allowed.get(c.id).provider !== c.provider))) fail("PRODUCTION_CHANNEL_PRESENT");
    for (const post of plan.posts) {
      if (!post.providers?.length || post.providers.some(p => !["linkedin", "facebook"].includes(p) || !context.channels.some(c => c.provider === p && c.delivery_mode === "simulation" && channels.channels.some(live => live.id === c.id && live.provider === p && live.connectionStatus === "connected")))) fail("DEMO_CHANNEL_REQUIRED");
    }
    const metadata = { course: { strategyId: plan.strategy_id, strategyRevision: plan.strategy_revision, workspaceId: plan.workspace_id, planSha256: plan.plan_sha256, preparedRunId: plan.prepared_run_id, simulationOnly: true } };
    try {
      const campaign = await operation("POST", "campaigns", { ...plan.campaign, status: "pending", metadata }, "create-campaign");
      campaignId = segment(campaign.id);
      const campaignList = await operation("GET", "campaigns", null, "campaign-readback");
      if (!campaignList?.items?.some(c => c.id === campaign.id && c.topic === plan.campaign.topic && c.brief === plan.campaign.brief && c.metadata?.course?.strategyId === plan.strategy_id)) fail("CAMPAIGN_READBACK_MISMATCH");
      for (const post of plan.posts) {
        const settings = { ...post.settings, targetChannels: post.providers, approvalRequired: true };
        const draft = await operation("POST", "posts", { title: post.title, rawIdea: post.copy, campaignId: campaign.id, settings, metadata: { ...metadata, postState: "draft" } }, "create-" + post.key);
        const id = segment(draft.id);
        await operation("PATCH", "posts/" + id, { title: post.title, rawIdea: post.copy, campaignId: campaign.id, postState: "draft", metadata: { ...metadata, postState: "draft", settings }, variantOverrides: post.variantOverrides }, "content-" + post.key);
        const readback = await operation("GET", "posts/" + id, null, "readback-" + post.key);
        if (readback.id !== draft.id || readback.campaignId !== campaign.id || readback.rawIdea !== post.copy || !["draft", "active"].includes(readback.postState)) fail("POST_READBACK_MISMATCH");
        if (action === "draft" && readback.postState !== "draft") fail("POST_ALREADY_ACTIVE");
        savedPosts.push({ id: draft.id, status: readback.status ?? "draft", key: post.key });
      }
      if (action !== "draft") {
        for (const saved of savedPosts) {
          const post = plan.posts.find(p => p.key === saved.key);
          const result = await operation("POST", `posts/${segment(saved.id)}/${action}`, { publishAt: post.publishAt, postState: "active", settings: { ...post.settings, targetChannels: post.providers, approvalRequired: true } }, action + "-" + saved.key);
          if (result.rejected?.length) fail("TARGET_REJECTED");
          const after = await operation("GET", "posts/" + segment(saved.id), null, action + "-readback-" + saved.key);
          if (after.id !== saved.id || after.campaignId !== campaign.id) fail("POST_READBACK_MISMATCH");
          if (action === "schedule" && !post.providers.every(provider => after.schedules?.some(s => s.provider === provider && s.status === "scheduled" && Date.parse(s.scheduledAt) === Date.parse(post.publishAt)))) fail("SCHEDULE_READBACK_MISMATCH");
          if (action === "publish" && !post.providers.every(provider => after.deliveries?.some(d => d.provider === provider && d.status === "simulated" && !d.postUrl))) fail("SIMULATION_READBACK_REQUIRED");
          if (after.deliveries?.some(d => d.postUrl || ["published", "sent"].includes(d.status))) fail("UNEXPECTED_EXTERNAL_DELIVERY");
          saved.status = action === "schedule" ? "demo_scheduled" : "demo_simulated";
        }
      }
      // The server reconciles canonical Host receipts into skill_runs; no parallel social tables.
      const recorded = await json(prefix + "/social/record-receipts", "POST", { prepared_run_id: plan.prepared_run_id, plan_sha256: plan.plan_sha256, action, receipt_ids: receipts });
      if (!recorded.run_id) fail("COURSE_RECORD_UNCONFIRMED");
      const run = await json(prefix + "/records/skill_runs/" + segment(recorded.run_id));
      if (run.organization_id !== plan.organization_id || run.workspace_id !== plan.workspace_id || run.data?.status !== "succeeded" || run.data?.metadata?.plan_sha256 !== plan.plan_sha256) fail("COURSE_RECORD_UNCONFIRMED");
      return { status: action === "draft" ? "canonical_drafts_saved" : action === "schedule" ? "demo_scheduled" : "demo_simulated", campaign_id: campaignId, posts: savedPosts, run_id: recorded.run_id, actual_external_delivery: false };
    } catch (error) {
      return { status: "partial_or_unknown", error: error.code ?? "OPERATION_UNCONFIRMED", campaign_id: campaignId, posts: savedPosts, receipt_ids: receipts, actual_external_delivery: null, next: "Recover canonical objects/receipts before any retry. No automatic resubmission or deletion." };
    }
  }
  const api = { execute, canonical, sha };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.PrompthonCourseSocial = api;
})(globalThis);
