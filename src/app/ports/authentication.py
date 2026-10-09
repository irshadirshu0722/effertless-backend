"""Application-facing authentication contracts."""

from typing import Protocol

from app.domain.entities.authenticated_user import AuthenticatedUser


class IdentityVerifier(Protocol):
    """Verify external credentials and return a provider-independent identity."""

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Validate a bearer token and return the authenticated user."""
