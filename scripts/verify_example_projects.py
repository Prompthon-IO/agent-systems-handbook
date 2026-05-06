#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str) -> ModuleType:
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def check_memory_starter() -> None:
    module = load_module(
        "memory_flow",
        "patterns/examples/agent-memory-retrieval-starter/src/memory_flow.py",
    )
    trace_module = load_module(
        "retrieval_trace",
        "patterns/examples/agent-memory-retrieval-starter/src/retrieval_trace.py",
    )
    policy_module = load_module(
        "artifact_policy",
        "patterns/examples/agent-memory-retrieval-starter/src/artifact_policy.py",
    )
    personal_context_module = load_module(
        "personal_context",
        "patterns/examples/agent-memory-retrieval-starter/src/personal_context.py",
    )
    state = module.AgentState()
    module.add_observation(state, "capture the latest user request")
    module.queue_retrieval(state, "previous agent memory decisions")
    module.promote_fact(state, "decision", "publish only durable artifacts")
    module.remember(
        state,
        "fact",
        "retrieval should remain explicit",
        "lab smoke test",
    )
    module.remember_personal_context(
        state,
        "preference",
        "user prefers concise summaries",
        "imported assistant memory",
    )
    imported_context = personal_context_module.normalize_imported_context(
        [
            (" Favorite Genre ", "  Science Fiction  "),
            (" TimeZone ", "  America/Toronto  "),
            ("nickname", "   "),
        ]
    )
    merged_context = personal_context_module.merge_personal_context(
        [],
        imported_context,
    )

    trace = trace_module.build_trace(
        "previous agent memory decisions",
        [
            trace_module.RetrievalCandidate(
                source_id="policy-note",
                snippet="Durable policy guidance",
                score=0.95,
            ),
            trace_module.RetrievalCandidate(
                source_id="chat-log",
                snippet="Recent working note",
                score=0.70,
            ),
            trace_module.RetrievalCandidate(
                source_id="scratchpad",
                snippet="Temporary note",
                score=0.20,
            ),
        ],
    )

    assert state.active_notes == ["capture the latest user request"]
    assert state.retrieval_queries == ["previous agent memory decisions"]
    assert state.artifacts["decision"] == "publish only durable artifacts"
    assert len(state.working_memory) == 1
    assert len(state.personal_context) == 1
    assert trace.selected_sources == ["policy-note", "chat-log"]
    assert trace.deferred_sources == ["scratchpad"]
    assert policy_module.should_promote("Final decision to publish the summary")
    assert (
        policy_module.artifact_key("Decision: Publish Notes")
        == "decision-publish-notes"
    )
    assert len(merged_context) == 2
    assert {item.kind for item in merged_context} == {
        "favorite_genre",
        "timezone",
    }
    assert {item.summary for item in merged_context} == {
        "Science Fiction",
        "America/Toronto",
    }
    assert all(item.source == "imported-summary" for item in merged_context)


def check_prompt_cache_starter() -> None:
    module = load_module(
        "prompt_cache_agent_starter",
        "patterns/examples/prompt-cache-agent-starter/src/prompt_cache_agent_starter.py",
    )
    layers = module.build_prompt_layers(
        tool_manifest="tool:get_weather",
        system_instructions="You are a bounded agent.",
        reference_context="Project policy v1",
        durable_memory_summary="User prefers concise answers.",
        current_task="Plan today's work.",
    )
    cold = module.RunObservation(
        label="cold",
        latency_ms=5200,
        usage=module.TokenUsage(input_tokens=10000, cache_write_tokens=7000),
        stable_prefix_hash=module.stable_prefix_hash(layers),
    )
    warm = module.RunObservation(
        label="warm",
        latency_ms=2600,
        usage=module.TokenUsage(input_tokens=10000, cache_read_tokens=7000),
        stable_prefix_hash=module.stable_prefix_hash(layers),
    )
    summary = module.summarize_usage(
        warm.usage,
        module.Pricing(
            base_input_usd_per_mtok=3.0,
            cache_write_usd_per_mtok=3.75,
            cache_hit_usd_per_mtok=0.30,
        ),
    )
    comparison = module.compare_runs(cold, warm)

    assert module.cache_boundary_index(layers) == 3
    assert [layer.name for layer in layers[3:]] == [
        "dynamic-memory",
        "turn-input",
    ]
    assert summary.cache_read_share == 0.7
    assert round(summary.estimated_input_cost_usd, 6) == 0.0111
    assert comparison.latency_delta_ms == -2600
    assert comparison.stable_prefix_changed is False


def check_weather_starter() -> None:
    module = load_module(
        "weather_server",
        "systems/examples/weather-mcp-server-starter/src/server.py",
    )
    manifest_module = load_module(
        "weather_tool_manifest",
        "systems/examples/weather-mcp-server-starter/src/tool_manifest.py",
    )
    access_module = load_module(
        "weather_access_policy",
        "systems/examples/weather-mcp-server-starter/src/access_policy.py",
    )
    response = module.get_forecast(module.ForecastRequest(city="Toronto", days=2))
    manifest = manifest_module.build_weather_manifest()
    access_module.authorize_forecast(
        access_module.CallerContext(
            actor_id="demo-agent",
            scopes=["weather:read"],
        ),
        "Toronto",
    )

    assert response.city == "Toronto"
    assert response.summary == "placeholder forecast"
    assert manifest.name == "get_forecast"
    assert manifest.input_schema["properties"]["days"]["maximum"] == 7
    assert "summary" in manifest.output_fields

    try:
        module.get_forecast(module.ForecastRequest(city=" ", days=0))
    except ValueError as exc:
        assert "city is required" in str(exc)
    else:
        raise AssertionError("invalid weather request should raise ValueError")

    try:
        access_module.authorize_forecast(
            access_module.CallerContext(
                actor_id="blocked-agent",
                scopes=[],
            ),
            "Toronto",
        )
    except PermissionError as exc:
        assert "weather:read" in str(exc)
    else:
        raise AssertionError("missing scope should raise PermissionError")


def check_langgraph_starter() -> None:
    module = load_module(
        "langgraph_starter",
        "ecosystem/examples/langgraph-starter/src/graph.py",
    )
    branching_module = load_module(
        "langgraph_branching",
        "ecosystem/examples/langgraph-starter/src/branching.py",
    )
    summary_module = load_module(
        "langgraph_run_summary",
        "ecosystem/examples/langgraph-starter/src/run_summary.py",
    )
    state = {
        "question": "How should routing work?",
        "plan": "",
        "route": "",
        "answer": "",
    }
    state = module.plan_node(state)
    state = module.route_node(state)
    state = module.synthesize_node(state)
    summary = summary_module.render_run_summary(
        state["question"],
        state["plan"],
        state["route"],
        state["answer"],
    )

    assert state["plan"]
    assert state["route"] == "tool"
    assert state["answer"] == "placeholder synthesis"
    assert branching_module.choose_route("lookup one source then answer") == "tool"
    assert branching_module.should_retry("Temporary timeout from tool call")
    assert "Route: tool" in summary


def check_messaging_transaction_starter() -> None:
    module = load_module(
        "messaging_transaction_flow",
        "ecosystem/examples/messaging-transaction-assistant-starter/src/transaction_flow.py",
    )
    handoff = module.run_flow(
        "Recharge my family phone with a standard data plan",
        max_price_inr=300,
    )

    assert handoff.status == "awaiting-user-confirmation"
    assert handoff.confirmation.recipient == "family"
    assert handoff.confirmation.requires_user_confirmation is True
    assert handoff.confirmation.amount_inr <= 300
    assert "instant-transfer-like" in handoff.payment_methods

    try:
        module.select_plan(module.capture_intent("recharge me"), max_price_inr=0)
    except ValueError as exc:
        assert "budget must be positive" in str(exc)
    else:
        raise AssertionError("non-positive budget should be rejected")

    try:
        module.select_plan(module.capture_intent("recharge me"), max_price_inr=100)
    except ValueError as exc:
        assert "no starter plan" in str(exc)
    else:
        raise AssertionError("too-small budget should reject all starter plans")


def check_research_starter() -> None:
    module = load_module(
        "research_loop",
        "case-studies/examples/deep-research-agent-starter/src/research_loop.py",
    )
    citation_module = load_module(
        "research_citation_formatter",
        "case-studies/examples/deep-research-agent-starter/src/citation_formatter.py",
    )
    review_module = load_module(
        "research_review",
        "case-studies/examples/deep-research-agent-starter/src/research_review.py",
    )
    task = module.ResearchTask(question="What is a deep research agent?")
    module.seed_plan(task)
    module.add_evidence(
        task,
        "Example source",
        "https://example.com",
        "Shows a small research loop",
    )
    report = module.draft_report(task)
    references = citation_module.render_reference_list(
        [("Example source", "https://example.com")]
    )
    gaps = review_module.identify_evidence_gaps(task.todo, len(task.evidence))

    assert len(task.todo) == 3
    assert len(task.evidence) == 1
    assert "What is a deep research agent?" in report
    assert "https://example.com" in report
    assert "[1] Example source - https://example.com" in references
    assert "add at least one more source before publishing" in gaps
    assert not review_module.is_ready_to_publish(len(task.evidence), gaps)


def check_customer_support_starter() -> None:
    src_dir = (
        REPO_ROOT
        / "case-studies/examples/customer-support-email-agent-starter/src"
    )
    sys.path.insert(0, str(src_dir))
    try:
        module = load_module(
            "customer_support_reply_guardrails",
            "case-studies/examples/customer-support-email-agent-starter/src/reply_guardrails.py",
        )
    finally:
        sys.path.remove(str(src_dir))

    policy_path = REPO_ROOT / ".tmp-customer-support-policy.md"
    policy_path.write_text(
        "Refunds are available within 30 days when the customer received the "
        "wrong item. Chargebacks and privacy requests must escalate to human "
        "review.",
        encoding="utf-8",
    )
    try:
        result = module.draft_policy_grounded_reply(
            "Subject: Refund request\nI received the wrong item yesterday.",
            str(policy_path),
        )
        handoff = module.draft_policy_grounded_reply(
            "Subject: Privacy request\nPlease delete my data immediately.",
            str(policy_path),
        )
    finally:
        policy_path.unlink(missing_ok=True)

    assert result.classification == "refund_request"
    assert result.policy_evidence
    assert result.needs_human_review is False
    assert "refund" in result.reply_subject.lower()
    assert "wrong item" in result.reply_body.lower()
    assert handoff.classification == "handoff_required"
    assert handoff.needs_human_review is True


def main() -> int:
    checks = [
        ("patterns/examples/agent-memory-retrieval-starter", check_memory_starter),
        ("patterns/examples/prompt-cache-agent-starter", check_prompt_cache_starter),
        ("systems/examples/weather-mcp-server-starter", check_weather_starter),
        ("ecosystem/examples/langgraph-starter", check_langgraph_starter),
        (
            "ecosystem/examples/messaging-transaction-assistant-starter",
            check_messaging_transaction_starter,
        ),
        ("case-studies/examples/deep-research-agent-starter", check_research_starter),
        (
            "case-studies/examples/customer-support-email-agent-starter",
            check_customer_support_starter,
        ),
    ]

    failures = 0
    for label, check in checks:
        try:
            check()
        except Exception as exc:  # pragma: no cover - direct CLI feedback
            failures += 1
            print(f"FAIL {label}: {exc}", file=sys.stderr)
        else:
            print(f"PASS {label}")

    if failures:
        print(
            f"{failures} starter check(s) failed.",
            file=sys.stderr,
        )
        return 1

    print(
        "All starter checks passed. These projects remain intentionally small"
        " starter examples rather than full production applications."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
