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
    spec.loader.exec_module(module)
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
    assert trace.selected_sources == ["policy-note", "chat-log"]
    assert trace.deferred_sources == ["scratchpad"]
    assert policy_module.should_promote("Final decision to publish the summary")
    assert (
        policy_module.artifact_key("Decision: Publish Notes")
        == "decision-publish-notes"
    )


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


def main() -> int:
    checks = [
        ("patterns/examples/agent-memory-retrieval-starter", check_memory_starter),
        ("systems/examples/weather-mcp-server-starter", check_weather_starter),
        ("ecosystem/examples/langgraph-starter", check_langgraph_starter),
        ("case-studies/examples/deep-research-agent-starter", check_research_starter),
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
