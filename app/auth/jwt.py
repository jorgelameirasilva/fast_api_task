"""
JWT Authentication Implementation
Production-grade JWT token validation and management
"""

from datetime import datetime, timezone
from typing import Optional
from functools import lru_cache
from fastapi import HTTPException, status
import jwt
from jwt import PyJWKClient, InvalidTokenError
from loguru import logger

from app.core.config import settings
from .models import AuthUser


@lru_cache()
def get_jwt_authenticator():
    """Get singleton JWT authenticator instance"""
    return JWTAuthenticator()


class JWTAuthenticator:
    """
    Production-grade JWT Token Authenticator
    Handles token validation, claim verification, and user extraction
    """

    def __init__(self):
        self.jwks_client: Optional[PyJWKClient] = None
        self._initialize_jwks_client()

    def _initialize_jwks_client(self):
        """Initialize JWKS client for token validation"""
        if not settings.APIM_ONELOGIN_URL:
            logger.warning(
                "APIM_ONELOGIN_URL not configured - JWT validation will fail"
            )
            return

        try:
            self.jwks_client = PyJWKClient(settings.APIM_ONELOGIN_URL)
            logger.info("JWKS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize JWKS client: {e}")

    def validate_and_extract_user(self, token: str) -> AuthUser:
        """
        Validate JWT token and extract user information

        Args:
            token: JWT token string

        Returns:
            AuthUser: Structured user information from token

        Raises:
            HTTPException: If token is invalid or expired
        """
        if not self.jwks_client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # Decode and validate token
            decoded_payload = self._decode_token(token)

            # Validate claims
            self._validate_claims(decoded_payload)

            # Convert to structured user model
            return AuthUser.from_jwt_payload(decoded_payload)

        except InvalidTokenError as e:
            logger.error(f"JWT validation failed: {e}")
            self._handle_jwt_error(e)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error",
            )

    def _decode_token(self, token: str) -> dict:
        """Decode JWT token using JWKS"""
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=settings.JWT_ALGORITHMS,
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )

    def _validate_claims(self, payload: dict):
        """Validate JWT claims"""
        current_timestamp = int(datetime.now(timezone.utc).timestamp())

        # Check expiration
        if payload.get("exp", 0) < current_timestamp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate issuer
        if payload.get("iss") != settings.JWT_ISSUER:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token contains Invalid Issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate audience
        if payload.get("aud") != settings.JWT_AUDIENCE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token contains Invalid Audience",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _handle_jwt_error(self, error: InvalidTokenError):
        """Handle specific JWT validation errors with appropriate HTTP responses"""
        error_str = str(error).lower()

        error_map = {
            "invalid_header": "Authorization header must start with Bearer",
            "invalid_issuer": "Token contains Invalid Issuer",
            "invalid_audience": "Token contains Invalid Audience",
            "expired": "Token has expired",
        }

        detail = next(
            (msg for key, msg in error_map.items() if key in error_str),
            "Token not found",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
