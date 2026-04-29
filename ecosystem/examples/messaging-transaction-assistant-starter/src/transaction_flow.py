from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionIntent:
    raw_message: str
    recipient: str
    operator: str
    requested_action: str


@dataclass(frozen=True)
class RechargePlan:
    operator: str
    plan_id: str
    label: str
    price_inr: int
    validity_days: int
    data_gb: float


@dataclass(frozen=True)
class Confirmation:
    recipient: str
    operator: str
    plan_label: str
    amount_inr: int
    requires_user_confirmation: bool = True


@dataclass(frozen=True)
class PaymentHandoff:
    status: str
    payment_methods: tuple[str, ...]
    confirmation: Confirmation


PLANS = (
    RechargePlan(
        operator="generic-mobile",
        plan_id="starter-199",
        label="Starter data plan",
        price_inr=199,
        validity_days=28,
        data_gb=1.5,
    ),
    RechargePlan(
        operator="generic-mobile",
        plan_id="standard-299",
        label="Standard data plan",
        price_inr=299,
        validity_days=28,
        data_gb=2.0,
    ),
)


def capture_intent(message: str) -> TransactionIntent:
    normalized = message.lower()
    recipient = "self"
    if "family" in normalized or "mom" in normalized or "dad" in normalized:
        recipient = "family"
    elif "friend" in normalized:
        recipient = "friend"

    operator = "generic-mobile"
    if "operator a" in normalized:
        operator = "operator-a"
    elif "operator b" in normalized:
        operator = "operator-b"
    elif "operator c" in normalized:
        operator = "operator-c"

    return TransactionIntent(
        raw_message=message,
        recipient=recipient,
        operator=operator,
        requested_action="mobile-prepaid-recharge",
    )


def select_plan(intent: TransactionIntent, max_price_inr: int | None = None) -> RechargePlan:
    if max_price_inr is not None and max_price_inr <= 0:
        raise ValueError("budget must be positive")
    budget = max_price_inr if max_price_inr is not None else 9999
    candidates = [plan for plan in PLANS if plan.price_inr <= budget]
    if not candidates:
        raise ValueError("no starter plan fits the requested budget")
    selected = candidates[-1]
    if intent.operator != "generic-mobile":
        return RechargePlan(
            operator=intent.operator,
            plan_id=selected.plan_id,
            label=selected.label,
            price_inr=selected.price_inr,
            validity_days=selected.validity_days,
            data_gb=selected.data_gb,
        )
    return selected


def build_confirmation(intent: TransactionIntent, plan: RechargePlan) -> Confirmation:
    return Confirmation(
        recipient=intent.recipient,
        operator=plan.operator,
        plan_label=plan.label,
        amount_inr=plan.price_inr,
    )


def prepare_payment_handoff(confirmation: Confirmation) -> PaymentHandoff:
    if not confirmation.requires_user_confirmation:
        raise ValueError("payment handoff must require explicit user confirmation")
    return PaymentHandoff(
        status="awaiting-user-confirmation",
        payment_methods=("instant-transfer-like", "card-like"),
        confirmation=confirmation,
    )


def run_flow(message: str, max_price_inr: int | None = None) -> PaymentHandoff:
    intent = capture_intent(message)
    plan = select_plan(intent, max_price_inr=max_price_inr)
    confirmation = build_confirmation(intent, plan)
    return prepare_payment_handoff(confirmation)
