"""
Response utilities for METRO API.
Provides standardized response formatting.
"""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


def get_response_format(request: Request) -> str:
    """
    Determine response format based on Accept header.
    Supports content negotiation for JSON-LD.
    
    Args:
        request: FastAPI request object
        
    Returns:
        "jsonld" if client accepts application/ld+json, otherwise "json"
    """
    accept = request.headers.get("accept", "application/json")
    if "application/ld+json" in accept:
        return "jsonld"
    return "json"


def create_error_response(
    error: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """
    Create a standardized error response.
    Follows D9.1 Section 3.1.3 error format.
    
    Args:
        error: Error code string
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional error details
        
    Returns:
        JSONResponse with error payload
    """
    content = {
        "error": error,
        "message": message,
    }
    if details:
        content["details"] = details
    
    return JSONResponse(status_code=status_code, content=content)


def create_success_response(
    data: Any,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """
    Create a success response with optional headers.
    
    Args:
        data: Response payload
        status_code: HTTP status code (default 200)
        headers: Optional response headers
        
    Returns:
        JSONResponse with data payload
    """
    return JSONResponse(
        status_code=status_code,
        content=data,
        headers=headers,
    )
