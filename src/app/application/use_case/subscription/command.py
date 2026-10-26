from dataclasses import dataclass
from typing import Any

from app.domain.entities.authenticated_user import AuthenticatedUser


@dataclass(slots=True)
class InitiateCheckoutCommand:
    user: AuthenticatedUser
    plan_code: str
    return_url: str
    replace: bool


@dataclass(slots=True)
class SubscriptionWebhookCommand:
    raw_payload: bytes
    signature: str
    timestamp: str
    event_data: dict[str, Any]
