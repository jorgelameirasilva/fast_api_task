"""
Integration tests for authenticated API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import patch, Mock

from app.auth.models import AuthUser


class TestAuthenticatedEndpoints:
    """Test authentication requirements for protected endpoints"""

    @pytest.mark.parametrize(
        "endpoint,method,payload",
        [
            ("/chat", "post", {"messages": [{"role": "user", "content": "Hello"}]}),
            ("/ask", "post", {"user_query": "What is AI?"}),
            (
                "/vote",
                "post",
                {
                    "user_query": "Test query",
                    "chatbot_response": "Test response",
                    "upvote": True,
                    "count": 1,
                },
            ),
        ],
    )
    def test_endpoints_require_authentication(self, client, endpoint, method, payload):
        """Test that protected endpoints require authentication"""
        # Act
        response = getattr(client, method)(endpoint, json=payload)

        # Assert
        assert response.status_code == 401
        assert "Authorization header required" in response.json()["detail"]

    @pytest.mark.parametrize(
        "endpoint,method,payload",
        [
            ("/chat", "post", {"messages": [{"role": "user", "content": "Hello"}]}),
            ("/ask", "post", {"user_query": "What is AI?"}),
            (
                "/vote",
                "post",
                {
                    "user_query": "Test query",
                    "chatbot_response": "Test response",
                    "upvote": True,
                    "count": 1,
                },
            ),
        ],
    )
    def test_endpoints_with_invalid_token(self, client, endpoint, method, payload):
        """Test protected endpoints with invalid token"""
        # Arrange
        invalid_headers = {"Authorization": "Bearer invalid-token"}

        # Act
        with patch("app.auth.dependencies.get_jwt_authenticator") as mock_auth:
            mock_authenticator = Mock()
            mock_authenticator.validate_and_extract_user.side_effect = HTTPException(
                status_code=401, detail="Invalid token"
            )
            mock_auth.return_value = mock_authenticator

            response = getattr(client, method)(
                endpoint, json=payload, headers=invalid_headers
            )

        # Assert
        assert response.status_code == 401

    def test_auth_setup_endpoint_public(self, client):
        """Test that auth setup endpoint is public"""
        # Act
        response = client.get("/auth_setup")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "auth_enabled" in data
        assert "auth_type" in data

    def test_chat_endpoint_with_authentication(
        self, authenticated_client, auth_headers
    ):
        """Test chat endpoint with proper authentication"""
        # Arrange
        chat_request = {
            "messages": [{"role": "user", "content": "Hello, how are you?"}]
        }

        # Act
        response = authenticated_client.post(
            "/chat", json=chat_request, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data

    def test_ask_endpoint_with_authentication(self, authenticated_client, auth_headers):
        """Test ask endpoint with proper authentication"""
        # Arrange
        ask_request = {"user_query": "What is artificial intelligence?"}

        # Act
        response = authenticated_client.post(
            "/ask", json=ask_request, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "user_query" in data
        assert "chatbot_response" in data

    def test_vote_endpoint_with_authentication(
        self, authenticated_client, auth_headers
    ):
        """Test vote endpoint with proper authentication"""
        # Arrange
        vote_request = {
            "user_query": "What is machine learning?",
            "chatbot_response": "Machine learning is a subset of AI...",
            "upvote": True,
            "count": 1,
        }

        # Act
        response = authenticated_client.post(
            "/vote", json=vote_request, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["upvote"] is True

    def test_authentication_with_different_users(self, client):
        """Test authentication with different user types"""
        # Test with regular user
        regular_user = AuthUser(
            sub="regular-user-123",
            email="user@example.com",
            roles=["user"],
            scope="read write",
        )

        admin_user = AuthUser(
            sub="admin-user-456",
            email="admin@example.com",
            roles=["admin", "user"],
            scope="read write delete admin",
        )

        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}

        # Test regular user access
        with patch("app.auth.dependencies.get_current_user", return_value=regular_user):
            response = client.post(
                "/chat",
                json=chat_request,
                headers={"Authorization": "Bearer user-token"},
            )
            assert response.status_code == 200

        # Test admin user access
        with patch("app.auth.dependencies.get_current_user", return_value=admin_user):
            response = client.post(
                "/chat",
                json=chat_request,
                headers={"Authorization": "Bearer admin-token"},
            )
            assert response.status_code == 200

    def test_token_extraction_edge_cases(self, client):
        """Test edge cases in token extraction"""
        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}

        # Test with malformed Bearer token
        response = client.post(
            "/chat", json=chat_request, headers={"Authorization": "Bearer"}
        )
        assert response.status_code == 401

        # Test with wrong scheme
        response = client.post(
            "/chat", json=chat_request, headers={"Authorization": "Basic dGVzdDp0ZXN0"}
        )
        assert response.status_code == 401

        # Test with empty authorization header
        response = client.post(
            "/chat", json=chat_request, headers={"Authorization": ""}
        )
        assert response.status_code == 401


class TestJWTIntegration:
    """Test JWT token integration end-to-end"""

    def test_jwt_token_validation_flow(self, client):
        """Test complete JWT validation flow"""
        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}

        # Mock the complete JWT validation chain
        test_user = AuthUser(
            sub="jwt-user-789",
            email="jwt@example.com",
            name="JWT User",
            roles=["user"],
            scope="read write",
        )

        with patch("app.auth.jwt.get_jwt_authenticator") as mock_get_auth:
            mock_authenticator = Mock()
            mock_authenticator.validate_and_extract_user.return_value = test_user
            mock_get_auth.return_value = mock_authenticator

            response = client.post(
                "/chat",
                json=chat_request,
                headers={"Authorization": "Bearer valid-jwt-token"},
            )

            # Verify the JWT validation was called
            mock_authenticator.validate_and_extract_user.assert_called_once_with(
                "valid-jwt-token"
            )
            assert response.status_code == 200

    def test_jwt_error_scenarios(self, client):
        """Test various JWT error scenarios"""
        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}

        error_scenarios = [
            (HTTPException(status_code=401, detail="Token expired"), 401),
            (HTTPException(status_code=401, detail="Invalid signature"), 401),
            (HTTPException(status_code=401, detail="Invalid issuer"), 401),
            (HTTPException(status_code=401, detail="Invalid audience"), 401),
            (
                HTTPException(status_code=500, detail="Authentication service error"),
                500,
            ),
        ]

        for exception, expected_status in error_scenarios:
            with patch("app.auth.jwt.get_jwt_authenticator") as mock_get_auth:
                mock_authenticator = Mock()
                mock_authenticator.validate_and_extract_user.side_effect = exception
                mock_get_auth.return_value = mock_authenticator

                response = client.post(
                    "/chat",
                    json=chat_request,
                    headers={"Authorization": "Bearer error-token"},
                )

                assert response.status_code == expected_status
