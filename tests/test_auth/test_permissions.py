"""
Tests for permission system.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.auth.permissions import check_asset_access, can_modify_asset
from app.core.exceptions import ForbiddenException
from app.models.asset import AccessLevel


class MockAsset:
    """Mock asset for testing permissions."""
    
    def __init__(
        self,
        id: str = "test-asset-id",
        owner_id: str = "owner-user-id",
        owner_institution: str = "METRO_Finland",
        access_level: AccessLevel = AccessLevel.PRIVATE,
        authorized_users: list | None = None,
        authorized_institutions: list | None = None,
        embargo_until: datetime | None = None,
    ):
        self.id = id
        self.owner_id = owner_id
        self.owner_institution = owner_institution
        self.access_level = access_level
        self.authorized_users = authorized_users
        self.authorized_institutions = authorized_institutions
        self.embargo_until = embargo_until


class TestPrivateAccess:
    """Tests for private access level."""
    
    def test_owner_can_access(self):
        """Owner should be able to access private assets."""
        asset = MockAsset(access_level=AccessLevel.PRIVATE)
        user_claims = {"user_id": "owner-user-id", "institution": "METRO_Finland"}
        
        result = check_asset_access(asset, user_claims)
        assert result is True
    
    def test_non_owner_cannot_access(self):
        """Non-owner should not access private assets."""
        asset = MockAsset(access_level=AccessLevel.PRIVATE)
        user_claims = {"user_id": "other-user-id", "institution": "METRO_Finland"}
        
        with pytest.raises(ForbiddenException):
            check_asset_access(asset, user_claims)


class TestGroupAccess:
    """Tests for group access level."""
    
    def test_authorized_user_can_access(self):
        """User in authorized list should access."""
        asset = MockAsset(
            access_level=AccessLevel.GROUP,
            authorized_users=["user-1", "user-2"],
        )
        user_claims = {"user_id": "user-1", "institution": "OTHER"}
        
        result = check_asset_access(asset, user_claims)
        assert result is True
    
    def test_authorized_institution_can_access(self):
        """Institution in authorized list should access."""
        asset = MockAsset(
            access_level=AccessLevel.GROUP,
            authorized_institutions=["METRO_Finland", "OTHER"],
        )
        user_claims = {"user_id": "random-user", "institution": "METRO_Finland"}
        
        result = check_asset_access(asset, user_claims)
        assert result is True
    
    def test_unauthorized_cannot_access(self):
        """Unauthorized user/institution should not access."""
        asset = MockAsset(
            access_level=AccessLevel.GROUP,
            authorized_users=["user-1"],
            authorized_institutions=["INST-1"],
        )
        user_claims = {"user_id": "user-2", "institution": "INST-2"}
        
        with pytest.raises(ForbiddenException):
            check_asset_access(asset, user_claims)


class TestInstitutionAccess:
    """Tests for institution access level."""
    
    def test_same_institution_can_access(self):
        """Same institution members should access."""
        asset = MockAsset(access_level=AccessLevel.INSTITUTION)
        user_claims = {"user_id": "any-user", "institution": "METRO_Finland"}
        
        result = check_asset_access(asset, user_claims)
        assert result is True
    
    def test_different_institution_cannot_access(self):
        """Different institution members should not access."""
        asset = MockAsset(access_level=AccessLevel.INSTITUTION)
        user_claims = {"user_id": "any-user", "institution": "OTHER_Institution"}
        
        with pytest.raises(ForbiddenException):
            check_asset_access(asset, user_claims)


class TestConsortiumAccess:
    """Tests for consortium access level."""
    
    def test_consortium_member_can_access(self):
        """DTRIP4H consortium members should access."""
        asset = MockAsset(access_level=AccessLevel.CONSORTIUM)
        user_claims = {
            "user_id": "any-user",
            "institution": "ANY",
            "is_consortium_member": True,
        }
        
        result = check_asset_access(asset, user_claims)
        assert result is True
    
    def test_non_member_cannot_access(self):
        """Non-consortium members should not access."""
        asset = MockAsset(access_level=AccessLevel.CONSORTIUM)
        user_claims = {
            "user_id": "any-user",
            "institution": "ANY",
            "is_consortium_member": False,
        }
        
        with pytest.raises(ForbiddenException):
            check_asset_access(asset, user_claims)


class TestApprovalRequiredAccess:
    """Tests for approval-required access level."""
    
    def test_approved_user_can_access(self):
        """Approved users should access."""
        asset = MockAsset(
            access_level=AccessLevel.APPROVAL_REQUIRED,
            authorized_users=["approved-user"],
        )
        user_claims = {"user_id": "approved-user", "institution": "ANY"}
        
        result = check_asset_access(asset, user_claims)
        assert result is True
    
    def test_unapproved_user_cannot_access(self):
        """Unapproved users should not access."""
        asset = MockAsset(
            access_level=AccessLevel.APPROVAL_REQUIRED,
            authorized_users=["other-user"],
        )
        user_claims = {"user_id": "unapproved-user", "institution": "ANY"}
        
        with pytest.raises(ForbiddenException):
            check_asset_access(asset, user_claims)


class TestPublicAccess:
    """Tests for public access level."""
    
    def test_any_authenticated_user_can_access(self):
        """Any authenticated user should access public assets."""
        asset = MockAsset(access_level=AccessLevel.PUBLIC)
        user_claims = {"user_id": "any-user", "institution": "ANY"}
        
        result = check_asset_access(asset, user_claims)
        assert result is True


class TestEmbargo:
    """Tests for embargo functionality."""
    
    def test_embargo_blocks_non_owner(self):
        """Embargoed assets should block non-owners."""
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        asset = MockAsset(
            access_level=AccessLevel.PUBLIC,
            embargo_until=future_date,
        )
        user_claims = {"user_id": "other-user", "institution": "ANY"}
        
        with pytest.raises(ForbiddenException):
            check_asset_access(asset, user_claims)
    
    def test_owner_can_access_during_embargo(self):
        """Owner should access during embargo."""
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        asset = MockAsset(
            access_level=AccessLevel.PUBLIC,
            embargo_until=future_date,
        )
        user_claims = {"user_id": "owner-user-id", "institution": "METRO_Finland"}
        
        result = check_asset_access(asset, user_claims)
        assert result is True


class TestModifyPermissions:
    """Tests for modification permissions."""
    
    def test_owner_can_modify(self):
        """Owner should be able to modify."""
        asset = MockAsset()
        user_claims = {"user_id": "owner-user-id"}
        
        result = can_modify_asset(asset, user_claims)
        assert result is True
    
    def test_non_owner_cannot_modify(self):
        """Non-owner should not modify."""
        asset = MockAsset()
        user_claims = {"user_id": "other-user"}
        
        result = can_modify_asset(asset, user_claims)
        assert result is False
