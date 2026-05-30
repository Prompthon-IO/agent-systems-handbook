import {
  cleanEmailBody,
  classifyHeuristically,
  selectActionSuggestion,
  shouldUseModelUnderstanding,
} from "@/lib/email-processing";

describe("email processing", () => {
  it("strips html, signatures, and quoted history before model reads", () => {
    const cleaned = cleanEmailBody(`
      <div>Hello support team,<br/>I need a refund for the wrong item.</div>
      <div>Best,<br/>Casey</div>
      <div>Sent from my iPhone</div>
      <blockquote>On Thu, support@example.com wrote: older thread</blockquote>
    `);

    expect(cleaned).toContain("Hello support team");
    expect(cleaned).toContain("refund for the wrong item");
    expect(cleaned).not.toContain("Sent from my iPhone");
    expect(cleaned).not.toContain("older thread");
    expect(cleaned).not.toContain("<div>");
  });

  it("classifies obvious refund requests without model usage", () => {
    const result = classifyHeuristically(
      "Subject: Refund request\nI received the wrong item and want a refund.",
    );

    expect(result.classification).toBe("refund_request");
    expect(result.confidence).toBe("high");
    expect(result.urgency).toBe("normal");
    expect(selectActionSuggestion(result.classification)).toBe("send_reply");
    expect(shouldUseModelUnderstanding(result)).toBe(false);
  });

  it("routes sensitive messages to handoff with model fallback", () => {
    const result = classifyHeuristically(
      "Subject: Privacy complaint\nDelete my data immediately or my lawyer will contact you.",
    );

    expect(result.classification).toBe("handoff_required");
    expect(result.confidence).toBe("high");
    expect(result.urgency).toBe("high");
    expect(selectActionSuggestion(result.classification)).toBe("handoff");
    expect(shouldUseModelUnderstanding(result)).toBe(true);
  });
});
