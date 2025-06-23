"""Authentication dependencies for FastAPI"""

import logging
import os
import time
import datetime
from typing import Dict, Any
from fastapi import Depends, HTTPException, Request
from jwt import PyJWKClient
import jwt

from app.core.config import settings
from app.core.authentication import AuthenticationHelper, AuthError

logger = logging.getLogger(__name__)

# Global authentication helper instance
_auth_helper: AuthenticationHelper | None = None


def get_auth_helper() -> AuthenticationHelper:
    """Get or create authentication helper instance"""
    global _auth_helper
    if _auth_helper is None:
        use_authentication = bool(int(os.environ.get("REQUIRE_AUTHENTICATION", 1)))
        _auth_helper = AuthenticationHelper(
            use_authentication=use_authentication,
            server_app_id=settings.azure_server_app_id or "default",
            server_app_secret=settings.azure_server_app_secret or "default",
            client_app_id=settings.azure_client_app_id or "default",
            tenant_id=settings.azure_tenant_id or "default",
            token_cache_path=settings.token_cache_path,
        )
    return _auth_helper


async def require_user(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency to require authenticated user
    Replicates the exact same logic as the old token_required decorator
    """
    REQUIRE_AUTHENTICATION = int(os.environ.get("REQUIRE_AUTHENTICATION", 1))

    if REQUIRE_AUTHENTICATION:
        AUDIENCE = os.environ.get("APP_AUTHENTICATION_CLIENT_ID", None)
        ISSUER = "https://login.microsoftonline.com/53b7cac7-14be-46d4-be43-f2ad9244d901/v2.0"
        JWKS_URL = f"https://login.microsoftonline.com/53b7cac7-14be-46d4-be43-f2ad9244d901/discovery/v2.0/keys"

        now = datetime.datetime.now()
        current_timestamp = int(now.timestamp())

        auth = request.headers.get("Authorization", None)
        if not auth:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "authorization_header_missing",
                    "description": "Authorization header is expected",
                },
            )

        parts = auth.split()
        if parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "invalid_header",
                    "description": "Authorization header must start with Bearer",
                },
            )
        elif len(parts) == 1:
            raise HTTPException(
                status_code=401,
                detail={"code": "invalid_header", "description": "Token not found"},
            )
        elif len(parts) > 2:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "invalid_header",
                    "description": "Authorization header must be a bearer token",
                },
            )

        token = auth.split()[-1].strip()
        jwk_client = PyJWKClient(JWKS_URL)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )

        if decoded_token["iss"] != ISSUER:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "invalid_issuer",
                    "description": "Token contains Invalid Issuer",
                },
            )

        if decoded_token["aud"] != AUDIENCE:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "invalid_audience",
                    "description": "Token contains Invalid Audience",
                },
            )

        if decoded_token["exp"] < current_timestamp:
            raise HTTPException(status_code=401, detail="Token has expired")

    # After JWT validation (or if auth disabled), get auth claims using MSAL On-Behalf-Of flow
    try:
        # Get the authentication helper instance
        auth_helper = get_auth_helper()

        # Get headers from request
        headers = dict(request.headers)

        # Use the exact same auth claims logic as old repo
        auth_claims = await auth_helper.get_auth_claims_if_enabled(headers)

        return auth_claims

    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.error)
    except Exception as e:
        logging.exception("Error getting current user")
        raise HTTPException(
            status_code=401,
            detail={
                "code": "authentication_error",
                "description": f"Authentication error: {str(e)}",
            },
        )


# Alias for backward compatibility
async def get_current_user(request: Request) -> Dict[str, Any]:
    """Alias for require_user for backward compatibility"""
    return await require_user(request)


def get_auth_setup() -> Dict[str, Any]:
    """
    Get authentication setup for client-side configuration
    Uses exactly the same logic as the old repo
    """
    try:
        auth_helper = get_auth_helper()
        return auth_helper.get_auth_setup_for_client()
    except Exception as e:
        logger.error(f"Failed to get auth setup: {str(e)}")
        return {}


# FastAPI dependency alias for use in route decorators
RequireAuth = Depends(require_user)
