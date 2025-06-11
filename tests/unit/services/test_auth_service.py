import pytest
from unittest.mock import patch, Mock
from app.services.auth_service import AuthService


class TestAuthService:
    """Unit tests for AuthService"""

    @pytest.mark.asyncio
    async def test_get_auth_setup_jwt_enabled(self):
        """Test getting auth setup configuration when JWT is enabled"""
        # Arrange
        auth_service = AuthService()

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.APIM_ONELOGIN_URL = (
                "https://example.com/.well-known/jwks.json"
            )
            mock_settings.APIM_BASE_URL = "https://api.example.com"

            # Act
            result = await auth_service.get_auth_setup()

            # Assert
            assert hasattr(result, "auth_enabled")
            assert hasattr(result, "auth_type")
            assert hasattr(result, "login_url")
            assert hasattr(result, "logout_url")
            assert result.auth_enabled is True
            assert result.auth_type == "JWT"
            assert result.login_url is not None
            # logout_url is currently None in the implementation
            assert result.logout_url is None

    @pytest.mark.asyncio
    async def test_get_auth_setup_jwt_disabled(self):
        """Test getting auth setup configuration when JWT is disabled"""
        # Arrange
        auth_service = AuthService()

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.APIM_ONELOGIN_URL = ""
            mock_settings.APIM_BASE_URL = ""

            # Act
            result = await auth_service.get_auth_setup()

            # Assert
            assert result.auth_enabled is False
            assert result.auth_type == "none"
            assert result.login_url is None
            assert result.logout_url is None

    @pytest.mark.asyncio
    async def test_get_auth_setup_partial_config(self):
        """Test auth setup with partial JWT configuration"""
        # Arrange
        auth_service = AuthService()

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.APIM_ONELOGIN_URL = (
                "https://example.com/.well-known/jwks.json"
            )
            mock_settings.APIM_BASE_URL = ""  # Missing base URL

            # Act
            result = await auth_service.get_auth_setup()

            # Assert
            assert result.auth_enabled is True  # Still enabled if JWKS URL is present
            assert result.auth_type == "JWT"
            # URLs should handle missing base URL gracefully
