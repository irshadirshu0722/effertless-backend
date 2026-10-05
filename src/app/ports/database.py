"""Persistence port marker for application-facing database contracts."""

from typing import Protocol


class UnitOfWork(Protocol):
    """Application boundary for transactional persistence operations."""
