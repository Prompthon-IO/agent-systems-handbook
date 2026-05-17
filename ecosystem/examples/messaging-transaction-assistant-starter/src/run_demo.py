from __future__ import annotations

from transaction_flow import run_flow


def main() -> int:
    handoff = run_flow("Recharge my family phone with a standard data plan")
    print(f"status: {handoff.status}")
    print(f"business_name: {handoff.business_context.business_name}")
    print(
        "knowledge_sources: "
        + ", ".join(handoff.business_context.knowledge_sources)
    )
    print(
        "human_takeover_available: "
        + str(handoff.business_context.human_takeover_available).lower()
    )
    print(f"recipient: {handoff.confirmation.recipient}")
    print(f"operator: {handoff.confirmation.operator}")
    print(f"amount_inr: {handoff.confirmation.amount_inr}")
    print("external_payment_executed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
