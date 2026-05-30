import type {
  ActionSuggestion,
  HeuristicClassificationResult,
  HeuristicConfidence,
  IssueClassification,
} from "@/lib/types";

const SENSITIVE_TERMS = [
  "chargeback",
  "lawyer",
  "legal",
  "delete my data",
  "privacy",
  "fraud",
  "unsafe",
  "injury",
];

const SIGNATURE_MARKERS = [
  "sent from my iphone",
  "sent from my android",
  "best,",
  "thanks,",
  "regards,",
];

function stripHtmlBlocks(input: string): string {
  return input
    .replace(/<blockquote[\s\S]*?<\/blockquote>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<\/?(div|p|br|li|ul|ol|span|body|html|head)[^>]*>/gi, "\n")
    .replace(/<[^>]+>/g, " ");
}

function collapseWhitespace(input: string): string {
  return input
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function stripQuotedHistory(lines: string[]): string[] {
  const result: string[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (
      trimmed.startsWith(">") ||
      /^on .+wrote:$/i.test(trimmed) ||
      /^from:/i.test(trimmed) ||
      /^subject:/i.test(trimmed) ||
      /^sent:/i.test(trimmed)
    ) {
      break;
    }
    result.push(line);
  }
  return result;
}

function stripSignature(lines: string[]): string[] {
  const result: string[] = [];
  let stopIndex = lines.length;
  for (let index = 0; index < lines.length; index += 1) {
    const trimmed = lines[index]!.trim().toLowerCase();
    if (SIGNATURE_MARKERS.includes(trimmed)) {
      stopIndex = index;
      break;
    }
  }
  for (let index = 0; index < stopIndex; index += 1) {
    result.push(lines[index]!);
  }
  return result;
}

export function cleanEmailBody(input: string): string {
  const withoutHtml = stripHtmlBlocks(input);
  const lines = collapseWhitespace(withoutHtml).split("\n");
  const withoutQuoted = stripQuotedHistory(lines);
  const withoutSignature = stripSignature(withoutQuoted);
  return collapseWhitespace(withoutSignature.join("\n"));
}

function makeResult(
  classification: IssueClassification,
  confidence: HeuristicConfidence,
  urgency: "normal" | "high",
  matchedTerms: string[],
): HeuristicClassificationResult {
  return { classification, confidence, urgency, matchedTerms };
}

function matchAny(normalized: string, terms: string[]): string[] {
  return terms.filter((term) => normalized.includes(term));
}

export function classifyHeuristically(input: string): HeuristicClassificationResult {
  const normalized = collapseWhitespace(input.toLowerCase());
  const urgency = matchAny(normalized, ["urgent", "asap", "immediately"]).length > 0 ? "high" : "normal";

  const sensitiveMatches = matchAny(normalized, SENSITIVE_TERMS);
  if (sensitiveMatches.length > 0) {
    return makeResult("handoff_required", "high", "high", sensitiveMatches);
  }

  const refundMatches = matchAny(normalized, ["refund", "money back", "return", "wrong item"]);
  if (refundMatches.length > 0) {
    return makeResult("refund_request", refundMatches.length > 1 ? "high" : "medium", urgency, refundMatches);
  }

  const billingMatches = matchAny(normalized, ["invoice", "billing", "payment", "charge"]);
  if (billingMatches.length > 0) {
    return makeResult("billing_issue", billingMatches.length > 1 ? "high" : "medium", urgency, billingMatches);
  }

  const complaintMatches = matchAny(normalized, ["complaint", "angry", "upset", "terrible", "broken"]);
  if (complaintMatches.length > 0) {
    return makeResult("complaint", complaintMatches.length > 1 ? "high" : "medium", urgency, complaintMatches);
  }

  const queryMatches = matchAny(normalized, ["question", "can you", "how do", "help"]);
  if (queryMatches.length > 0) {
    return makeResult("query", queryMatches.length > 1 ? "medium" : "low", urgency, queryMatches);
  }

  return makeResult("query", "low", urgency, []);
}

export function selectActionSuggestion(classification: IssueClassification): ActionSuggestion {
  if (classification === "handoff_required") {
    return "handoff";
  }
  if (classification === "complaint") {
    return "manual_follow_up";
  }
  return "send_reply";
}

export function shouldUseModelUnderstanding(result: HeuristicClassificationResult): boolean {
  return result.classification === "handoff_required" || result.confidence !== "high";
}

export function summarizeCleanBody(body: string, maxWords = 24): string {
  const words = collapseWhitespace(body).split(" ").filter(Boolean);
  if (words.length <= maxWords) {
    return words.join(" ");
  }
  return `${words.slice(0, maxWords).join(" ")}...`;
}
