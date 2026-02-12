"""
Authentication dependencies for FastAPI.
Provides dependency injection for authenticated endpoints.
"""

from typing import Annotated, Any

from fastapi import Depends, Header, Request

from app.config import get_settings
from app.core.exceptions import UnauthorizedException
from app.auth.jwt import validate_token, extract_user_claims, check_scope

settings = get_settings()


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    Dependency to get current authenticated user.
    
    In development mode (DEV_MODE=true), returns mock user.
    In production, validates JWT token from Authorization header.
    
    Args:
        request: FastAPI request
        authorization: Authorization header value
        
    Returns:
        User claims dictionary
        
    Raises:
        UnauthorizedException: If authentication fails
    """
    # Development mode - bypass authentication
    if settings.DEV_MODE:
        user_claims = {
            "user_id": settings.DEV_USER_ID,
            "name": "Development User",
            "email": settings.DEV_USER_EMAIL,
            "institution": settings.DEV_USER_INSTITUTION,
            "roles": ["researcher", "dtrip4h_member"],
            "is_consortium_member": True,
            "scopes": ["assets:read", "assets:write"],
        }
        # Store in request state for access in endpoints
        request.state.user = user_claims
        return user_claims
    
    # Production mode - require valid token
    if not authorization:
        raise UnauthorizedException("Authorization header required")
    
    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException("Invalid authorization header format")
    
    token = parts[1]
    
    # Validate token and extract claims
    payload = await validate_token(token)
    user_claims = extract_user_claims(payload)
    
    # Store in request state
    request.state.user = user_claims
    
    return user_claims


async def get_optional_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | None:
    """
    Dependency to optionally get current user.
    Returns None if no valid authentication provided.
    
    Useful for endpoints that work with or without authentication
    but may provide different results.
    """
    if settings.DEV_MODE:
        user_claims = {
            "user_id": settings.DEV_USER_ID,
            "name": "Development User",
            "email": settings.DEV_USER_EMAIL,
            "institution": settings.DEV_USER_INSTITUTION,
            "roles": ["researcher", "dtrip4h_member"],
            "is_consortium_member": True,
            "scopes": ["assets:read", "assets:write"],
        }
        request.state.user = user_claims
        return user_claims
    
    if not authorization:
        return None
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        token = parts[1]
        payload = await validate_token(token)
        user_claims = extract_user_claims(payload)
        request.state.user = user_claims
        return user_claims
        
    except UnauthorizedException:
        return None


def require_scope(required_scope: str):
    """
    Dependency factory to require a specific scope.
    
    Usage:
        @app.post("/assets")
        async def create_asset(
            user: dict = Depends(require_scope("assets:write"))
        ):
            ...
    
    Args:
        required_scope: Required scope (e.g., "assets:read", "assets:write")
        
    Returns:
        Dependency function
    """
    async def _check_scope(
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if not check_scope(user, required_scope):
            raise UnauthorizedException(
                f"Required scope '{required_scope}' not present in token"
            )
        return user
    
    return _check_scope


# Type aliases for dependency injection
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
OptionalUser = Annotated[dict[str, Any] | None, Depends(get_optional_user)]

# Scoped dependencies
RequireRead = Annotated[dict[str, Any], Depends(require_scope("assets:read"))]
RequireWrite = Annotated[dict[str, Any], Depends(require_scope("assets:write"))]
RequireAdmin = Annotated[dict[str, Any], Depends(require_scope("assets:admin"))]
