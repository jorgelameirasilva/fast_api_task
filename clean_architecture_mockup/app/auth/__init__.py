"""
Authentication Module - Clean Architecture Implementation
Provides JWT authentication, authorization, and user management following clean architecture principles.
"""

from .models import AuthUser, AuthContext
from .dependencies import (
    get_current_user,
    get_optional_user,
    get_auth_context,
    require_roles,
    require_scope,
    require_any_role,
    require_all_roles,
)
from .services.authentication_service import AuthenticationService
from .repositories.jwt_repository import JWTRepository, MockJWTRepository

__all__ = [
    # Models
    "AuthUser",
    "AuthContext",
    # Dependencies
    "get_current_user",
    "get_optional_user",
    "get_auth_context",
    "require_roles",
    "require_scope",
    "require_any_role",
    "require_all_roles",
    # Services
    "AuthenticationService",
    # Repositories
    "JWTRepository",
    "MockJWTRepository",
]
