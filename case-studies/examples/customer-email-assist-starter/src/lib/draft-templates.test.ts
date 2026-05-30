import { renderDraftFromTemplate } from "@/lib/draft-templates";

describe("draft templates", () => {
  it("renders a refund reply from JSON slot values and policy evidence", () => {
    const rendered = renderDraftFromTemplate({
      classification: "refund_request",
      customerName: "Casey",
      acknowledgement: "I understand the wrong item was delivered.",
      nextStep: "We can review the order once you confirm the order number.",
      policyEvidence: [
        "Refunds are available within 30 days when the customer received the wrong item.",
      ],
      signoff: "Support Team",
    });

    expect(rendered.subject).toBe("Re: Your refund request");
    expect(rendered.html).toContain("Casey");
    expect(rendered.html).toContain("wrong item was delivered");
    expect(rendered.html).toContain("Refunds are available within 30 days");
    expect(rendered.text).toContain("Support Team");
  });
});
