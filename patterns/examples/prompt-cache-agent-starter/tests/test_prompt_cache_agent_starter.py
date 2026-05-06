#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from prompt_cache_agent_starter import (  # noqa: E402
    Pricing,
    RunObservation,
    TokenUsage,
    build_prompt_layers,
    cache_boundary_index,
    compare_runs,
    stable_prefix_hash,
    summarize_usage,
)


def test_prompt_cache_boundary() -> None:
    layers = build_prompt_layers(
        tool_manifest="tool:get_weather",
        system_instructions="You are a bounded agent.",
        reference_context="Project policy v1",
        durable_memory_summary="User prefers concise answers.",
        current_task="Plan today's work.",
    )

    assert cache_boundary_index(layers) == 3
    assert [layer.name for layer in layers[3:]] == [
        "dynamic-memory",
        "turn-input",
    ]
    assert stable_prefix_hash(layers) == stable_prefix_hash(layers[:3])


def test_usage_summary_and_comparison() -> None:
    cold = RunObservation(
        label="cold",
        latency_ms=5200,
        usage=TokenUsage(input_tokens=10000, cache_write_tokens=7000),
        stable_prefix_hash="prefix-a",
    )
    warm = RunObservation(
        label="warm",
        latency_ms=2600,
        usage=TokenUsage(input_tokens=10000, cache_read_tokens=7000),
        stable_prefix_hash="prefix-a",
    )
    pricing = Pricing(
        base_input_usd_per_mtok=3.0,
        cache_write_usd_per_mtok=3.75,
        cache_hit_usd_per_mtok=0.30,
    )

    warm_summary = summarize_usage(warm.usage, pricing)
    comparison = compare_runs(cold, warm)

    assert warm_summary.cache_read_share == 0.7
    assert round(warm_summary.estimated_input_cost_usd or 0, 6) == 0.0111
    assert comparison.latency_delta_ms == -2600
    assert comparison.cache_read_share_delta == 0.7
    assert comparison.stable_prefix_changed is False


if __name__ == "__main__":
    test_prompt_cache_boundary()
    test_usage_summary_and_comparison()
    print("prompt-cache-agent-starter smoke test passed")
