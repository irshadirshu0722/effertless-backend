"""Provider-independent authenticated user identity."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Identity extracted from a verified authentication token."""

    user_id: str
    email: str | None = None
    email_verified: bool = False
    claims: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("Authenticated user_id must not be empty")

        object.__setattr__(
            self,
            "claims",
            MappingProxyType(dict(self.claims)),
        )
