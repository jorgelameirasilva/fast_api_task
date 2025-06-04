import pytest
from app.services.auth_service import AuthService


class TestAuthService:
    """Unit tests for AuthService"""

    @pytest.mark.asyncio
    async def test_get_auth_setup(self):
        """Test getting auth setup configuration"""
        # Arrange
        auth_service = AuthService()

        # Act
        result = await auth_service.get_auth_setup()

        # Assert
        assert hasattr(result, "auth_enabled")
        assert hasattr(result, "auth_type")
        assert hasattr(result, "login_url")
        assert hasattr(result, "logout_url")
        assert result.auth_enabled is False
        assert result.auth_type == "none"
        assert result.login_url is None
        assert result.logout_url is None
