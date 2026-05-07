#!/usr/bin/env python3
"""Build a local report from captured Claude prompt-cache run artifacts."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass
class RunArtifact:
    label: str
    latency_ms: float | None
    input_tokens: int | None
    cache_write_tokens: int
    cache_read_tokens: int
    output_tokens: int | None
    stable_layer_hash: str | None
    dynamic_memory_hash: str | None
    notes: list[str]


@dataclass
class Pricing:
    base_input_usd_per_mtok: float | None
    cache_write_usd_per_mtok: float | None
    cache_hit_usd_per_mtok: float | None

    @property
    def complete(self) -> bool:
        return (
            self.base_input_usd_per_mtok is not None
            and self.cache_write_usd_per_mtok is not None
            and self.cache_hit_usd_per_mtok is not None
        )


def read_artifacts(path: Path) -> list[RunArtifact]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        rows = parse_jsonl(text)
    else:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            rows = parse_jsonl(text)
        else:
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict) and isinstance(payload.get("runs"), list):
                rows = payload["runs"]
            elif isinstance(payload, dict):
                rows = [payload]
            else:
                rows = []
    if not isinstance(rows, list) or not rows:
        raise ValueError("input must contain at least one run artifact")
    return [normalize_run(row, index) for index, row in enumerate(rows, start=1)]


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def normalize_run(row: dict[str, Any], index: int) -> RunArtifact:
    return RunArtifact(
        label=str(row.get("label") or f"run-{index}"),
        latency_ms=optional_float(row.get("latency_ms")),
        input_tokens=optional_int(row.get("input_tokens", row.get("prompt_tokens"))),
        cache_write_tokens=optional_int(
            row.get(
                "cache_creation_input_tokens",
                row.get("cache_write_tokens", 0),
            )
        )
        or 0,
        cache_read_tokens=optional_int(
            row.get("cache_read_input_tokens", row.get("cached_tokens", 0))
        )
        or 0,
        output_tokens=optional_int(row.get("output_tokens")),
        stable_layer_hash=optional_str(
            row.get("stable_layer_hash", row.get("prefix_hash"))
        ),
        dynamic_memory_hash=optional_str(row.get("dynamic_memory_hash")),
        notes=optional_str_list(row.get("notes")),
    )


def optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def optional_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("notes must be a list when present")
    return [str(item) for item in value]


def ratio(numerator: int, denominator: int | None) -> float | None:
    if denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def total_input_tokens(run: RunArtifact) -> int | None:
    if run.input_tokens is None:
        if run.cache_write_tokens or run.cache_read_tokens:
            return run.cache_write_tokens + run.cache_read_tokens
        return None
    return run.input_tokens + run.cache_write_tokens + run.cache_read_tokens


def estimate_input_cost(run: RunArtifact, pricing: Pricing) -> float | None:
    if not pricing.complete or run.input_tokens is None:
        return None
    return (
        (run.input_tokens / 1_000_000) * pricing.base_input_usd_per_mtok
        + (run.cache_write_tokens / 1_000_000) * pricing.cache_write_usd_per_mtok
        + (run.cache_read_tokens / 1_000_000) * pricing.cache_hit_usd_per_mtok
    )


def optional_field_status(values: Iterable[str | None]) -> str:
    collected = list(values)
    present = [value for value in collected if value is not None]
    if not present:
        return "missing"
    if len(present) != len(collected):
        return "partial"
    if len(set(present)) == 1:
        return "same"
    return "changed"


def render_report(runs: list[RunArtifact], pricing: Pricing) -> str:
    lines = [
        "# Prompt Cache Harness Report",
        "",
        "## Runs",
        "",
        "| Run | Latency | Regular input | Cache writes | Cache reads | Total input | Read share | Write share | Input cost |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in runs:
        total_tokens = total_input_tokens(run)
        read_share = ratio(run.cache_read_tokens, total_tokens)
        write_share = ratio(run.cache_write_tokens, total_tokens)
        cost = estimate_input_cost(run, pricing)
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{run.label}`",
                    format_latency(run.latency_ms),
                    format_int(run.input_tokens),
                    format_int(run.cache_write_tokens),
                    format_int(run.cache_read_tokens),
                    format_int(total_tokens),
                    format_percent(read_share),
                    format_percent(write_share),
                    format_cost(cost),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Cache Boundary Signals", ""])
    stable_status = optional_field_status(run.stable_layer_hash for run in runs)
    if stable_status == "changed":
        lines.append("- Stable layer hash changed across runs; cache reuse may be invalidated.")
    elif stable_status == "partial":
        lines.append("- Stable layer hash is missing in at least one run; stability is not comparable.")
    elif stable_status == "missing":
        lines.append("- Stable layer hash was not supplied.")
    else:
        lines.append("- Stable layer hash stayed constant across supplied runs.")

    memory_status = optional_field_status(run.dynamic_memory_hash for run in runs)
    if memory_status == "changed":
        lines.append("- Dynamic memory hash changed; this is acceptable only if memory sits after the cache boundary.")
    elif memory_status == "partial":
        lines.append("- Dynamic memory hash is missing in at least one run; memory movement is not comparable.")
    elif memory_status == "missing":
        lines.append("- Dynamic memory hash was not supplied.")
    else:
        lines.append("- Dynamic memory hash stayed constant across supplied runs.")

    warm_runs = runs[1:] if len(runs) > 1 else runs
    warm_read_shares = [
        share
        for share in (ratio(run.cache_read_tokens, total_input_tokens(run)) for run in warm_runs)
        if share is not None
    ]
    if warm_read_shares and max(warm_read_shares) >= 0.5:
        lines.append("- At least one warm run reused a meaningful share of input tokens.")
    elif warm_read_shares:
        lines.append("- Warm runs show limited cache-read reuse.")
    else:
        lines.append("- Cache-read share could not be calculated from supplied artifacts.")

    notes = [note for run in runs for note in run.notes]
    if notes:
        lines.extend(["", "## Operator Notes", ""])
        lines.extend(f"- {note}" for note in notes)

    return "\n".join(lines) + "\n"


def format_latency(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0f} ms"


def format_int(value: int | None) -> str:
    if value is None:
        return "n/a"
    return str(value)


def format_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def format_cost(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:.6f}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--base-input-usd-per-mtok", type=float)
    parser.add_argument("--cache-write-usd-per-mtok", type=float)
    parser.add_argument("--cache-hit-usd-per-mtok", type=float)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pricing = Pricing(
        base_input_usd_per_mtok=args.base_input_usd_per_mtok,
        cache_write_usd_per_mtok=args.cache_write_usd_per_mtok,
        cache_hit_usd_per_mtok=args.cache_hit_usd_per_mtok,
    )
    report = render_report(read_artifacts(args.input), pricing)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
