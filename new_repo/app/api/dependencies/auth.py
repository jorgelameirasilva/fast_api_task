"""Authentication dependencies for FastAPI"""

import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.authentication import AuthenticationHelper

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

# Global authentication helper instance
auth_helper: Optional[AuthenticationHelper] = None


def get_auth_helper() -> AuthenticationHelper:
    """Get or create authentication helper"""
    global auth_helper
    if auth_helper is None:
        auth_helper = AuthenticationHelper(
            use_authentication=settings.azure_use_authentication,
            server_app_id=settings.azure_server_app_id,
            server_app_secret=settings.azure_server_app_secret,
            client_app_id=settings.azure_client_app_id,
            tenant_id=settings.azure_tenant_id,
            token_cache_path=settings.token_cache_path,
        )
    return auth_helper


async def verify_token(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify Bearer token and return auth claims

    This dependency replicates the @token_required decorator behavior
    from the original Quart application.
    """

    # If authentication is disabled, return empty claims
    if not settings.azure_use_authentication:
        return {}

    # Check for authorization header
    if not credentials:
        logger.warning("Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Get authentication helper
        auth = get_auth_helper()

        # Create headers dict compatible with original auth helper
        headers = dict(request.headers)

        # Get auth claims using the same method as original
        auth_claims = await auth.get_auth_claims_if_enabled(headers)

        logger.info("Token verification successful")
        return auth_claims or {}

    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_auth_claims(request: Request) -> Dict[str, Any]:
    """
    Get authentication claims for the current request

    This is used when you need auth claims but want to handle
    authentication errors differently than the verify_token dependency.
    """
    try:
        # Get authentication helper
        auth = get_auth_helper()

        # Create headers dict compatible with original auth helper
        headers = dict(request.headers)

        # Get auth claims
        auth_claims = await auth.get_auth_claims_if_enabled(headers)
        return auth_claims or {}

    except Exception as e:
        logger.error(f"Failed to get auth claims: {str(e)}")
        return {}


def get_auth_setup() -> Dict[str, Any]:
    """
    Get authentication setup for client-side configuration

    Equivalent to the /auth_setup endpoint from the original app
    """
    try:
        auth = get_auth_helper()
        return auth.get_auth_setup_for_client()
    except Exception as e:
        logger.error(f"Failed to get auth setup: {str(e)}")
        return {}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
) -> dict[str, Any]:
    """
    Get current user from JWT token

    For development/testing, returns a mock user
    In production, this would validate the JWT token
    """
    try:
        # For development/testing - return mock user
        mock_user = {
            "oid": "test-user-123",
            "preferred_username": "test@example.com",
            "name": "Test User",
            "sub": "test-user-123",
        }

        return mock_user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    request: Request,
) -> dict[str, Any] | None:
    """
    Get current user optionally (for endpoints that work with or without auth)
    """
    try:
        # Try to get authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        # For development/testing - return mock user
        mock_user = {
            "oid": "test-user-123",
            "preferred_username": "test@example.com",
            "name": "Test User",
            "sub": "test-user-123",
        }

        return mock_user

    except Exception:
        return None


# Dependency aliases for convenience
RequireAuth = Depends(verify_token)
OptionalAuth = Depends(get_auth_claims)
