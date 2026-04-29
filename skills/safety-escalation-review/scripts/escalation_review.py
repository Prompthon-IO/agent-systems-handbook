#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


RISK_TERMS = {
    "violence": [
        "attack",
        "bomb",
        "gun",
        "kill",
        "mass shooting",
        "shoot",
        "stab",
        "weapon",
    ],
    "self_harm": [
        "end my life",
        "hurt myself",
        "self harm",
        "suicide",
        "suicidal",
    ],
    "targeting": [
        "address",
        "at school",
        "at work",
        "target",
        "tomorrow",
        "tonight",
    ],
    "evasion": [
        "banned account",
        "evade",
        "new account",
        "policy bypass",
        "work around",
    ],
}


REDACTIONS = [
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[redacted-email]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[redacted-phone]"),
    (re.compile(r"(?<![A-Za-z0-9_])(?:sk[-_][A-Za-z0-9_-]{16,}|gh(?:o|p)[_-][A-Za-z0-9_-]{16,}|pat[_-][A-Za-z0-9_-]{16,}|xoxb-[A-Za-z0-9-]{16,})\b"), "[redacted-token]"),
    (re.compile(r"\b(?:api[_-]?key|token|secret)\b\s*[:=]\s*(?:['\"])?[A-Za-z0-9][A-Za-z0-9_-]{11,}(?:['\"])?", re.I), "[redacted-secret]"),
]


@dataclass
class Review:
    source_path: Path
    severity: str
    signals: dict[str, list[str]]
    timeline_cues: list[str]
    redacted_excerpt: str
    reviewed_at: str


def read_input(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() != ".json":
        return raw

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    lines: list[str] = []

    def walk(value: object, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{prefix}{key}.")
        elif isinstance(value, list):
            for index, item in enumerate(value, start=1):
                walk(item, f"{prefix}{index}.")
        elif value is not None:
            label = prefix[:-1] if prefix else "value"
            lines.append(f"{label}: {value}")

    walk(data)
    return "\n".join(lines)


def redact(text: str) -> str:
    redacted = text
    for pattern, replacement in REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def find_signals(text: str) -> dict[str, list[str]]:
    lowered = text.lower()
    findings: dict[str, list[str]] = {}
    for category, terms in RISK_TERMS.items():
        hits = sorted({term for term in terms if term in lowered})
        if hits:
            findings[category] = hits
    return findings


def find_timeline_cues(text: str) -> list[str]:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:today|tonight|tomorrow|yesterday)\b",
        r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b\d{1,2}:\d{2}\s?(?:am|pm)?\b",
    ]
    cues: list[str] = []
    for pattern in patterns:
        cues.extend(match.group(0) for match in re.finditer(pattern, text, re.I))
    return sorted(set(cues))


def estimate_severity(signals: dict[str, list[str]], timeline_cues: Sequence[str]) -> str:
    categories = set(signals)
    has_time = bool(timeline_cues)
    if {"violence", "targeting"} <= categories and has_time:
        return "critical-review"
    if "violence" in categories and ("targeting" in categories or "evasion" in categories):
        return "high-review"
    if "self_harm" in categories or "violence" in categories:
        return "elevated-review"
    if categories:
        return "screening-review"
    return "no-obvious-risk-signal"


def excerpt(text: str, limit: int = 1200) -> str:
    compact = "\n".join(line.rstrip() for line in text.strip().splitlines())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "\n[excerpt truncated]"


def build_review(source_path: Path) -> Review:
    text = read_input(source_path)
    redacted = redact(text)
    signals = find_signals(redacted)
    timeline_cues = find_timeline_cues(redacted)
    return Review(
        source_path=source_path,
        severity=estimate_severity(signals, timeline_cues),
        signals=signals,
        timeline_cues=timeline_cues,
        redacted_excerpt=excerpt(redacted),
        reviewed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def render_memo(review: Review) -> str:
    signal_lines = [
        f"- {category}: {', '.join(terms)}"
        for category, terms in review.signals.items()
    ]
    if not signal_lines:
        signal_lines.append("- none detected by the deterministic keyword pass")

    timeline_lines = [f"- {cue}" for cue in review.timeline_cues]
    if not timeline_lines:
        timeline_lines.append("- no explicit date or time cues detected")

    return "\n".join(
        [
            "# Safety Escalation Review Memo",
            "",
            "## Case Summary",
            "",
            f"- Source evidence: `{review.source_path}`",
            f"- Reviewed at: {review.reviewed_at}",
            f"- Severity estimate: `{review.severity}`",
            "- External action taken: none",
            "",
            "This memo is a local preparation artifact for human review. It does",
            "not determine legal duties and does not contact external parties.",
            "",
            "## Detected Risk Signals",
            "",
            *signal_lines,
            "",
            "## Timeline Cues",
            "",
            *timeline_lines,
            "",
            "## Redacted Evidence Excerpt",
            "",
            "```text",
            review.redacted_excerpt or "[no text extracted]",
            "```",
            "",
            "## Privacy And Handling Notes",
            "",
            "- Keep the original evidence in its current local location.",
            "- Do not commit private transcripts, reports, or runtime artifacts.",
            "- Review the redaction before sharing this memo internally.",
            "- Apply organization policy before any external notification.",
            "",
            "## Human Handoff Checklist",
            "",
            "- [ ] Name the responsible human owner or team.",
            "- [ ] Separate direct evidence from interpretation.",
            "- [ ] Confirm whether any immediate safety action is required.",
            "- [ ] Confirm whether legal, trust-and-safety, security, or clinical",
            "      review owns the next decision.",
            "- [ ] Record the final human decision outside the public repository.",
            "",
        ]
    )


def default_output_path(source_path: Path) -> Path:
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", source_path.stem).strip("-")
    if not safe_name:
        safe_name = "evidence"
    base = Path.home() / ".codex" / "state" / "safety-escalation-review" / "memos"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return base / f"{safe_name}-{stamp}.md"


def expanded_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def command_review(args: argparse.Namespace) -> int:
    source_path = args.input
    if not source_path.exists():
        raise FileNotFoundError(f"input file does not exist: {source_path}")
    review = build_review(source_path)
    output_path = args.output if args.output else default_output_path(source_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_memo(review), encoding="utf-8")
    print(f"memo: {output_path}")
    print(f"severity: {review.severity}")
    print(f"signal_categories: {', '.join(review.signals) if review.signals else 'none'}")
    print("external_action_taken: none")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare a local safety escalation memo.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    review = subparsers.add_parser("review", help="review a local evidence file")
    review.add_argument("--input", required=True, type=expanded_path, help="local transcript, note, or JSON evidence file")
    review.add_argument("--output", type=expanded_path, help="Markdown memo path; defaults under ~/.codex/state")
    review.set_defaults(func=command_review)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
