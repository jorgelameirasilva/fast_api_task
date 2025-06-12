"""
Authentication Tests for Clean Architecture
Comprehensive test suite for JWT authentication, authorization, and integration
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.auth.models import (
    AuthUser,
    AuthContext,
    TokenValidationRequest,
    TokenValidationResult,
)
from app.auth.repositories.jwt_repository import (
    MockJWTRepository,
    ProductionJWTRepository,
)
from app.auth.services.authentication_service import AuthenticationService


class TestAuthUser:
    """Test AuthUser model functionality"""

    def test_user_creation_from_jwt_payload(self):
        """Test creating AuthUser from JWT payload"""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "preferred_username": "test",
            "roles": ["user", "editor"],
            "groups": ["users", "editors"],
            "scope": "read write",
            "iat": 1640995200,  # 2022-01-01 00:00:00 UTC
            "exp": 1672531200,  # 2023-01-01 00:00:00 UTC
        }

        user = AuthUser.from_jwt_payload(payload)

        assert user.user_id == "user-123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.preferred_username == "test"
        assert user.roles == ["user", "editor"]
        assert user.groups == ["users", "editors"]
        assert user.scope == "read write"
        assert user.issued_at == datetime.fromtimestamp(1640995200)
        assert user.expires_at == datetime.fromtimestamp(1672531200)

    def test_role_checking(self):
        """Test role checking methods"""
        user = AuthUser(
            user_id="test-123",
            roles=["user", "editor", "admin"],
            scope="read write admin",
        )

        # Single role checks
        assert user.has_role("user")
        assert user.has_role("admin")
        assert not user.has_role("super_admin")

        # Any role checks
        assert user.has_any_role(["user", "moderator"])
        assert user.has_any_role(["moderator", "admin"])
        assert not user.has_any_role(["moderator", "super_admin"])

        # All roles checks
        assert user.has_all_roles(["user", "editor"])
        assert not user.has_all_roles(["user", "super_admin"])

    def test_scope_checking(self):
        """Test scope checking methods"""
        user = AuthUser(user_id="test-123", scope="read write admin:users")

        assert user.has_scope("read")
        assert user.has_scope("write")
        assert user.has_scope("admin:users")
        assert not user.has_scope("delete")


class TestAuthContext:
    """Test AuthContext functionality"""

    def test_authenticated_context(self):
        """Test authenticated context creation"""
        user = AuthUser(user_id="test-123", roles=["user"])
        context = AuthContext.authenticated(user, request_id="req-123")

        assert context.is_authenticated
        assert context.token_valid
        assert context.auth_method == "JWT"
        assert context.user == user
        assert context.request_id == "req-123"

    def test_anonymous_context(self):
        """Test anonymous context creation"""
        context = AuthContext.anonymous(request_id="req-456")

        assert not context.is_authenticated
        assert not context.token_valid
        assert context.auth_method is None
        assert context.user is None
        assert context.request_id == "req-456"

    def test_context_role_checking(self):
        """Test role checking through context"""
        user = AuthUser(user_id="test-123", roles=["user", "admin"])
        context = AuthContext.authenticated(user)

        assert context.has_role("user")
        assert context.has_any_role(["moderator", "user"])
        assert not context.has_role("super_admin")

        # Anonymous context
        anonymous = AuthContext.anonymous()
        assert not anonymous.has_role("user")
        assert not anonymous.has_any_role(["user", "admin"])


class TestMockJWTRepository:
    """Test MockJWTRepository for development/testing"""

    @pytest.fixture
    def mock_repo(self):
        return MockJWTRepository()

    @pytest.mark.asyncio
    async def test_valid_mock_tokens(self, mock_repo):
        """Test validation of predefined mock tokens"""
        request = TokenValidationRequest(token="mock-token-admin")
        result = await mock_repo.validate_token(request)

        assert result.is_valid
        assert result.user is not None
        assert result.user.user_id == "admin-123"
        assert "admin" in result.user.roles
        assert result.validation_metadata["repository"] == "mock"

    @pytest.mark.asyncio
    async def test_invalid_token(self, mock_repo):
        """Test validation of invalid tokens"""
        request = TokenValidationRequest(token="invalid-token")
        result = await mock_repo.validate_token(request)

        assert not result.is_valid
        assert result.user is None
        assert result.error_code == "INVALID_TOKEN"

    @pytest.mark.asyncio
    async def test_special_test_cases(self, mock_repo):
        """Test special test case tokens"""
        # Expired token
        request = TokenValidationRequest(token="expired-token")
        result = await mock_repo.validate_token(request)

        assert not result.is_valid
        assert result.error_code == "TOKEN_EXPIRED"

        # Invalid issuer
        request = TokenValidationRequest(token="invalid-issuer")
        result = await mock_repo.validate_token(request)

        assert not result.is_valid
        assert result.error_code == "INVALID_ISSUER"

    @pytest.mark.asyncio
    async def test_custom_mock_user(self, mock_repo):
        """Test adding custom mock users"""
        custom_user = AuthUser(
            user_id="custom-123", email="custom@example.com", roles=["custom_role"]
        )

        mock_repo.create_custom_mock_user("custom-token", custom_user)

        request = TokenValidationRequest(token="custom-token")
        result = await mock_repo.validate_token(request)

        assert result.is_valid
        assert result.user.user_id == "custom-123"
        assert "custom_role" in result.user.roles

    @pytest.mark.asyncio
    async def test_health_check(self, mock_repo):
        """Test mock repository health check"""
        health = await mock_repo.health_check()

        assert health["status"] == "healthy"
        assert health["service"] == "Mock JWT Repository"
        assert "mock_users" in health


class TestAuthenticationService:
    """Test AuthenticationService business logic"""

    @pytest.fixture
    def mock_jwt_repo(self):
        return MockJWTRepository()

    @pytest.fixture
    def auth_service(self, mock_jwt_repo):
        return AuthenticationService(mock_jwt_repo)

    @pytest.mark.asyncio
    async def test_successful_authentication(self, auth_service):
        """Test successful user authentication"""
        auth_context = await auth_service.authenticate_user("mock-token-admin")

        assert auth_context.is_authenticated
        assert auth_context.user is not None
        assert auth_context.user.user_id == "admin-123"
        assert "admin" in auth_context.user.roles

    @pytest.mark.asyncio
    async def test_failed_authentication(self, auth_service):
        """Test failed authentication raises HTTPException"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authenticate_user("invalid-token")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_optional_authentication_success(self, auth_service):
        """Test optional authentication with valid token"""
        auth_context = await auth_service.authenticate_optional("mock-token-user")

        assert auth_context.is_authenticated
        assert auth_context.user.user_id == "user-456"

    @pytest.mark.asyncio
    async def test_optional_authentication_no_token(self, auth_service):
        """Test optional authentication with no token"""
        auth_context = await auth_service.authenticate_optional(None)

        assert not auth_context.is_authenticated
        assert auth_context.user is None

    @pytest.mark.asyncio
    async def test_optional_authentication_invalid_token(self, auth_service):
        """Test optional authentication with invalid token returns anonymous"""
        auth_context = await auth_service.authenticate_optional("invalid-token")

        assert not auth_context.is_authenticated
        assert auth_context.user is None

    @pytest.mark.asyncio
    async def test_role_authorization_success(self, auth_service):
        """Test successful role authorization"""
        user = AuthUser(user_id="test", roles=["admin", "user"])
        auth_context = AuthContext.authenticated(user)

        # Should not raise exception
        await auth_service.authorize_roles(auth_context, ["admin"])
        await auth_service.authorize_roles(auth_context, ["user", "admin"])

    @pytest.mark.asyncio
    async def test_role_authorization_failure(self, auth_service):
        """Test failed role authorization"""
        from fastapi import HTTPException

        user = AuthUser(user_id="test", roles=["user"])
        auth_context = AuthContext.authenticated(user)

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authorize_roles(auth_context, ["admin"])

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_scope_authorization(self, auth_service):
        """Test scope-based authorization"""
        from fastapi import HTTPException

        user = AuthUser(user_id="test", scope="read write")
        auth_context = AuthContext.authenticated(user)

        # Should succeed
        await auth_service.authorize_scope(auth_context, "read")

        # Should fail
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authorize_scope(auth_context, "admin")

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_authorization(self, auth_service):
        """Test authorization with unauthenticated context"""
        from fastapi import HTTPException

        auth_context = AuthContext.anonymous()

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authorize_roles(auth_context, ["user"])

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_context_extraction(self, auth_service):
        """Test extracting user context for logging"""
        user = AuthUser(
            user_id="test-123",
            email="test@example.com",
            roles=["user", "editor"],
            scope="read write",
        )
        auth_context = AuthContext.authenticated(user)

        context = await auth_service.get_user_context(auth_context)

        assert context["authenticated"] is True
        assert context["user_id"] == "test-123"
        assert context["email"] == "test@example.com"
        assert context["roles"] == ["user", "editor"]
        assert context["scopes"] == ["read", "write"]

    @pytest.mark.asyncio
    async def test_anonymous_user_context(self, auth_service):
        """Test user context for anonymous users"""
        auth_context = AuthContext.anonymous()

        context = await auth_service.get_user_context(auth_context)

        assert context["authenticated"] is False
        assert context["user_id"] is None
        assert context["roles"] == []
        assert context["scopes"] == []


class TestIntegration:
    """Integration tests for full authentication flow"""

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self):
        """Test complete authentication flow from token to context"""
        # Setup
        jwt_repo = MockJWTRepository()
        auth_service = AuthenticationService(jwt_repo)

        # Test full flow
        token = "mock-token-admin"
        auth_context = await auth_service.authenticate_user(token)

        # Verify authentication
        assert auth_context.is_authenticated
        assert auth_context.user.user_id == "admin-123"

        # Test authorization
        await auth_service.authorize_roles(auth_context, ["admin"])
        await auth_service.authorize_scope(auth_context, "admin")

        # Test user context extraction
        user_context = await auth_service.get_user_context(auth_context)
        assert user_context["authenticated"] is True
        assert "admin" in user_context["roles"]

    @pytest.mark.asyncio
    async def test_multi_role_authorization_scenarios(self):
        """Test various authorization scenarios"""
        jwt_repo = MockJWTRepository()
        auth_service = AuthenticationService(jwt_repo)

        # Admin user - should have access to everything
        admin_context = await auth_service.authenticate_user("mock-token-admin")
        await auth_service.authorize_roles(admin_context, ["admin"])
        await auth_service.authorize_roles(
            admin_context, ["user"]
        )  # Admin also has user role

        # Regular user - should have limited access
        user_context = await auth_service.authenticate_user("mock-token-user")
        await auth_service.authorize_roles(user_context, ["user"])

        # Readonly user - should have very limited access
        readonly_context = await auth_service.authenticate_user("mock-token-readonly")
        await auth_service.authorize_roles(readonly_context, ["readonly"])
        await auth_service.authorize_scope(readonly_context, "read")

        # Verify role isolation
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await auth_service.authorize_roles(user_context, ["admin"])

        with pytest.raises(HTTPException):
            await auth_service.authorize_scope(readonly_context, "write")

    def test_mock_tokens_available(self):
        """Test that mock tokens are available for testing"""
        repo = MockJWTRepository()
        tokens = repo.get_mock_tokens()

        # Verify we have tokens for different roles
        available_roles = list(tokens.keys())
        assert "admin" in available_roles
        assert "user" in available_roles
        assert "readonly" in available_roles


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
