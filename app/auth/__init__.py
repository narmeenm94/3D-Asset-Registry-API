"""
Authentication and authorization module for METRO API.
Implements DDTE JWT token validation per D9.1 Section 4.1.
"""

from app.auth.jwt import validate_token, extract_user_claims, fetch_jwks, check_scope
from app.auth.permissions import check_asset_access, can_modify_asset, get_access_denial_details
from app.auth.dependencies import (
    get_current_user,
    get_optional_user,
    require_scope,
    CurrentUser,
    OptionalUser,
    RequireRead,
    RequireWrite,
    RequireAdmin,
)

__all__ = [
    # JWT functions
    "validate_token",
    "extract_user_claims",
    "fetch_jwks",
    "check_scope",
    # Permission functions
    "check_asset_access",
    "can_modify_asset",
    "get_access_denial_details",
    # Dependencies
    "get_current_user",
    "get_optional_user",
    "require_scope",
    # Type aliases
    "CurrentUser",
    "OptionalUser",
    "RequireRead",
    "RequireWrite",
    "RequireAdmin",
]
