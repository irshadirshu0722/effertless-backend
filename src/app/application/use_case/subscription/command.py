from dataclasses import dataclass

from app.domain.entities.authenticated_user import AuthenticatedUser


@dataclass(slots=True)
class InitiateCheckoutCommand:
    user: AuthenticatedUser
    plan_code: str
    return_url: str
