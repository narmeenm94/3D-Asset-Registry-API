"""
Asset-level permission checking.
Implements the 6-level permission hierarchy per D9.1 Section 8.4.2.
"""

from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import ForbiddenException
from app.models.asset import AccessLevel, Asset


def check_asset_access(
    asset: Asset,
    user_claims: dict[str, Any],
    action: str = "read",
) -> bool:
    """
    Check if user has access to an asset.
    
    Implements the permission hierarchy:
    1. Private - Only owner can access
    2. Group - Authorized users/institutions
    3. Institution - Same institution members
    4. Consortium - All DTRIP4H members
    5. Approval Required - Explicit approval needed
    6. Public - Any authenticated user
    
    Args:
        asset: Asset model to check
        user_claims: User claims from JWT
        action: Action being performed ("read", "write", "delete")
        
    Returns:
        True if access is granted
        
    Raises:
        ForbiddenException: If access is denied
    """
    user_id = user_claims.get("user_id")
    user_institution = user_claims.get("institution")
    is_consortium_member = user_claims.get("is_consortium_member", False)
    
    # Owner always has access
    if user_id and asset.owner_id == user_id:
        return True
    
    # Write/delete actions require ownership
    if action in ("write", "delete"):
        raise ForbiddenException(
            message="Only asset owner can modify or delete assets",
            details={
                "asset_id": asset.id,
                "required": "ownership",
                "action": action,
            },
        )
    
    # Check embargo
    if asset.embargo_until:
        if datetime.now(timezone.utc) < asset.embargo_until:
            if asset.owner_id != user_id:
                raise ForbiddenException(
                    message="Asset is under embargo",
                    details={
                        "asset_id": asset.id,
                        "embargo_until": asset.embargo_until.isoformat(),
                    },
                )
    
    # Evaluate access based on level
    access_granted = _evaluate_access_level(
        asset=asset,
        user_id=user_id,
        user_institution=user_institution,
        is_consortium_member=is_consortium_member,
    )
    
    if not access_granted:
        raise ForbiddenException(
            message="Insufficient permissions to access this asset",
            details={
                "asset_id": asset.id,
                "required_access_level": asset.access_level.value,
                "user_institution": user_institution,
                "required_institution": asset.owner_institution if asset.access_level == AccessLevel.INSTITUTION else None,
            },
        )
    
    return True


def _evaluate_access_level(
    asset: Asset,
    user_id: str | None,
    user_institution: str | None,
    is_consortium_member: bool,
) -> bool:
    """
    Evaluate access based on asset's access level.
    
    Args:
        asset: Asset to check
        user_id: User's ID
        user_institution: User's institution
        is_consortium_member: Whether user is DTRIP4H member
        
    Returns:
        True if access should be granted
    """
    match asset.access_level:
        case AccessLevel.PRIVATE:
            # Only owner (checked above)
            return False
        
        case AccessLevel.GROUP:
            # Check authorized users list
            if user_id and asset.authorized_users:
                if user_id in asset.authorized_users:
                    return True
            
            # Check authorized institutions list
            if user_institution and asset.authorized_institutions:
                if user_institution in asset.authorized_institutions:
                    return True
            
            return False
        
        case AccessLevel.INSTITUTION:
            # Same institution only
            return user_institution and user_institution == asset.owner_institution
        
        case AccessLevel.CONSORTIUM:
            # Any DTRIP4H consortium member
            return is_consortium_member
        
        case AccessLevel.APPROVAL_REQUIRED:
            # User must be in approved list
            if user_id and asset.authorized_users:
                return user_id in asset.authorized_users
            return False
        
        case AccessLevel.PUBLIC:
            # Any authenticated user
            return user_id is not None
        
        case _:
            return False


def can_modify_asset(asset: Asset, user_claims: dict[str, Any]) -> bool:
    """
    Check if user can modify an asset (update metadata, tags, upload version).
    
    Args:
        asset: Asset to check
        user_claims: User claims from JWT
        
    Returns:
        True if user can modify the asset
    """
    user_id = user_claims.get("user_id")
    
    # Only owner can modify
    return user_id is not None and asset.owner_id == user_id


def get_access_denial_details(
    asset: Asset,
    user_claims: dict[str, Any],
) -> dict[str, Any]:
    """
    Get detailed information about why access was denied.
    Used for helpful error messages.
    
    Args:
        asset: Asset that was denied
        user_claims: User claims from JWT
        
    Returns:
        Details dictionary for error response
    """
    user_institution = user_claims.get("institution")
    
    details = {
        "asset_id": asset.id,
        "access_level": asset.access_level.value,
    }
    
    match asset.access_level:
        case AccessLevel.PRIVATE:
            details["reason"] = "Asset is private, only owner can access"
            details["contact"] = f"Contact asset owner for access"
        
        case AccessLevel.GROUP:
            details["reason"] = "Access restricted to specific users/institutions"
            details["required"] = "Must be in authorized users or institutions list"
        
        case AccessLevel.INSTITUTION:
            details["reason"] = "Access restricted to institution members"
            details["required_institution"] = asset.owner_institution
            details["user_institution"] = user_institution
        
        case AccessLevel.CONSORTIUM:
            details["reason"] = "Access restricted to DTRIP4H consortium members"
            details["required"] = "dtrip4h_member role"
        
        case AccessLevel.APPROVAL_REQUIRED:
            details["reason"] = "Explicit approval required from asset owner"
            details["contact"] = f"Request access from asset owner"
    
    return details
