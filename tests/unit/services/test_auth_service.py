import pytest
from unittest.mock import patch

from app.services.auth_service import AuthService
from app.schemas.chat import AuthSetupResponse


class TestAuthService:
    """Unit tests for AuthService"""

    @pytest.mark.asyncio
    async def test_get_auth_setup_disabled(self, auth_service):
        """Test getting auth setup when authentication is disabled"""
        # Arrange
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.AUTH_ENABLED = False

            # Act
            response = await auth_service.get_auth_setup()

            # Assert
            assert isinstance(response, AuthSetupResponse)
            assert response.auth_enabled is False
            assert response.auth_type == "none"
            assert response.login_url is None
            assert response.logout_url is None

    @pytest.mark.asyncio
    async def test_get_auth_setup_enabled(self, auth_service):
        """Test getting auth setup when authentication is enabled"""
        # Arrange
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.AUTH_ENABLED = True

            # Act
            response = await auth_service.get_auth_setup()

            # Assert
            assert isinstance(response, AuthSetupResponse)
            assert response.auth_enabled is True
            assert response.auth_type == "azure_ad"
            assert response.login_url == "/login"
            assert response.logout_url == "/logout"

    @pytest.mark.asyncio
    async def test_validate_auth_claims_disabled(self, auth_service):
        """Test validating auth claims when authentication is disabled"""
        # Arrange
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.AUTH_ENABLED = False

            # Act
            result = await auth_service.validate_auth_claims({"user": "test"})

            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_auth_claims_enabled_valid(self, auth_service):
        """Test validating valid auth claims when authentication is enabled"""
        # Arrange
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.AUTH_ENABLED = True
            claims = {"sub": "user123", "email": "user@example.com"}

            # Act
            result = await auth_service.validate_auth_claims(claims)

            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_auth_claims_enabled_none(self, auth_service):
        """Test validating None claims when authentication is enabled"""
        # Arrange
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.AUTH_ENABLED = True

            # Act
            result = await auth_service.validate_auth_claims(None)

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_auth_claims_enabled_empty(self, auth_service):
        """Test validating empty claims when authentication is enabled"""
        # Arrange
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.AUTH_ENABLED = True

            # Act
            result = await auth_service.validate_auth_claims({})

            # Assert
            assert result is True  # Empty dict is considered valid

    @pytest.mark.asyncio
    async def test_extract_user_info_none_claims(self, auth_service):
        """Test extracting user info from None claims"""
        # Act
        user_info = await auth_service.extract_user_info(None)

        # Assert
        assert user_info == {}

    @pytest.mark.asyncio
    async def test_extract_user_info_empty_claims(self, auth_service):
        """Test extracting user info from empty claims"""
        # Act
        user_info = await auth_service.extract_user_info({})

        # Assert - Empty dict is considered falsy, so returns empty dict
        assert user_info == {}

    @pytest.mark.asyncio
    async def test_extract_user_info_full_claims(self, auth_service):
        """Test extracting user info from complete claims"""
        # Arrange
        claims = {
            "sub": "user123",
            "email": "user@example.com",
            "name": "John Doe",
            "roles": ["admin", "user"],
        }

        # Act
        user_info = await auth_service.extract_user_info(claims)

        # Assert
        assert user_info == {
            "user_id": "user123",
            "email": "user@example.com",
            "name": "John Doe",
            "roles": ["admin", "user"],
        }

    @pytest.mark.asyncio
    async def test_extract_user_info_partial_claims(self, auth_service):
        """Test extracting user info from partial claims"""
        # Arrange
        claims = {
            "sub": "user456",
            "email": "partial@example.com",
            # Missing name and roles
        }

        # Act
        user_info = await auth_service.extract_user_info(claims)

        # Assert
        assert user_info == {
            "user_id": "user456",
            "email": "partial@example.com",
            "name": None,
            "roles": [],
        }

    @pytest.mark.asyncio
    async def test_extract_user_info_missing_sub(self, auth_service):
        """Test extracting user info when 'sub' is missing"""
        # Arrange
        claims = {"email": "nosub@example.com", "name": "No Sub User"}

        # Act
        user_info = await auth_service.extract_user_info(claims)

        # Assert
        assert user_info == {
            "user_id": "anonymous",
            "email": "nosub@example.com",
            "name": "No Sub User",
            "roles": [],
        }

    @pytest.mark.asyncio
    async def test_extract_user_info_various_role_formats(self, auth_service):
        """Test extracting user info with various role formats"""
        # Test with string roles
        claims_string_roles = {
            "sub": "user789",
            "roles": "admin,user",  # String instead of list
        }

        user_info = await auth_service.extract_user_info(claims_string_roles)
        assert user_info["roles"] == "admin,user"  # Should preserve the format

        # Test with None roles
        claims_none_roles = {"sub": "user790", "roles": None}

        user_info = await auth_service.extract_user_info(claims_none_roles)
        assert user_info["roles"] is None  # Should preserve None value

    @pytest.mark.asyncio
    async def test_auth_service_instance_isolation(self):
        """Test that different AuthService instances work independently"""
        # Arrange
        service1 = AuthService()
        service2 = AuthService()

        # Act & Assert - Both should work independently
        response1 = await service1.get_auth_setup()
        response2 = await service2.get_auth_setup()

        assert isinstance(response1, AuthSetupResponse)
        assert isinstance(response2, AuthSetupResponse)
        # Both should have same behavior but be separate instances
        assert response1.auth_enabled == response2.auth_enabled

    @pytest.mark.asyncio
    async def test_extract_user_info_special_characters(self, auth_service):
        """Test extracting user info with special characters"""
        # Arrange
        claims = {
            "sub": "user-with-special@chars.com",
            "email": "spëcial.usér+tag@dömain.com",
            "name": "José María García-López",
            "roles": ["admin-role", "user_role", "role.with.dots"],
        }

        # Act
        user_info = await auth_service.extract_user_info(claims)

        # Assert
        assert user_info["user_id"] == "user-with-special@chars.com"
        assert user_info["email"] == "spëcial.usér+tag@dömain.com"
        assert user_info["name"] == "José María García-López"
        assert user_info["roles"] == ["admin-role", "user_role", "role.with.dots"]

    @pytest.mark.asyncio
    async def test_auth_setup_response_structure(self, auth_service):
        """Test that auth setup response has correct structure"""
        # Act
        response = await auth_service.get_auth_setup()

        # Assert
        assert hasattr(response, "auth_enabled")
        assert hasattr(response, "auth_type")
        assert hasattr(response, "login_url")
        assert hasattr(response, "logout_url")
        assert isinstance(response.auth_enabled, bool)
        assert isinstance(response.auth_type, str)
        # login_url and logout_url can be None or str
