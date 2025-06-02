from loguru import logger

from app.schemas.chat import AuthSetupResponse
from app.core.config import settings


class AuthService:
    """Service focused solely on authentication operations"""

    async def get_auth_setup(self) -> AuthSetupResponse:
        """Get authentication setup configuration"""
        logger.info("Getting auth setup configuration")

        return AuthSetupResponse(
            auth_enabled=settings.AUTH_ENABLED,
            auth_type="none" if not settings.AUTH_ENABLED else "azure_ad",
            login_url="/login" if settings.AUTH_ENABLED else None,
            logout_url="/logout" if settings.AUTH_ENABLED else None,
        )

    async def validate_auth_claims(self, claims: dict) -> bool:
        """Validate authentication claims"""
        if not settings.AUTH_ENABLED:
            return True

        # Add your authentication validation logic here
        # For now, return True as placeholder
        return claims is not None

    async def extract_user_info(self, claims: dict) -> dict:
        """Extract user information from auth claims"""
        if not claims:
            return {}

        # Extract relevant user information from claims
        # This would depend on your authentication provider
        return {
            "user_id": claims.get("sub", "anonymous"),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "roles": claims.get("roles", []),
        }


# Create singleton instance
auth_service = AuthService()
