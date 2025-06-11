"""
Authentication Models
Pydantic models for authentication data structures
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    """
    Structured user model from JWT token claims
    """

    user_id: str = Field(alias="sub", description="User identifier")
    email: Optional[str] = Field(None, description="User email address")
    name: Optional[str] = Field(None, description="User full name")
    preferred_username: Optional[str] = Field(None, description="Preferred username")
    roles: List[str] = Field(default_factory=list, description="User roles")
    groups: List[str] = Field(default_factory=list, description="User groups")
    scope: str = Field(default="", description="OAuth scopes")
    issued_at: Optional[datetime] = Field(
        None, alias="iat", description="Token issued at"
    )
    expires_at: Optional[datetime] = Field(
        None, alias="exp", description="Token expires at"
    )

    class Config:
        populate_by_name = True

    @classmethod
    def from_jwt_payload(cls, payload: Dict[str, Any]) -> "AuthUser":
        """Create AuthUser from JWT token payload"""
        # Convert timestamps to datetime objects
        iat = payload.get("iat")
        exp = payload.get("exp")

        return cls(
            **payload,
            issued_at=datetime.fromtimestamp(iat) if iat else None,
            expires_at=datetime.fromtimestamp(exp) if exp else None,
        )

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        return any(role in self.roles for role in roles)

    def has_scope(self, scope: str) -> bool:
        """Check if user has specific scope"""
        return scope in self.scope.split()


class AuthContext(BaseModel):
    """
    Authentication context for requests
    """

    user: Optional[AuthUser] = None
    is_authenticated: bool = False
    token_valid: bool = False
    auth_method: Optional[str] = None

    @classmethod
    def authenticated(cls, user: AuthUser) -> "AuthContext":
        """Create authenticated context"""
        return cls(
            user=user, is_authenticated=True, token_valid=True, auth_method="JWT"
        )

    @classmethod
    def anonymous(cls) -> "AuthContext":
        """Create anonymous context"""
        return cls(
            user=None, is_authenticated=False, token_valid=False, auth_method=None
        )
