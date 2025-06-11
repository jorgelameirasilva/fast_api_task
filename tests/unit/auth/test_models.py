"""
Tests for authentication models
"""

import pytest
from datetime import datetime
from app.auth.models import AuthUser, AuthContext


class TestAuthUser:
    """Tests for AuthUser model"""

    def test_auth_user_creation_basic(self):
        """Test basic AuthUser creation"""
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "name": "Test User",
            "roles": ["user"],
        }

        user = AuthUser(**user_data)

        assert user.user_id == "user123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.roles == ["user"]

    def test_auth_user_from_jwt_payload(self):
        """Test creating AuthUser from JWT payload"""
        jwt_payload = {
            "sub": "user456",
            "email": "jwt@example.com",
            "name": "JWT User",
            "preferred_username": "jwtuser",
            "roles": ["admin", "user"],
            "groups": ["administrators"],
            "scope": "read write delete",
            "iat": 1640995200,  # 2022-01-01 00:00:00 UTC
            "exp": 1641081600,  # 2022-01-02 00:00:00 UTC
        }

        user = AuthUser.from_jwt_payload(jwt_payload)

        assert user.user_id == "user456"
        assert user.email == "jwt@example.com"
        assert user.name == "JWT User"
        assert user.preferred_username == "jwtuser"
        assert user.roles == ["admin", "user"]
        assert user.groups == ["administrators"]
        assert user.scope == "read write delete"
        assert isinstance(user.issued_at, datetime)
        assert isinstance(user.expires_at, datetime)

    def test_auth_user_has_role(self):
        """Test role checking functionality"""
        user = AuthUser(sub="user123", roles=["admin", "moderator", "user"])

        assert user.has_role("admin") is True
        assert user.has_role("moderator") is True
        assert user.has_role("user") is True
        assert user.has_role("guest") is False
        assert user.has_role("superuser") is False

    def test_auth_user_has_any_role(self):
        """Test checking for any of multiple roles"""
        user = AuthUser(sub="user123", roles=["user", "moderator"])

        assert user.has_any_role(["admin", "moderator"]) is True
        assert user.has_any_role(["user", "guest"]) is True
        assert user.has_any_role(["admin", "superuser"]) is False
        assert user.has_any_role([]) is False

    def test_auth_user_has_scope(self):
        """Test scope checking functionality"""
        user = AuthUser(sub="user123", scope="read write admin:users")

        assert user.has_scope("read") is True
        assert user.has_scope("write") is True
        assert user.has_scope("admin:users") is True
        assert user.has_scope("delete") is False
        assert user.has_scope("admin:system") is False

    def test_auth_user_empty_scope(self):
        """Test scope checking with empty scope"""
        user = AuthUser(sub="user123", scope="")

        assert user.has_scope("read") is False
        assert user.has_scope("") is False

    def test_auth_user_alias_handling(self):
        """Test that aliases work correctly"""
        user_data = {
            "sub": "user123",  # Should map to user_id
            "iat": 1640995200,  # Should map to issued_at
            "exp": 1641081600,  # Should map to expires_at
        }

        user = AuthUser(**user_data)

        assert user.user_id == "user123"
        assert isinstance(user.issued_at, datetime)
        assert isinstance(user.expires_at, datetime)

    def test_auth_user_default_values(self):
        """Test default values for optional fields"""
        user = AuthUser(sub="user123")

        assert user.user_id == "user123"
        assert user.email is None
        assert user.name is None
        assert user.preferred_username is None
        assert user.roles == []
        assert user.groups == []
        assert user.scope == ""
        assert user.issued_at is None
        assert user.expires_at is None


class TestAuthContext:
    """Tests for AuthContext model"""

    def test_authenticated_context(self):
        """Test creating authenticated context"""
        user = AuthUser(sub="user123", email="test@example.com")

        context = AuthContext.authenticated(user)

        assert context.user == user
        assert context.is_authenticated is True
        assert context.token_valid is True
        assert context.auth_method == "JWT"

    def test_anonymous_context(self):
        """Test creating anonymous context"""
        context = AuthContext.anonymous()

        assert context.user is None
        assert context.is_authenticated is False
        assert context.token_valid is False
        assert context.auth_method is None

    def test_context_direct_creation(self):
        """Test direct context creation"""
        user = AuthUser(sub="user123")

        context = AuthContext(
            user=user, is_authenticated=True, token_valid=True, auth_method="Custom"
        )

        assert context.user == user
        assert context.is_authenticated is True
        assert context.token_valid is True
        assert context.auth_method == "Custom"

    def test_context_default_values(self):
        """Test default values for AuthContext"""
        context = AuthContext()

        assert context.user is None
        assert context.is_authenticated is False
        assert context.token_valid is False
        assert context.auth_method is None
