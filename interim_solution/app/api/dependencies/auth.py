"""Authentication dependencies for FastAPI"""

import logging
from typing import Dict, Any
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.authentication import AuthenticationHelper, AuthError


logger = logging.getLogger(__name__)

# Global authentication helper instance
auth_helper = AuthenticationHelper(
    use_authentication=settings.azure_use_authentication,
    server_app_id=settings.azure_server_app_id,
    server_app_secret=settings.azure_server_app_secret,
    client_app_id=settings.azure_client_app_id,
    tenant_id=settings.azure_tenant_id,
    token_cache_path=settings.token_cache_path,
)


async def get_auth_claims(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency to get authentication claims from request headers

    Returns:
        Dict containing user authentication claims

    Raises:
        HTTPException: If authentication is enabled and token validation fails
    """
    try:
        # Get headers from FastAPI request
        headers = dict(request.headers)

        # Use the authentication helper to get claims
        auth_claims = await auth_helper.get_auth_claims_if_enabled(headers)

        return auth_claims

    except AuthError as e:
        logger.error(f"Authentication error: {e.error}")
        raise HTTPException(status_code=e.status_code, detail=e.error)
    except Exception as e:
        logger.error(f"Unexpected authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


async def validate_jwt_token(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency that validates JWT tokens with comprehensive checks

    Returns:
        Dict containing decoded JWT token claims

    Raises:
        HTTPException: If token validation fails
    """
    if not auth_helper.use_authentication:
        return {}

    try:
        # Validate JWT token from request
        decoded_token = await auth_helper.validate_token_from_request(request)
        return decoded_token

    except AuthError as e:
        logger.error(f"JWT validation error: {e.error}")
        raise HTTPException(status_code=e.status_code, detail=e.error)
    except Exception as e:
        logger.error(f"Unexpected JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation failed"
        )


async def require_auth(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency for routes that require authentication

    This dependency will:
    1. Validate JWT token if authentication is enabled
    2. Extract user claims
    3. Raise HTTPException if authentication fails

    Returns:
        Dict containing user authentication claims
    """
    return await get_auth_claims(request)


async def require_jwt_auth(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency for routes that require strict JWT authentication

    This dependency will:
    1. Always validate JWT token structure and signatures
    2. Check expiration, issuer, and audience
    3. Raise HTTPException if any validation fails

    Returns:
        Dict containing decoded JWT token claims
    """
    return await validate_jwt_token(request)


async def optional_auth(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency for routes with optional authentication

    This dependency will:
    1. Try to get auth claims if headers are present
    2. Return empty dict if no authentication headers
    3. Not raise exceptions for missing authentication

    Returns:
        Dict containing user authentication claims or empty dict
    """
    try:
        return await get_auth_claims(request)
    except HTTPException:
        # Return empty claims if authentication fails
        return {}


# Alias the functions for backward compatibility
RequireAuth = require_auth
RequireJWTAuth = require_jwt_auth
OptionalAuth = optional_auth
