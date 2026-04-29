#!/usr/bin/env python3
"""Compare cold and warm agent-run artifacts for prompt-cache stability."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class RunArtifact:
    label: str
    latency_ms: float | None
    prompt_tokens: int | None
    cached_tokens: int | None
    output_tokens: int | None
    system_prompt_hash: str | None
    tool_manifest_hash: str | None
    history_hash: str | None
    prefix_hash: str | None
    prompt_cache_key: str | None
    notes: list[str]


@dataclass
class BenchmarkReport:
    cold_label: str
    warm_label: str
    cold_latency_ms: float | None
    warm_latency_ms: float | None
    latency_delta_ms: float | None
    cold_cache_share: float | None
    warm_cache_share: float | None
    likely_cache_breaks: list[str]
    notes: list[str]


def load_run(path: Path) -> RunArtifact:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RunArtifact(
        label=str(payload.get("label") or path.stem),
        latency_ms=_optional_float(payload.get("latency_ms")),
        prompt_tokens=_optional_int(payload.get("prompt_tokens")),
        cached_tokens=_optional_int(payload.get("cached_tokens")),
        output_tokens=_optional_int(payload.get("output_tokens")),
        system_prompt_hash=_optional_str(payload.get("system_prompt_hash")),
        tool_manifest_hash=_optional_str(payload.get("tool_manifest_hash")),
        history_hash=_optional_str(payload.get("history_hash")),
        prefix_hash=_optional_str(payload.get("prefix_hash")),
        prompt_cache_key=_optional_str(payload.get("prompt_cache_key")),
        notes=_optional_str_list(payload.get("notes")),
    )


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("notes must be a list or null")
    return [str(note) for note in value]


def cache_share(run: RunArtifact) -> float | None:
    if not run.prompt_tokens or run.cached_tokens is None:
        return None
    if run.prompt_tokens <= 0:
        return None
    return run.cached_tokens / run.prompt_tokens


def compare_runs(cold: RunArtifact, warm: RunArtifact) -> BenchmarkReport:
    likely_breaks: list[str] = []
    notes: list[str] = []
    for field_name, label in (
        ("system_prompt_hash", "system prompt changed"),
        ("tool_manifest_hash", "tool manifest changed"),
        ("prefix_hash", "prompt prefix changed"),
        ("history_hash", "conversation history changed"),
        ("prompt_cache_key", "prompt cache key changed"),
    ):
        cold_value = getattr(cold, field_name)
        warm_value = getattr(warm, field_name)
        if cold_value is None and warm_value is None:
            continue
        if cold_value is None:
            notes.append(f"{field_name} missing in cold artifact.")
            continue
        if warm_value is None:
            notes.append(f"{field_name} missing in warm artifact.")
            continue
        if cold_value != warm_value:
            likely_breaks.append(label)

    cold_share = cache_share(cold)
    warm_share = cache_share(warm)

    if warm_share is None:
        notes.append("Warm run does not expose cached-token share.")
    elif warm_share == 0:
        notes.append("Warm run shows zero cached-token reuse.")
    elif warm_share < 0.5:
        notes.append("Warm run reused only a minority of prompt tokens.")
    else:
        notes.append("Warm run reused a meaningful portion of the prompt.")

    if cold.notes or warm.notes:
        notes.extend([*cold.notes, *warm.notes])

    latency_delta_ms: float | None = None
    if cold.latency_ms is not None and warm.latency_ms is not None:
        latency_delta_ms = warm.latency_ms - cold.latency_ms

    return BenchmarkReport(
        cold_label=cold.label,
        warm_label=warm.label,
        cold_latency_ms=cold.latency_ms,
        warm_latency_ms=warm.latency_ms,
        latency_delta_ms=latency_delta_ms,
        cold_cache_share=cold_share,
        warm_cache_share=warm_share,
        likely_cache_breaks=likely_breaks,
        notes=notes,
    )


def render_markdown(report: BenchmarkReport) -> str:
    def pct(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value * 100:.1f}%"

    def latency(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.0f} ms"

    lines = [
        "# Cache Benchmark Report",
        "",
        "## Run Pair",
        "",
        f"- Cold run: `{report.cold_label}`",
        f"- Warm run: `{report.warm_label}`",
        "",
        "## Metrics",
        "",
        f"- Cold latency: {latency(report.cold_latency_ms)}",
        f"- Warm latency: {latency(report.warm_latency_ms)}",
        f"- Latency delta: {latency(report.latency_delta_ms)}",
        f"- Cold cached-token share: {pct(report.cold_cache_share)}",
        f"- Warm cached-token share: {pct(report.warm_cache_share)}",
        "",
        "## Likely Cache Breaks",
        "",
    ]
    if report.likely_cache_breaks:
        lines.extend(f"- {item}" for item in report.likely_cache_breaks)
    else:
        lines.append("- No structural cache-break field changed in the supplied artifacts.")
    lines.extend(
        [
            "",
            "## Notes",
            "",
        ]
    )
    if report.notes:
        lines.extend(f"- {item}" for item in report.notes)
    else:
        lines.append("- No extra notes were supplied.")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cold-run", required=True, type=Path)
    parser.add_argument("--warm-run", required=True, type=Path)
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cold = load_run(args.cold_run)
    warm = load_run(args.warm_run)
    report = compare_runs(cold, warm)

    if args.format == "json":
        rendered = json.dumps(asdict(report), indent=2) + "\n"
    else:
        rendered = render_markdown(report)

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
