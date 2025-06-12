"""
JWT Repository
Abstracts JWT token validation and user extraction following repository pattern
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import logging
import uuid

from ..models import AuthUser, TokenValidationRequest, TokenValidationResult

logger = logging.getLogger(__name__)


class JWTRepository(ABC):
    """Abstract JWT repository interface"""

    @abstractmethod
    async def validate_token(
        self, request: TokenValidationRequest
    ) -> TokenValidationResult:
        """Validate JWT token and extract user information"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, str]:
        """Check repository health status"""
        pass


class ProductionJWTRepository(JWTRepository):
    """Production JWT repository using PyJWT and JWKS"""

    def __init__(self):
        self.jwks_client: Optional[Any] = None
        self._initialize_jwks_client()
        logger.info("Initialized Production JWT Repository")

    def _initialize_jwks_client(self):
        """Initialize JWKS client for token validation"""
        try:
            # Import here to avoid dependency issues in development
            from jwt import PyJWKClient
            from app.core.config import get_settings

            settings = get_settings()

            if not settings.APIM_ONELOGIN_URL:
                logger.warning(
                    "APIM_ONELOGIN_URL not configured - JWT validation will fail"
                )
                return

            self.jwks_client = PyJWKClient(settings.APIM_ONELOGIN_URL)
            logger.info("JWKS client initialized successfully")

        except ImportError:
            logger.warning("PyJWT not available - falling back to mock repository")
        except Exception as e:
            logger.error(f"Failed to initialize JWKS client: {e}")

    async def validate_token(
        self, request: TokenValidationRequest
    ) -> TokenValidationResult:
        """Validate JWT token using production JWKS"""
        if not self.jwks_client:
            return TokenValidationResult(
                is_valid=False,
                error_code="JWKS_CLIENT_UNAVAILABLE",
                error_message="JWKS client not available",
                validation_metadata={
                    "repository": "production",
                    "jwks_configured": False,
                },
            )

        try:
            import jwt
            from app.core.config import get_settings

            settings = get_settings()

            # Get signing key
            signing_key = self.jwks_client.get_signing_key_from_jwt(request.token)

            # Decode token
            payload = jwt.decode(
                request.token,
                signing_key.key,
                algorithms=settings.JWT_ALGORITHMS,
                audience=settings.JWT_AUDIENCE if request.validate_audience else None,
                issuer=settings.JWT_ISSUER if request.validate_issuer else None,
                options={
                    "verify_exp": request.validate_expiry,
                    "verify_aud": request.validate_audience,
                    "verify_iss": request.validate_issuer,
                },
            )

            # Additional claims validation
            if request.validate_expiry:
                current_timestamp = int(datetime.now(timezone.utc).timestamp())
                if payload.get("exp", 0) < current_timestamp:
                    return TokenValidationResult(
                        is_valid=False,
                        error_code="TOKEN_EXPIRED",
                        error_message="Token has expired",
                        validation_metadata={
                            "exp": payload.get("exp"),
                            "current": current_timestamp,
                        },
                    )

            # Create user from payload
            user = AuthUser.from_jwt_payload(payload)

            return TokenValidationResult(
                is_valid=True,
                user=user,
                validation_metadata={
                    "repository": "production",
                    "algorithm": payload.get("alg", "unknown"),
                    "issuer": payload.get("iss"),
                    "audience": payload.get("aud"),
                },
            )

        except jwt.InvalidTokenError as e:
            logger.error(f"JWT validation failed: {e}")
            return TokenValidationResult(
                is_valid=False,
                error_code="INVALID_TOKEN",
                error_message=str(e),
                validation_metadata={"repository": "production", "jwt_error": str(e)},
            )
        except Exception as e:
            logger.error(f"Unexpected JWT validation error: {e}")
            return TokenValidationResult(
                is_valid=False,
                error_code="VALIDATION_ERROR",
                error_message="Unexpected validation error",
                validation_metadata={"repository": "production", "error": str(e)},
            )

    async def health_check(self) -> Dict[str, str]:
        """Check production JWT repository health"""
        try:
            if self.jwks_client:
                return {
                    "status": "healthy",
                    "service": "Production JWT Repository",
                    "jwks": "configured",
                }
            else:
                return {
                    "status": "degraded",
                    "service": "Production JWT Repository",
                    "jwks": "not_configured",
                }
        except Exception:
            return {"status": "unhealthy", "service": "Production JWT Repository"}


class MockJWTRepository(JWTRepository):
    """Mock JWT repository for development and testing"""

    def __init__(self):
        self.mock_users = self._create_mock_users()
        logger.info("Initialized Mock JWT Repository")

    def _create_mock_users(self) -> Dict[str, AuthUser]:
        """Create mock users for development/testing"""
        return {
            "mock-token-admin": AuthUser(
                user_id="admin-123",
                email="admin@example.com",
                name="Mock Admin User",
                preferred_username="admin",
                roles=["admin", "user"],
                groups=["administrators", "users"],
                scope="read write admin",
                issued_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc).replace(year=2030),
            ),
            "mock-token-user": AuthUser(
                user_id="user-456",
                email="user@example.com",
                name="Mock Regular User",
                preferred_username="user",
                roles=["user"],
                groups=["users"],
                scope="read write",
                issued_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc).replace(year=2030),
            ),
            "mock-token-readonly": AuthUser(
                user_id="readonly-789",
                email="readonly@example.com",
                name="Mock Readonly User",
                preferred_username="readonly",
                roles=["readonly"],
                groups=["readonly_users"],
                scope="read",
                issued_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc).replace(year=2030),
            ),
        }

    async def validate_token(
        self, request: TokenValidationRequest
    ) -> TokenValidationResult:
        """Validate mock JWT tokens"""
        token = request.token

        # Check for mock tokens
        if token in self.mock_users:
            user = self.mock_users[token]

            # Simulate expiry check if requested
            if request.validate_expiry and user.expires_at:
                if user.expires_at < datetime.now(timezone.utc):
                    return TokenValidationResult(
                        is_valid=False,
                        error_code="TOKEN_EXPIRED",
                        error_message="Mock token has expired",
                        validation_metadata={"repository": "mock", "token": token},
                    )

            return TokenValidationResult(
                is_valid=True,
                user=user,
                validation_metadata={
                    "repository": "mock",
                    "token": token,
                    "mock_user": True,
                },
            )

        # Handle special test cases
        if token == "expired-token":
            return TokenValidationResult(
                is_valid=False,
                error_code="TOKEN_EXPIRED",
                error_message="Token has expired",
                validation_metadata={"repository": "mock", "test_case": "expired"},
            )

        if token == "invalid-issuer":
            return TokenValidationResult(
                is_valid=False,
                error_code="INVALID_ISSUER",
                error_message="Token contains invalid issuer",
                validation_metadata={
                    "repository": "mock",
                    "test_case": "invalid_issuer",
                },
            )

        if token == "invalid-audience":
            return TokenValidationResult(
                is_valid=False,
                error_code="INVALID_AUDIENCE",
                error_message="Token contains invalid audience",
                validation_metadata={
                    "repository": "mock",
                    "test_case": "invalid_audience",
                },
            )

        # Default case - invalid token
        return TokenValidationResult(
            is_valid=False,
            error_code="INVALID_TOKEN",
            error_message="Mock token not found",
            validation_metadata={"repository": "mock", "token": token},
        )

    async def health_check(self) -> Dict[str, str]:
        """Mock health check always returns healthy"""
        return {
            "status": "healthy",
            "service": "Mock JWT Repository",
            "mock_users": str(len(self.mock_users)),
        }

    def get_mock_tokens(self) -> Dict[str, str]:
        """Get available mock tokens for testing"""
        return {
            role: token
            for token, user in self.mock_users.items()
            for role in user.roles
        }

    def create_custom_mock_user(self, token: str, user: AuthUser) -> None:
        """Add custom mock user for testing"""
        self.mock_users[token] = user
        logger.info(f"Added custom mock user with token: {token}")
