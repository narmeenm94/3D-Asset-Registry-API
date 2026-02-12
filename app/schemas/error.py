"""
Pydantic schemas for error responses.
Aligned with D9.1 Section 3.1.3 Error Handling.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Standard error response format per D9.1 Section 3.1.3.
    
    Examples:
        400: {"error": "validation_failed", "message": "..."}
        401: {"error": "unauthorized", "message": "valid token required"}
        403: {"error": "forbidden", "message": "access denied", "details": {...}}
        404: {"error": "not_found", "message": "asset ID not found"}
        413: {"error": "payload_too_large", "message": "maximum size exceeded"}
    """
    
    error: str = Field(
        ...,
        description="Error code string",
        examples=["validation_failed", "unauthorized", "forbidden", "not_found"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional error details",
    )


class ValidationErrorDetail(BaseModel):
    """Detail for validation errors."""
    
    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Response for validation errors (400)."""
    
    error: str = "validation_failed"
    message: str = "Request validation failed"
    details: list[ValidationErrorDetail]
