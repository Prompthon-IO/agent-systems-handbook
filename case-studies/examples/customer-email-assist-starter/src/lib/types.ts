export type CustomerStatus = "pending" | "approved" | "ignored";

export type IssueClassification =
  | "query"
  | "complaint"
  | "refund_request"
  | "billing_issue"
  | "handoff_required";

export type ActionSuggestion = "send_reply" | "manual_follow_up" | "handoff";

export type IssueStatus = "draft_ready" | "approved_to_send" | "resolved" | "sync_error";

export type Urgency = "normal" | "high";

export type HeuristicConfidence = "high" | "medium" | "low";

export interface HeuristicClassificationResult {
  classification: IssueClassification;
  confidence: HeuristicConfidence;
  urgency: Urgency;
  matchedTerms: string[];
}

export interface DraftTemplateFields {
  classification: IssueClassification;
  customerName: string;
  acknowledgement: string;
  nextStep: string;
  policyEvidence: string[];
  signoff: string;
}

export interface RenderedDraft {
  subject: string;
  html: string;
  text: string;
}

export interface PreparedCustomer {
  email: string;
  displayName: string;
  description: string;
  status: CustomerStatus;
}

export interface PreparedInboundItem {
  gmailThreadId: string;
  gmailLastInboundMessageId: string;
  subject: string;
  cleanBody: string;
  receivedAt: string;
  customer: PreparedCustomer;
}

export interface UnderstandingRecord {
  gmailThreadId: string;
  gmailLastInboundMessageId: string;
  customerEmail: string;
  customerName: string;
  subject: string;
  receivedAt: string;
  originalMessageText: string;
  classification: IssueClassification;
  summary: string;
  urgency: Urgency;
  actionSuggestion: ActionSuggestion;
}

export interface DraftBatchItem {
  issueId: number;
  classification: IssueClassification;
  customerName: string;
  summary: string;
  originalMessageText: string;
  policyEvidence: string[];
}

export interface DraftRenderRecord {
  issueId: number;
  classification: IssueClassification;
  draftFields: Omit<DraftTemplateFields, "classification">;
}
