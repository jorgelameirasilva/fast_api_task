"""
Authentication Dependencies - Clean Architecture Implementation
FastAPI dependencies for JWT authentication and authorization following clean architecture principles
"""

import uuid
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .services.authentication_service import AuthenticationService
from .models import AuthUser, AuthContext

# Security schemes
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def get_authentication_service() -> AuthenticationService:
    """Get authentication service from dependency injection container"""
    from app.core.container import container

    return container.authentication_service()


def get_request_id(request: Request) -> str:
    """Get or generate request ID for tracking"""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def extract_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract and validate token from authorization header"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_current_user(
    token: str = Depends(extract_token),
    auth_service: AuthenticationService = Depends(get_authentication_service),
    request_id: str = Depends(get_request_id),
) -> AuthUser:
    """
    Get authenticated user from JWT token

    This is the primary authentication dependency for protected endpoints.
    """
    auth_context = await auth_service.authenticate_user(token, request_id)

    if not auth_context.is_authenticated or not auth_context.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_context.user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    auth_service: AuthenticationService = Depends(get_authentication_service),
    request_id: str = Depends(get_request_id),
) -> Optional[AuthUser]:
    """
    Get user if authenticated, None otherwise

    Use this for endpoints that work with or without authentication.
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        auth_context = await auth_service.authenticate_user(
            credentials.credentials, request_id
        )
        return auth_context.user if auth_context.is_authenticated else None
    except HTTPException:
        return None


async def get_auth_context(
    user: Optional[AuthUser] = Depends(get_optional_user),
    request_id: str = Depends(get_request_id),
) -> AuthContext:
    """
    Get authentication context for the request

    Provides structured authentication information including user and auth status.
    """
    if user:
        return AuthContext.authenticated(user, request_id=request_id)
    return AuthContext.anonymous(request_id=request_id)


# Authorization dependency factories
def require_roles(required_roles: List[str]):
    """
    Factory for role-based access control

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles(["admin"]))])
        async def admin_endpoint():
            pass
    """

    async def check_roles(
        current_user: AuthUser = Depends(get_current_user),
        auth_service: AuthenticationService = Depends(get_authentication_service),
        request_id: str = Depends(get_request_id),
    ):
        auth_context = AuthContext.authenticated(current_user, request_id)
        await auth_service.authorize_roles(auth_context, required_roles)
        return current_user

    return check_roles


def require_scope(required_scope: str):
    """
    Factory for scope-based access control

    Usage:
        @router.get("/api/data", dependencies=[Depends(require_scope("read:data"))])
        async def protected_data():
            pass
    """

    async def check_scope(
        current_user: AuthUser = Depends(get_current_user),
        auth_service: AuthenticationService = Depends(get_authentication_service),
        request_id: str = Depends(get_request_id),
    ):
        auth_context = AuthContext.authenticated(current_user, request_id)
        await auth_service.authorize_scope(auth_context, required_scope)
        return current_user

    return check_scope


def require_any_role(*roles: str):
    """
    Shorthand for requiring any of the specified roles

    Usage:
        @router.get("/moderator", dependencies=[Depends(require_any_role("admin", "moderator"))])
    """
    return require_roles(list(roles))


def require_all_roles(*roles: str):
    """
    Require user to have ALL specified roles

    Usage:
        @router.get("/super-admin", dependencies=[Depends(require_all_roles("admin", "super_user"))])
    """

    async def check_all_roles(
        current_user: AuthUser = Depends(get_current_user),
        auth_service: AuthenticationService = Depends(get_authentication_service),
        request_id: str = Depends(get_request_id),
    ):
        auth_context = AuthContext.authenticated(current_user, request_id)
        await auth_service.authorize_all_roles(auth_context, list(roles))
        return current_user

    return check_all_roles


# Enhanced dependencies for clean architecture
async def get_user_context(
    auth_context: AuthContext = Depends(get_auth_context),
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> dict:
    """
    Get detailed user context for logging and audit purposes
    """
    return await auth_service.get_user_context(auth_context)


def require_authenticated():
    """
    Simple dependency to require authentication without specific roles

    Usage:
        @router.get("/protected", dependencies=[Depends(require_authenticated())])
        async def protected_endpoint():
            pass
    """

    async def check_authenticated(user: AuthUser = Depends(get_current_user)):
        return user

    return check_authenticated


def with_auth_context():
    """
    Dependency that provides AuthContext instead of just AuthUser

    Usage:
        @router.get("/profile")
        async def get_profile(auth_context: AuthContext = Depends(with_auth_context())):
            if auth_context.is_authenticated:
                # Handle authenticated user
                pass
            else:
                # Handle anonymous user
                pass
    """

    async def get_context(auth_context: AuthContext = Depends(get_auth_context)):
        return auth_context

    return get_context
