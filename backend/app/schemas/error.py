"""VANTYX Standardized Error Schemas.

Ensures all client-facing API errors adhere to a predictable contract.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ErrorItem(BaseModel):
    """Specific error descriptor."""
    code: str = Field(description="Machine-readable error classification code")
    message: str = Field(description="Human-readable explanation of the error")
    field: Optional[str] = Field(default=None, description="Request parameter or field causing the error, if any")


class ErrorResponse(BaseModel):
    """Uniform error envelope returned by all API endpoints."""
    success: bool = Field(default=False, description="Always false for error envelopes")
    error: ErrorItem = Field(description="Primary error detail")
    details: Optional[List[Any]] = Field(default=None, description="Detailed validation breakdown or contextual list")
