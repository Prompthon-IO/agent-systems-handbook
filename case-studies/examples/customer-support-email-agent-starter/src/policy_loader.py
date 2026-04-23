from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class PolicyDocument:
    path: Path
    text: str


def load_policy_document(policy_path: str | Path) -> PolicyDocument:
    path = Path(policy_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"policy document not found: {path}")
    if not path.is_file():
        raise ValueError(f"policy path is not a file: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"policy document is empty: {path}")

    return PolicyDocument(path=path, text=text)


def find_policy_evidence(policy: PolicyDocument, query_terms: list[str], limit: int = 3) -> list[str]:
    sentences = split_sentences(policy.text)
    selected: list[str] = []
    lowered_terms = [term.lower() for term in query_terms if term.strip()]

    for sentence in sentences:
        normalized = sentence.lower()
        if any(term in normalized for term in lowered_terms):
            selected.append(sentence)
        if len(selected) >= limit:
            break

    return selected


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]
