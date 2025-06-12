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

    def has_all_roles(self, roles: List[str]) -> bool:
        """Check if user has all specified roles"""
        return all(role in self.roles for role in roles)

    def has_scope(self, scope: str) -> bool:
        """Check if user has specific scope"""
        return scope in self.scope.split()

    def to_context_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/context purposes"""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "roles": self.roles,
            "groups": self.groups,
            "scopes": self.scope.split() if self.scope else [],
        }


class AuthContext(BaseModel):
    """
    Authentication context for requests
    """

    user: Optional[AuthUser] = None
    is_authenticated: bool = False
    token_valid: bool = False
    auth_method: Optional[str] = None
    request_id: Optional[str] = None

    @classmethod
    def authenticated(
        cls, user: AuthUser, request_id: Optional[str] = None
    ) -> "AuthContext":
        """Create authenticated context"""
        return cls(
            user=user,
            is_authenticated=True,
            token_valid=True,
            auth_method="JWT",
            request_id=request_id,
        )

    @classmethod
    def anonymous(cls, request_id: Optional[str] = None) -> "AuthContext":
        """Create anonymous context"""
        return cls(
            user=None,
            is_authenticated=False,
            token_valid=False,
            auth_method=None,
            request_id=request_id,
        )

    def has_role(self, role: str) -> bool:
        """Check if authenticated user has specific role"""
        return self.user.has_role(role) if self.user else False

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if authenticated user has any of the specified roles"""
        return self.user.has_any_role(roles) if self.user else False

    def has_scope(self, scope: str) -> bool:
        """Check if authenticated user has specific scope"""
        return self.user.has_scope(scope) if self.user else False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging purposes"""
        return {
            "is_authenticated": self.is_authenticated,
            "auth_method": self.auth_method,
            "user": self.user.to_context_dict() if self.user else None,
            "request_id": self.request_id,
        }


class TokenValidationRequest(BaseModel):
    """Request model for token validation"""

    token: str = Field(..., description="JWT token to validate")
    validate_expiry: bool = Field(True, description="Whether to validate token expiry")
    validate_audience: bool = Field(True, description="Whether to validate audience")
    validate_issuer: bool = Field(True, description="Whether to validate issuer")


class TokenValidationResult(BaseModel):
    """Result of token validation"""

    is_valid: bool = Field(..., description="Whether token is valid")
    user: Optional[AuthUser] = Field(None, description="Extracted user if valid")
    error_code: Optional[str] = Field(None, description="Error code if invalid")
    error_message: Optional[str] = Field(None, description="Error message if invalid")
    validation_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Validation metadata"
    )
