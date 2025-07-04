"""Tests for enhanced JWT authentication functionality"""

import pytest
import time
import jwt
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.authentication import AuthenticationHelper, AuthError


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_helper():
    """Create authentication helper for testing"""
    return AuthenticationHelper(
        use_authentication=True,
        server_app_id="test-app-id",
        server_app_secret="test-secret",
        client_app_id="test-client-id",
        tenant_id="test-tenant-id",
    )


class TestJWTAuthentication:
    """Test JWT authentication functionality"""

    def test_health_endpoint_no_auth(self, client):
        """Test that health endpoint works without authentication"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_auth_setup_endpoint(self, client):
        """Test authentication setup endpoint"""
        response = client.get("/auth_setup")
        assert response.status_code == 200
        data = response.json()
        assert "useLogin" in data
        assert "msalConfig" in data

    def test_auth_claims_no_token(self, client):
        """Test auth claims endpoint without token"""
        response = client.get("/auth/claims")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["claims"] == {}

    def test_auth_validate_missing_token(self, client):
        """Test JWT validation endpoint without token"""
        response = client.post("/auth/validate")
        assert response.status_code == 401

    def test_auth_validate_invalid_header(self, client):
        """Test JWT validation with invalid authorization header"""
        response = client.post(
            "/auth/validate", headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code == 401

    def test_auth_validate_bearer_no_token(self, client):
        """Test JWT validation with Bearer but no token"""
        response = client.post("/auth/validate", headers={"Authorization": "Bearer"})
        assert response.status_code == 401

    def test_auth_profile_missing_token(self, client):
        """Test user profile endpoint without token"""
        response = client.get("/auth/profile")
        assert response.status_code == 401

    def test_get_token_auth_header_success(self, auth_helper):
        """Test successful token extraction from headers"""
        headers = {"Authorization": "Bearer test-token-123"}
        token = auth_helper.get_token_auth_header(headers)
        assert token == "test-token-123"

    def test_get_token_auth_header_missing(self, auth_helper):
        """Test token extraction with missing authorization header"""
        with pytest.raises(AuthError) as exc_info:
            auth_helper.get_token_auth_header({})
        assert exc_info.value.status_code == 401
        assert "authorization_header_missing" in str(exc_info.value.error)

    def test_get_token_auth_header_invalid_format(self, auth_helper):
        """Test token extraction with invalid header format"""
        headers = {"Authorization": "InvalidFormat token"}
        with pytest.raises(AuthError) as exc_info:
            auth_helper.get_token_auth_header(headers)
        assert exc_info.value.status_code == 401

    def test_get_token_auth_header_no_token(self, auth_helper):
        """Test token extraction with Bearer but no token"""
        headers = {"Authorization": "Bearer"}
        with pytest.raises(AuthError) as exc_info:
            auth_helper.get_token_auth_header(headers)
        assert exc_info.value.status_code == 401

    def test_get_token_auth_header_multiple_parts(self, auth_helper):
        """Test token extraction with too many parts"""
        headers = {"Authorization": "Bearer token extra part"}
        with pytest.raises(AuthError) as exc_info:
            auth_helper.get_token_auth_header(headers)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_validation_invalid_token(self, auth_helper):
        """Test JWT validation with invalid token"""
        with pytest.raises(AuthError) as exc_info:
            await auth_helper.validate_jwt_token("invalid-token")
        assert exc_info.value.status_code == 401

    def test_authentication_helper_configuration(self, auth_helper):
        """Test authentication helper is configured correctly"""
        assert auth_helper.use_authentication is True
        assert auth_helper.server_app_id == "test-app-id"
        assert auth_helper.AUDIENCE == "api://test-app-id"
        assert auth_helper.ISSUER == "https://sts.windows.net/test-tenant-id/"

    def test_singleton_instance(self, auth_helper):
        """Test that authentication helper uses singleton pattern"""
        instance = AuthenticationHelper.get_instance()
        assert instance is auth_helper

    @patch("app.core.authentication.jwt.PyJWKClient")
    @pytest.mark.asyncio
    async def test_jwt_validation_expired_token(self, mock_jwk_client, auth_helper):
        """Test JWT validation with expired token"""
        # Mock the JWT client
        mock_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwk_client.return_value = mock_client

        # Create an expired token
        expired_payload = {
            "iss": auth_helper.ISSUER,
            "aud": auth_helper.AUDIENCE,
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,  # Issued 2 hours ago
            "oid": "test-user-id",
        }

        with patch("app.core.authentication.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")

            with pytest.raises(AuthError) as exc_info:
                await auth_helper.validate_jwt_token("test-token")
            assert exc_info.value.status_code == 401
            assert "expired" in str(exc_info.value.error).lower()


class TestAuthenticationIntegration:
    """Test authentication integration with API endpoints"""

    def test_chat_endpoint_with_mock_auth(self, client):
        """Test chat endpoint works with mock authentication"""
        # Set environment variable to use mock clients
        import os

        os.environ["USE_MOCK_CLIENTS"] = "true"

        chat_request = {
            "messages": [{"role": "user", "content": "Hello"}],
            "context": {},
            "stream": False,
        }

        response = client.post("/chat", json=chat_request)
        assert response.status_code == 200

    def test_vote_endpoint_with_mock_auth(self, client):
        """Test vote endpoint works with mock authentication"""
        import os

        os.environ["USE_MOCK_CLIENTS"] = "true"

        vote_request = {
            "user_query": "Test query",
            "chatbot_response": "Test response",
            "upvote": 1,
            "downvote": 0,
            "count": 1,
        }

        response = client.post("/vote", json=vote_request)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_claims_with_mock_headers():
    """Test authentication claims extraction with mock headers"""
    auth_helper = AuthenticationHelper(
        use_authentication=False,  # Disabled for testing
        server_app_id="test-app",
        server_app_secret="test-secret",
        client_app_id="test-client",
        tenant_id="test-tenant",
    )

    # Test with authentication disabled
    claims = await auth_helper.get_auth_claims_if_enabled({})
    assert claims == {}


def test_security_filters():
    """Test security filter building functionality"""
    overrides = {"use_oid_security_filter": True, "use_groups_security_filter": True}
    auth_claims = {"oid": "test-user-oid", "groups": ["group1", "group2"]}

    security_filter = AuthenticationHelper.build_security_filters(
        overrides, auth_claims
    )
    assert "oid eq 'test-user-oid'" in security_filter
    assert "group1" in security_filter
    assert "group2" in security_filter
