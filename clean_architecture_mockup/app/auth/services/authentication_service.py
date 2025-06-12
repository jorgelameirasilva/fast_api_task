"""
Authentication Service
Domain service for authentication and authorization logic
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status

from ..repositories.jwt_repository import JWTRepository
from ..models import (
    AuthUser,
    AuthContext,
    TokenValidationRequest,
    TokenValidationResult,
)

logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Domain service for authentication and authorization

    Handles JWT token validation, user extraction, and authorization checks
    following clean architecture principles.
    """

    def __init__(self, jwt_repository: JWTRepository):
        self.jwt_repository = jwt_repository
        logger.info("Initialized AuthenticationService")

    async def authenticate_user(
        self, token: str, request_id: Optional[str] = None
    ) -> AuthContext:
        """
        Authenticate user from JWT token

        Args:
            token: JWT token string
            request_id: Optional request ID for tracking

        Returns:
            AuthContext: Authentication context with user info

        Raises:
            HTTPException: If authentication fails
        """
        logger.debug(f"Authenticating user with token: {token[:20]}...")

        try:
            # Validate token using repository
            validation_request = TokenValidationRequest(token=token)
            result = await self.jwt_repository.validate_token(validation_request)

            if result.is_valid and result.user:
                logger.info(f"User authenticated: {result.user.user_id}")
                return AuthContext.authenticated(result.user, request_id=request_id)
            else:
                logger.warning(f"Authentication failed: {result.error_message}")
                self._handle_authentication_error(result)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def authenticate_optional(
        self, token: Optional[str], request_id: Optional[str] = None
    ) -> AuthContext:
        """
        Optional authentication - returns anonymous context if no token or invalid token

        Args:
            token: Optional JWT token string
            request_id: Optional request ID for tracking

        Returns:
            AuthContext: Authenticated or anonymous context
        """
        if not token:
            return AuthContext.anonymous(request_id=request_id)

        try:
            return await self.authenticate_user(token, request_id)
        except HTTPException:
            # For optional auth, return anonymous context instead of raising
            logger.debug("Optional authentication failed, returning anonymous context")
            return AuthContext.anonymous(request_id=request_id)

    async def authorize_roles(
        self, auth_context: AuthContext, required_roles: List[str]
    ) -> None:
        """
        Check if authenticated user has required roles

        Args:
            auth_context: Authentication context
            required_roles: List of required roles

        Raises:
            HTTPException: If user doesn't have required roles
        """
        if not auth_context.is_authenticated or not auth_context.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not auth_context.user.has_any_role(required_roles):
            logger.warning(
                f"Authorization failed for user {auth_context.user.user_id}: "
                f"required roles {required_roles}, user roles {auth_context.user.roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}",
            )

        logger.debug(
            f"Role authorization successful for user {auth_context.user.user_id}"
        )

    async def authorize_scope(
        self, auth_context: AuthContext, required_scope: str
    ) -> None:
        """
        Check if authenticated user has required scope

        Args:
            auth_context: Authentication context
            required_scope: Required OAuth scope

        Raises:
            HTTPException: If user doesn't have required scope
        """
        if not auth_context.is_authenticated or not auth_context.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not auth_context.user.has_scope(required_scope):
            logger.warning(
                f"Scope authorization failed for user {auth_context.user.user_id}: "
                f"required scope '{required_scope}', user scopes '{auth_context.user.scope}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required scope '{required_scope}' not found",
            )

        logger.debug(
            f"Scope authorization successful for user {auth_context.user.user_id}"
        )

    async def authorize_all_roles(
        self, auth_context: AuthContext, required_roles: List[str]
    ) -> None:
        """
        Check if authenticated user has ALL required roles

        Args:
            auth_context: Authentication context
            required_roles: List of roles (all required)

        Raises:
            HTTPException: If user doesn't have all required roles
        """
        if not auth_context.is_authenticated or not auth_context.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        missing_roles = [
            role for role in required_roles if not auth_context.user.has_role(role)
        ]
        if missing_roles:
            logger.warning(
                f"Authorization failed for user {auth_context.user.user_id}: "
                f"missing roles {missing_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {', '.join(missing_roles)}",
            )

        logger.debug(
            f"All roles authorization successful for user {auth_context.user.user_id}"
        )

    def _handle_authentication_error(self, result: TokenValidationResult) -> None:
        """Handle authentication errors with appropriate HTTP responses"""
        error_code = result.error_code or "UNKNOWN_ERROR"
        error_message = result.error_message or "Authentication failed"

        # Map error codes to HTTP status codes and messages
        error_map = {
            "TOKEN_EXPIRED": (status.HTTP_401_UNAUTHORIZED, "Token has expired"),
            "INVALID_TOKEN": (status.HTTP_401_UNAUTHORIZED, "Invalid token"),
            "INVALID_ISSUER": (
                status.HTTP_401_UNAUTHORIZED,
                "Token contains invalid issuer",
            ),
            "INVALID_AUDIENCE": (
                status.HTTP_401_UNAUTHORIZED,
                "Token contains invalid audience",
            ),
            "JWKS_CLIENT_UNAVAILABLE": (
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Authentication service unavailable",
            ),
            "VALIDATION_ERROR": (
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Token validation error",
            ),
        }

        status_code, detail = error_map.get(
            error_code, (status.HTTP_401_UNAUTHORIZED, error_message)
        )

        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def get_user_context(self, auth_context: AuthContext) -> Dict[str, Any]:
        """
        Get user context for logging and audit purposes

        Args:
            auth_context: Authentication context

        Returns:
            Dict with user context information
        """
        if not auth_context.is_authenticated or not auth_context.user:
            return {"authenticated": False, "user_id": None, "roles": [], "scopes": []}

        return {
            "authenticated": True,
            "user_id": auth_context.user.user_id,
            "email": auth_context.user.email,
            "roles": auth_context.user.roles,
            "groups": auth_context.user.groups,
            "scopes": (
                auth_context.user.scope.split() if auth_context.user.scope else []
            ),
            "auth_method": auth_context.auth_method,
        }

    async def health_check(self) -> Dict[str, str]:
        """Check authentication service health"""
        try:
            jwt_health = await self.jwt_repository.health_check()
            return {
                "service": "AuthenticationService",
                "status": (
                    "healthy" if jwt_health.get("status") == "healthy" else "degraded"
                ),
                "jwt_repository": jwt_health.get("status", "unknown"),
            }
        except Exception as e:
            return {
                "service": "AuthenticationService",
                "status": "unhealthy",
                "error": str(e),
            }
