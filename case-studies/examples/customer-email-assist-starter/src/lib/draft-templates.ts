import type { DraftTemplateFields, RenderedDraft } from "@/lib/types";

function escapeHtml(input: string): string {
  return input
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function subjectForClassification(classification: DraftTemplateFields["classification"]): string {
  switch (classification) {
    case "refund_request":
      return "Re: Your refund request";
    case "billing_issue":
      return "Re: Your billing question";
    case "complaint":
      return "Re: Your support concern";
    case "handoff_required":
      return "Re: Your support request";
    case "query":
    default:
      return "Re: Your question";
  }
}

export function renderDraftFromTemplate(fields: DraftTemplateFields): RenderedDraft {
  const greeting = fields.customerName.trim() ? `Hi ${fields.customerName.trim()},` : "Hello,";
  const evidenceHtml = fields.policyEvidence
    .map((entry) => `<li>${escapeHtml(entry)}</li>`)
    .join("");
  const evidenceText = fields.policyEvidence.map((entry) => `- ${entry}`).join("\n");

  const html = [
    `<p>${escapeHtml(greeting)}</p>`,
    `<p>${escapeHtml(fields.acknowledgement)}</p>`,
    `<p>${escapeHtml(fields.nextStep)}</p>`,
    evidenceHtml ? `<p>Policy evidence:</p><ul>${evidenceHtml}</ul>` : "",
    `<p>${escapeHtml(fields.signoff)}</p>`,
  ]
    .filter(Boolean)
    .join("");

  const text = [
    greeting,
    "",
    fields.acknowledgement,
    "",
    fields.nextStep,
    evidenceText ? `Policy evidence:\n${evidenceText}` : "",
    "",
    fields.signoff,
  ]
    .filter(Boolean)
    .join("\n");

  return {
    subject: subjectForClassification(fields.classification),
    html,
    text,
  };
}
