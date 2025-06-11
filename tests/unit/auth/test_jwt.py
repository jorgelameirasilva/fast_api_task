"""
Tests for JWT authentication
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from fastapi import HTTPException
import jwt

from app.auth.jwt import JWTAuthenticator, get_jwt_authenticator
from app.auth.models import AuthUser


class TestJWTAuthenticator:
    """Tests for JWTAuthenticator class"""

    def test_jwt_authenticator_initialization(self):
        """Test JWT authenticator initialization"""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.APIM_ONELOGIN_URL = (
                "https://example.com/.well-known/jwks.json"
            )

            with patch("app.auth.jwt.PyJWKClient") as mock_jwks_client:
                authenticator = JWTAuthenticator()

                assert authenticator.jwks_client is not None
                mock_jwks_client.assert_called_once_with(
                    "https://example.com/.well-known/jwks.json"
                )

    def test_jwt_authenticator_no_url(self):
        """Test JWT authenticator when no JWKS URL is configured"""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.APIM_ONELOGIN_URL = ""

            authenticator = JWTAuthenticator()

            assert authenticator.jwks_client is None

    @patch("app.auth.jwt.settings")
    def test_validate_and_extract_user_success(self, mock_settings):
        """Test successful JWT validation and user extraction"""
        # Setup
        mock_settings.JWT_ALGORITHMS = ["RS256"]
        mock_settings.JWT_AUDIENCE = "test-audience"
        mock_settings.JWT_ISSUER = "test-issuer"

        authenticator = JWTAuthenticator()

        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        authenticator.jwks_client = mock_jwks_client

        # Mock JWT payload
        future_timestamp = (
            int((datetime.now(timezone.utc).timestamp())) + 3600
        )  # 1 hour from now
        mock_payload = {
            "sub": "user123",
            "email": "test@example.com",
            "name": "Test User",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": future_timestamp,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "roles": ["user"],
        }

        with patch("app.auth.jwt.jwt.decode", return_value=mock_payload):
            # Act
            user = authenticator.validate_and_extract_user("valid-token")

            # Assert
            assert isinstance(user, AuthUser)
            assert user.user_id == "user123"
            assert user.email == "test@example.com"
            assert user.name == "Test User"
            assert user.roles == ["user"]

    def test_validate_and_extract_user_no_jwks_client(self):
        """Test JWT validation when JWKS client is not initialized"""
        authenticator = JWTAuthenticator()
        authenticator.jwks_client = None

        with pytest.raises(HTTPException) as exc_info:
            authenticator.validate_and_extract_user("any-token")

        assert exc_info.value.status_code == 500
        assert "Authentication service unavailable" in exc_info.value.detail

    @patch("app.auth.jwt.settings")
    def test_validate_and_extract_user_expired_token(self, mock_settings):
        """Test JWT validation with expired token"""
        # Setup
        mock_settings.JWT_ALGORITHMS = ["RS256"]
        mock_settings.JWT_AUDIENCE = "test-audience"
        mock_settings.JWT_ISSUER = "test-issuer"

        authenticator = JWTAuthenticator()

        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        authenticator.jwks_client = mock_jwks_client

        # Mock expired JWT payload
        expired_timestamp = (
            int(datetime.now(timezone.utc).timestamp()) - 3600
        )  # 1 hour ago
        mock_payload = {
            "sub": "user123",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": expired_timestamp,
        }

        with patch("app.auth.jwt.jwt.decode", return_value=mock_payload):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                authenticator.validate_and_extract_user("expired-token")

            assert exc_info.value.status_code == 401
            assert "Token has expired" in exc_info.value.detail

    @patch("app.auth.jwt.settings")
    def test_validate_and_extract_user_invalid_issuer(self, mock_settings):
        """Test JWT validation with invalid issuer"""
        # Setup
        mock_settings.JWT_ALGORITHMS = ["RS256"]
        mock_settings.JWT_AUDIENCE = "test-audience"
        mock_settings.JWT_ISSUER = "expected-issuer"

        authenticator = JWTAuthenticator()

        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        authenticator.jwks_client = mock_jwks_client

        # Mock JWT payload with wrong issuer
        future_timestamp = int(datetime.now(timezone.utc).timestamp()) + 3600
        mock_payload = {
            "sub": "user123",
            "iss": "wrong-issuer",  # Wrong issuer
            "aud": "test-audience",
            "exp": future_timestamp,
        }

        with patch("app.auth.jwt.jwt.decode", return_value=mock_payload):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                authenticator.validate_and_extract_user("invalid-issuer-token")

            assert exc_info.value.status_code == 401
            assert "Token contains Invalid Issuer" in exc_info.value.detail

    @patch("app.auth.jwt.settings")
    def test_validate_and_extract_user_invalid_audience(self, mock_settings):
        """Test JWT validation with invalid audience"""
        # Setup
        mock_settings.JWT_ALGORITHMS = ["RS256"]
        mock_settings.JWT_AUDIENCE = "expected-audience"
        mock_settings.JWT_ISSUER = "test-issuer"

        authenticator = JWTAuthenticator()

        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        authenticator.jwks_client = mock_jwks_client

        # Mock JWT payload with wrong audience
        future_timestamp = int(datetime.now(timezone.utc).timestamp()) + 3600
        mock_payload = {
            "sub": "user123",
            "iss": "test-issuer",
            "aud": "wrong-audience",  # Wrong audience
            "exp": future_timestamp,
        }

        with patch("app.auth.jwt.jwt.decode", return_value=mock_payload):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                authenticator.validate_and_extract_user("invalid-audience-token")

            assert exc_info.value.status_code == 401
            assert "Token contains Invalid Audience" in exc_info.value.detail

    def test_validate_and_extract_user_invalid_token_error(self):
        """Test JWT validation with InvalidTokenError"""
        authenticator = JWTAuthenticator()

        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        authenticator.jwks_client = mock_jwks_client

        with patch(
            "app.auth.jwt.jwt.decode",
            side_effect=jwt.InvalidTokenError("invalid token"),
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                authenticator.validate_and_extract_user("invalid-token")

            assert exc_info.value.status_code == 401
            assert "Token not found" in exc_info.value.detail

    def test_validate_and_extract_user_general_exception(self):
        """Test JWT validation with general exception"""
        authenticator = JWTAuthenticator()

        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = Exception(
            "Connection error"
        )
        authenticator.jwks_client = mock_jwks_client

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            authenticator.validate_and_extract_user("any-token")

        assert exc_info.value.status_code == 500
        assert "Authentication service error" in exc_info.value.detail


class TestJWTAuthenticatorSingleton:
    """Tests for JWT authenticator singleton functionality"""

    def test_get_jwt_authenticator_singleton(self):
        """Test that get_jwt_authenticator returns singleton instance"""
        # Clear any cached instances
        get_jwt_authenticator.cache_clear()

        with patch("app.auth.jwt.JWTAuthenticator") as mock_authenticator_class:
            mock_instance = Mock()
            mock_authenticator_class.return_value = mock_instance

            # Call multiple times
            auth1 = get_jwt_authenticator()
            auth2 = get_jwt_authenticator()

            # Should be the same instance
            assert auth1 is auth2
            # Constructor should only be called once
            mock_authenticator_class.assert_called_once()
