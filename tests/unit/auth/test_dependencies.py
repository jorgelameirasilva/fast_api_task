"""
Tests for authentication dependencies
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import (
    extract_token,
    get_current_user,
    get_optional_user,
    get_auth_context,
    require_roles,
    require_scope,
    require_any_role,
    require_all_roles,
)
from app.auth.models import AuthUser, AuthContext


class TestExtractToken:
    """Tests for extract_token dependency"""

    def test_extract_token_success(self):
        """Test successful token extraction"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid-jwt-token"
        )

        token = extract_token(credentials)

        assert token == "valid-jwt-token"

    def test_extract_token_no_credentials(self):
        """Test token extraction with no credentials"""
        with pytest.raises(HTTPException) as exc_info:
            extract_token(None)

        assert exc_info.value.status_code == 401
        assert "Authorization header required" in exc_info.value.detail

    def test_extract_token_empty_credentials(self):
        """Test token extraction with empty credentials"""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

        with pytest.raises(HTTPException) as exc_info:
            extract_token(credentials)

        assert exc_info.value.status_code == 401
        assert "Authorization header required" in exc_info.value.detail


class TestGetCurrentUser:
    """Tests for get_current_user dependency"""

    @patch("app.auth.dependencies.get_jwt_authenticator")
    def test_get_current_user_success(self, mock_get_authenticator):
        """Test successful user authentication"""
        # Setup
        mock_authenticator = Mock()
        mock_user = AuthUser(sub="user123", email="test@example.com")
        mock_authenticator.validate_and_extract_user.return_value = mock_user
        mock_get_authenticator.return_value = mock_authenticator

        # Act
        result = get_current_user("valid-token")

        # Assert
        assert result == mock_user
        mock_authenticator.validate_and_extract_user.assert_called_once_with(
            "valid-token"
        )

    @patch("app.auth.dependencies.get_jwt_authenticator")
    def test_get_current_user_invalid_token(self, mock_get_authenticator):
        """Test user authentication with invalid token"""
        # Setup
        mock_authenticator = Mock()
        mock_authenticator.validate_and_extract_user.side_effect = HTTPException(
            status_code=401, detail="Invalid token"
        )
        mock_get_authenticator.return_value = mock_authenticator

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user("invalid-token")

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


class TestGetOptionalUser:
    """Tests for get_optional_user dependency"""

    def test_get_optional_user_no_credentials(self):
        """Test optional user authentication with no credentials"""
        result = get_optional_user(None)
        assert result is None

    def test_get_optional_user_empty_credentials(self):
        """Test optional user authentication with empty credentials"""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

        result = get_optional_user(credentials)
        assert result is None

    @patch("app.auth.dependencies.get_jwt_authenticator")
    def test_get_optional_user_valid_token(self, mock_get_authenticator):
        """Test optional user authentication with valid token"""
        # Setup
        mock_authenticator = Mock()
        mock_user = AuthUser(sub="user123", email="test@example.com")
        mock_authenticator.validate_and_extract_user.return_value = mock_user
        mock_get_authenticator.return_value = mock_authenticator

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid-token"
        )

        # Act
        result = get_optional_user(credentials)

        # Assert
        assert result == mock_user

    @patch("app.auth.dependencies.get_jwt_authenticator")
    def test_get_optional_user_invalid_token(self, mock_get_authenticator):
        """Test optional user authentication with invalid token"""
        # Setup
        mock_authenticator = Mock()
        mock_authenticator.validate_and_extract_user.side_effect = HTTPException(
            status_code=401, detail="Invalid token"
        )
        mock_get_authenticator.return_value = mock_authenticator

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid-token"
        )

        # Act
        result = get_optional_user(credentials)

        # Assert
        assert result is None  # Should not raise exception, just return None


class TestGetAuthContext:
    """Tests for get_auth_context dependency"""

    def test_get_auth_context_authenticated(self):
        """Test auth context for authenticated user"""
        user = AuthUser(sub="user123", email="test@example.com")

        context = get_auth_context(user)

        assert isinstance(context, AuthContext)
        assert context.user == user
        assert context.is_authenticated is True
        assert context.token_valid is True
        assert context.auth_method == "JWT"

    def test_get_auth_context_anonymous(self):
        """Test auth context for anonymous user"""
        context = get_auth_context(None)

        assert isinstance(context, AuthContext)
        assert context.user is None
        assert context.is_authenticated is False
        assert context.token_valid is False
        assert context.auth_method is None


class TestRequireRoles:
    """Tests for require_roles dependency factory"""

    def test_require_roles_success(self):
        """Test successful role check"""
        user = AuthUser(sub="user123", roles=["admin", "user"])
        check_roles = require_roles(["admin"])

        result = check_roles(user)

        assert result == user

    def test_require_roles_insufficient_permissions(self):
        """Test role check with insufficient permissions"""
        user = AuthUser(sub="user123", roles=["user"])
        check_roles = require_roles(["admin"])

        with pytest.raises(HTTPException) as exc_info:
            check_roles(user)

        assert exc_info.value.status_code == 403
        assert "Required roles: admin" in exc_info.value.detail

    def test_require_roles_multiple_roles_success(self):
        """Test role check with multiple required roles (any)"""
        user = AuthUser(sub="user123", roles=["moderator"])
        check_roles = require_roles(["admin", "moderator"])

        result = check_roles(user)

        assert result == user

    def test_require_roles_multiple_roles_failure(self):
        """Test role check with multiple required roles (none)"""
        user = AuthUser(sub="user123", roles=["user"])
        check_roles = require_roles(["admin", "moderator"])

        with pytest.raises(HTTPException) as exc_info:
            check_roles(user)

        assert exc_info.value.status_code == 403
        assert "Required roles: admin, moderator" in exc_info.value.detail


class TestRequireScope:
    """Tests for require_scope dependency factory"""

    def test_require_scope_success(self):
        """Test successful scope check"""
        user = AuthUser(sub="user123", scope="read write delete")
        check_scope = require_scope("read")

        result = check_scope(user)

        assert result == user

    def test_require_scope_missing_scope(self):
        """Test scope check with missing scope"""
        user = AuthUser(sub="user123", scope="read write")
        check_scope = require_scope("delete")

        with pytest.raises(HTTPException) as exc_info:
            check_scope(user)

        assert exc_info.value.status_code == 403
        assert "Required scope 'delete' not found" in exc_info.value.detail

    def test_require_scope_empty_scope(self):
        """Test scope check with empty user scope"""
        user = AuthUser(sub="user123", scope="")
        check_scope = require_scope("read")

        with pytest.raises(HTTPException) as exc_info:
            check_scope(user)

        assert exc_info.value.status_code == 403
        assert "Required scope 'read' not found" in exc_info.value.detail


class TestRequireAnyRole:
    """Tests for require_any_role helper function"""

    def test_require_any_role_success(self):
        """Test require_any_role success"""
        user = AuthUser(sub="user123", roles=["moderator"])
        check_roles = require_any_role("admin", "moderator")

        result = check_roles(user)

        assert result == user

    def test_require_any_role_failure(self):
        """Test require_any_role failure"""
        user = AuthUser(sub="user123", roles=["user"])
        check_roles = require_any_role("admin", "moderator")

        with pytest.raises(HTTPException) as exc_info:
            check_roles(user)

        assert exc_info.value.status_code == 403


class TestRequireAllRoles:
    """Tests for require_all_roles dependency factory"""

    def test_require_all_roles_success(self):
        """Test successful all roles check"""
        user = AuthUser(sub="user123", roles=["admin", "user", "moderator"])
        check_roles = require_all_roles("admin", "user")

        result = check_roles(user)

        assert result == user

    def test_require_all_roles_missing_one_role(self):
        """Test all roles check with missing role"""
        user = AuthUser(sub="user123", roles=["admin"])
        check_roles = require_all_roles("admin", "user")

        with pytest.raises(HTTPException) as exc_info:
            check_roles(user)

        assert exc_info.value.status_code == 403
        assert "Missing required roles: user" in exc_info.value.detail

    def test_require_all_roles_missing_multiple_roles(self):
        """Test all roles check with missing multiple roles"""
        user = AuthUser(sub="user123", roles=["user"])
        check_roles = require_all_roles("admin", "moderator", "superuser")

        with pytest.raises(HTTPException) as exc_info:
            check_roles(user)

        assert exc_info.value.status_code == 403
        assert (
            "Missing required roles: admin, moderator, superuser"
            in exc_info.value.detail
        )
