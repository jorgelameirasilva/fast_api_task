"""
Authentication Module
Provides JWT authentication, authorization, and user management for the application.
"""

from .dependencies import (
    get_current_user,
    get_optional_user,
    require_roles,
    require_scope,
)
from .jwt import JWTAuthenticator
from .models import AuthUser, AuthContext

__all__ = [
    "get_current_user",
    "get_optional_user",
    "require_roles",
    "require_scope",
    "JWTAuthenticator",
    "AuthUser",
    "AuthContext",
]
