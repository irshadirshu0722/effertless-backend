from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CheckoutSessionResult:
    subscription_id: str
    checkout_session_id: str
    status: str = "pending"
