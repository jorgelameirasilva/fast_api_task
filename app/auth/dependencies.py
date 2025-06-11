"""
Authentication Dependencies
FastAPI dependencies for JWT authentication and authorization
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .jwt import get_jwt_authenticator
from .models import AuthUser, AuthContext


# Security schemes
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def extract_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract and validate token from authorization header"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(token: str = Depends(extract_token)) -> AuthUser:
    """
    Get authenticated user from JWT token

    This is the primary authentication dependency for protected endpoints.
    """
    authenticator = get_jwt_authenticator()
    return authenticator.validate_and_extract_user(token)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[AuthUser]:
    """
    Get user if authenticated, None otherwise

    Use this for endpoints that work with or without authentication.
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        authenticator = get_jwt_authenticator()
        return authenticator.validate_and_extract_user(credentials.credentials)
    except HTTPException:
        return None


def get_auth_context(
    user: Optional[AuthUser] = Depends(get_optional_user),
) -> AuthContext:
    """
    Get authentication context for the request

    Provides structured authentication information including user and auth status.
    """
    if user:
        return AuthContext.authenticated(user)
    return AuthContext.anonymous()


# Authorization dependency factories
def require_roles(required_roles: List[str]):
    """
    Factory for role-based access control

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles(["admin"]))])
        async def admin_endpoint():
            pass
    """

    def check_roles(current_user: AuthUser = Depends(get_current_user)):
        if not current_user.has_any_role(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}",
            )
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

    def check_scope(current_user: AuthUser = Depends(get_current_user)):
        if not current_user.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required scope '{required_scope}' not found",
            )
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

    def check_all_roles(current_user: AuthUser = Depends(get_current_user)):
        missing_roles = [role for role in roles if not current_user.has_role(role)]
        if missing_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {', '.join(missing_roles)}",
            )
        return current_user

    return check_all_roles
