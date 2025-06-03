from loguru import logger
from app.schemas.chat import AuthSetupResponse


class AuthService:
    """Service focused solely on authentication operations"""

    async def get_auth_setup(self) -> AuthSetupResponse:
        """Get authentication setup configuration - simplified for now"""
        logger.info("Getting auth setup configuration")

        # Simple auth configuration - authentication disabled for now
        return AuthSetupResponse(
            auth_enabled=False,
            auth_type="none",
            login_url=None,
            logout_url=None,
        )


# Create singleton instance
auth_service = AuthService()
