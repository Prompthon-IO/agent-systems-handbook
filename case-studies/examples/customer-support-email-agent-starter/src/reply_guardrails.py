from __future__ import annotations

from dataclasses import dataclass

from email_triage import TriageResult, classify_email
from policy_loader import find_policy_evidence, load_policy_document


ESCALATION_CLASSIFICATIONS = {"handoff_required"}


@dataclass
class DraftReply:
    summary: str
    classification: str
    policy_evidence: list[str]
    reply_subject: str
    reply_body: str
    needs_human_review: bool


def draft_policy_grounded_reply(email_text: str, policy_path: str) -> DraftReply:
    triage = classify_email(email_text)
    policy = load_policy_document(policy_path)
    query_terms = terms_for_classification(triage)
    evidence = find_policy_evidence(policy, query_terms)
    needs_review = triage.needs_human_review or not evidence

    subject = subject_for_classification(triage.classification)
    body = build_reply_body(triage, evidence, needs_review)

    return DraftReply(
        summary=triage.summary,
        classification=triage.classification,
        policy_evidence=evidence,
        reply_subject=subject,
        reply_body=body,
        needs_human_review=needs_review,
    )


def terms_for_classification(triage: TriageResult) -> list[str]:
    terms = [triage.classification.replace("_", " ")]
    if triage.classification == "refund_request":
        terms.extend(["refund", "return", "replacement"])
    elif triage.classification == "billing_issue":
        terms.extend(["billing", "invoice", "payment", "charge"])
    elif triage.classification == "complaint":
        terms.extend(["complaint", "wrong item", "damaged", "support"])
    elif triage.classification == "handoff_required":
        terms.extend(["escalate", "human review", "privacy", "chargeback"])
    else:
        terms.extend(["faq", "question", "support"])
    return terms


def subject_for_classification(classification: str) -> str:
    labels = {
        "refund_request": "Re: Your refund request",
        "billing_issue": "Re: Your billing question",
        "complaint": "Re: Your support concern",
        "handoff_required": "Re: Your support request",
        "query": "Re: Your question",
    }
    return labels.get(classification, "Re: Your support request")


def build_reply_body(
    triage: TriageResult,
    evidence: list[str],
    needs_human_review: bool,
) -> str:
    if needs_human_review:
        return (
            "Thanks for reaching out. I want to make sure we handle this "
            "correctly, so I am routing your request to our support team for "
            "human review. We will follow up after checking the relevant "
            "policy and account details."
        )

    policy_line = evidence[0]
    return (
        "Thanks for reaching out. Based on our support policy, "
        f"{policy_line} "
        "If you can share any missing order or account details, our team can "
        "continue from there."
    )
