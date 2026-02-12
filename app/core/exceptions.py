"""
Custom exceptions for METRO API.
Aligned with D9.1 Section 3.1.3 Error Handling specification.
"""

from typing import Any


class MetroAPIException(Exception):
    """Base exception for all METRO API errors."""

    def __init__(
        self,
        error: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to response dictionary."""
        response = {
            "error": self.error,
            "message": self.message,
        }
        if self.details:
            response["details"] = self.details
        return response


class ValidationException(MetroAPIException):
    """400 - Malformed request (invalid JSON, missing parameters)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error="validation_failed",
            message=message,
            status_code=400,
            details=details,
        )


class UnauthorizedException(MetroAPIException):
    """401 - Missing or invalid DDTE token."""

    def __init__(self, message: str = "Valid token required"):
        super().__init__(
            error="unauthorized",
            message=message,
            status_code=401,
        )


class ForbiddenException(MetroAPIException):
    """403 - Valid token but insufficient permissions."""

    def __init__(self, message: str = "Access denied", details: dict[str, Any] | None = None):
        super().__init__(
            error="forbidden",
            message=message,
            status_code=403,
            details=details,
        )


class AssetNotFoundException(MetroAPIException):
    """404 - Asset not found."""

    def __init__(self, asset_id: str):
        super().__init__(
            error="not_found",
            message=f"Asset with ID '{asset_id}' not found",
            status_code=404,
        )


class PayloadTooLargeException(MetroAPIException):
    """413 - Upload size exceeds limit."""

    def __init__(self, max_size: int):
        max_size_mb = max_size / (1024 * 1024)
        super().__init__(
            error="payload_too_large",
            message=f"Maximum upload size exceeded ({max_size_mb:.0f}MB limit)",
            status_code=413,
        )


class StorageException(MetroAPIException):
    """500 - Storage backend error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error="storage_error",
            message=message,
            status_code=500,
            details=details,
        )
