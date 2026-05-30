import fs from "node:fs";
import path from "node:path";

import type { IssueClassification } from "@/lib/types";

function splitSentences(input: string): string[] {
  return input
    .split(/\n+|(?<=[.!?])\s+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
}

export function loadPolicyText(policyPath?: string): string {
  const resolvedPath = path.resolve(
    policyPath ??
      process.env.CUSTOMER_EMAIL_ASSIST_POLICY_PATH ??
      path.join(process.cwd(), "support-policy.md"),
  );
  return fs.readFileSync(resolvedPath, "utf8");
}

export function policyTermsForClassification(classification: IssueClassification): string[] {
  switch (classification) {
    case "refund_request":
      return ["refund", "wrong item", "return", "replacement"];
    case "billing_issue":
      return ["billing", "invoice", "payment", "charge"];
    case "complaint":
      return ["complaint", "support", "damaged", "wrong item"];
    case "handoff_required":
      return ["privacy", "chargeback", "manual review", "escalate"];
    case "query":
    default:
      return ["faq", "question", "support"];
  }
}

export function findPolicyEvidence(
  policyText: string,
  classification: IssueClassification,
  limit = 3,
): string[] {
  const terms = policyTermsForClassification(classification);
  const matches = splitSentences(policyText).filter((sentence) => {
    const normalized = sentence.toLowerCase();
    return terms.some((term) => normalized.includes(term));
  });

  return matches.slice(0, limit);
}
