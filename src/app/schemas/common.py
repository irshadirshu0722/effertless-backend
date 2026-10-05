"""Common API response schemas.

Pydantic models used across multiple endpoints. Domain models (in app/domain/)
are separate from these API schemas — explicit mapping methods prevent coupling.
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Standard error detail within an error response."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response format (see docs/api/errors.md)."""

    error: ErrorDetail
