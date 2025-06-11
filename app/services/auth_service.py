from loguru import logger
from app.schemas.chat import AuthSetupResponse
from app.core.config import settings


class AuthService:
    """Service focused solely on authentication operations"""

    async def get_auth_setup(self) -> AuthSetupResponse:
        """Get authentication setup configuration"""
        logger.info("Getting auth setup configuration")

        # Check if JWT authentication is properly configured
        auth_enabled = bool(
            settings.APIM_ONELOGIN_URL and settings.JWT_AUDIENCE and settings.JWT_ISSUER
        )

        if auth_enabled:
            return AuthSetupResponse(
                auth_enabled=True,
                auth_type="JWT",
                login_url=settings.APIM_ONELOGIN_URL,
                logout_url=None,  # Could be configured if needed
            )
        else:
            return AuthSetupResponse(
                auth_enabled=False,
                auth_type="none",
                login_url=None,
                logout_url=None,
            )


# Create singleton instance
auth_service = AuthService()
