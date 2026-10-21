"""Subscription, payment, and quota tracking ports."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.domain.entities.plan import Plan


class PlanRepository(Protocol):
    """Persistence contract for subscription plans."""

    async def list_active(self) -> Sequence[Plan]:
        """List all active, non-deleted plans."""

    async def get_by_code(self, code: str) -> Plan | None:
        """Fetch a plan by unique code."""

    async def get_by_id(self, plan_id: UUID) -> Plan | None:
        """Fetch a plan by unique ID."""

    async def save(self, plan: Plan) -> Plan:
        """Create or update a plan."""
