"""
JWT token validation with JWKS caching.
Implements DDTE authentication per D9.1 Section 8.4.1.
"""

import time
from typing import Any

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.config import get_settings
from app.core.exceptions import UnauthorizedException

settings = get_settings()


# JWKS cache
_jwks_cache: dict[str, Any] = {}
_jwks_cache_time: float = 0


async def fetch_jwks() -> dict[str, Any]:
    """
    Fetch JWKS (JSON Web Key Set) from DDTE.
    Implements caching to reduce network calls.
    
    Returns:
        JWKS dictionary with public keys
        
    Raises:
        UnauthorizedException: If JWKS cannot be fetched
    """
    global _jwks_cache, _jwks_cache_time
    
    # Check cache validity
    current_time = time.time()
    if _jwks_cache and (current_time - _jwks_cache_time) < settings.JWKS_CACHE_TTL:
        return _jwks_cache
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                settings.DDTE_JWKS_URL,
                timeout=10.0,
            )
            response.raise_for_status()
            
            _jwks_cache = response.json()
            _jwks_cache_time = current_time
            
            return _jwks_cache
            
    except httpx.HTTPError as e:
        # If we have a cached version, use it even if expired
        if _jwks_cache:
            return _jwks_cache
        raise UnauthorizedException(f"Failed to fetch JWKS: {str(e)}")


def get_rsa_key(jwks: dict[str, Any], kid: str) -> dict[str, Any] | None:
    """
    Get RSA public key from JWKS by key ID.
    
    Args:
        jwks: JWKS dictionary
        kid: Key ID from JWT header
        
    Returns:
        RSA key dictionary or None if not found
    """
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key.get("kty"),
                "kid": key.get("kid"),
                "use": key.get("use"),
                "n": key.get("n"),
                "e": key.get("e"),
            }
    return None


async def validate_token(token: str) -> dict[str, Any]:
    """
    Validate a DDTE JWT token.
    
    Performs:
    1. Signature verification using JWKS public key
    2. Expiration check
    3. Issuer verification
    4. Audience verification
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token claims
        
    Raises:
        UnauthorizedException: If token is invalid
    """
    try:
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise UnauthorizedException("Token missing key ID")
        
        # Fetch JWKS and get signing key
        jwks = await fetch_jwks()
        rsa_key = get_rsa_key(jwks, kid)
        
        if not rsa_key:
            raise UnauthorizedException("Unable to find appropriate key")
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.DDTE_AUDIENCE,
            issuer=settings.DDTE_ISSUER,
        )
        
        return payload
        
    except ExpiredSignatureError:
        raise UnauthorizedException("Token has expired")
    except JWTError as e:
        raise UnauthorizedException(f"Invalid token: {str(e)}")


def extract_user_claims(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract user claims from validated JWT payload.
    
    Expected claims per D9.1 Section 8.4.1:
    - sub: User unique identifier
    - name: User display name
    - email: User email
    - institution_id: Institution code
    - roles: User roles array
    
    Args:
        payload: Decoded JWT payload
        
    Returns:
        Normalized user claims dictionary
    """
    roles = payload.get("roles", [])
    
    return {
        "user_id": payload.get("sub"),
        "name": payload.get("name"),
        "email": payload.get("email"),
        "institution": payload.get("institution_id"),
        "roles": roles,
        "is_consortium_member": "dtrip4h_member" in roles,
        "scopes": payload.get("scope", "").split() if payload.get("scope") else [],
    }


def check_scope(user_claims: dict[str, Any], required_scope: str) -> bool:
    """
    Check if user has required scope.
    
    Args:
        user_claims: Extracted user claims
        required_scope: Required scope (e.g., "assets:read")
        
    Returns:
        True if user has scope
    """
    return required_scope in user_claims.get("scopes", [])
