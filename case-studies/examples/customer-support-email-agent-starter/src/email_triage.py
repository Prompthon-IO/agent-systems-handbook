from __future__ import annotations

from dataclasses import dataclass


SENSITIVE_TERMS = (
    "chargeback",
    "lawyer",
    "legal",
    "sue",
    "privacy",
    "delete my data",
    "unsafe",
    "injury",
    "fraud",
)


@dataclass
class TriageResult:
    classification: str
    summary: str
    urgency: str
    sentiment: str
    needs_human_review: bool


def classify_email(email_text: str) -> TriageResult:
    normalized = " ".join(email_text.lower().split())
    classification = "query"

    if any(term in normalized for term in SENSITIVE_TERMS):
        classification = "handoff_required"
    elif any(term in normalized for term in ("refund", "return", "money back")):
        classification = "refund_request"
    elif any(term in normalized for term in ("invoice", "charge", "billing", "payment")):
        classification = "billing_issue"
    elif any(term in normalized for term in ("angry", "upset", "complaint", "terrible", "wrong item")):
        classification = "complaint"

    urgency = "high" if any(term in normalized for term in ("urgent", "asap", "immediately")) else "normal"
    sentiment = "negative" if classification in {"complaint", "handoff_required"} else "neutral"
    needs_review = classification == "handoff_required"

    return TriageResult(
        classification=classification,
        summary=summarize_email(email_text),
        urgency=urgency,
        sentiment=sentiment,
        needs_human_review=needs_review,
    )


def summarize_email(email_text: str, max_words: int = 28) -> str:
    words = " ".join(email_text.split()).split(" ")
    summary = " ".join(words[:max_words]).strip()
    if len(words) > max_words:
        return f"{summary}..."
    return summary
