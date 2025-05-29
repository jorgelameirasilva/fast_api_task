import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestChatEndpoints:
    """Test chat-related endpoints"""

    def test_chat_endpoint_success(self):
        """Test successful chat request"""
        chat_data = {
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "context": {"test": True},
            "session_state": "test-session-123",
        }

        response = client.post("/chat", json=chat_data)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        assert "content" in data["message"]
        assert data["session_state"] == "test-session-123"

    def test_chat_endpoint_no_user_message(self):
        """Test chat request with no user messages"""
        chat_data = {
            "messages": [{"role": "system", "content": "You are a helpful assistant"}]
        }

        response = client.post("/chat", json=chat_data)

        assert response.status_code == 400
        assert "No user message found" in response.json()["detail"]

    def test_chat_endpoint_invalid_data(self):
        """Test chat request with invalid data"""
        response = client.post("/chat", json={})

        assert response.status_code == 422  # Validation error

    def test_ask_endpoint_success(self):
        """Test successful ask request"""
        ask_data = {"user_query": "What is the capital of France?", "count": 1}

        response = client.post("/ask", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        assert data["user_query"] == "What is the capital of France?"
        assert "chatbot_response" in data
        assert "context" in data
        assert "sources" in data
        assert data["count"] == 1

    def test_ask_endpoint_empty_query(self):
        """Test ask request with empty query"""
        ask_data = {"user_query": ""}

        response = client.post("/ask", json=ask_data)

        assert response.status_code == 422  # Validation error

    def test_ask_endpoint_with_optional_fields(self):
        """Test ask request with optional fields"""
        ask_data = {
            "user_query": "Tell me about AI",
            "user_query_vector": [0.1, 0.2, 0.3],
            "chatbot_response": "Previous response",
            "count": 5,
            "upvote": True,
        }

        response = client.post("/ask", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        assert data["user_query"] == "Tell me about AI"
        assert data["count"] == 5

    def test_vote_endpoint_success(self):
        """Test successful vote request"""
        vote_data = {
            "user_query": "What is AI?",
            "chatbot_response": "AI is artificial intelligence",
            "count": 1,
            "upvote": True,
        }

        response = client.post("/vote", json=vote_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["upvote"] is True
        assert data["count"] == 1

    def test_vote_endpoint_downvote(self):
        """Test vote request with downvote"""
        vote_data = {
            "user_query": "What is AI?",
            "chatbot_response": "AI is artificial intelligence",
            "count": 2,
            "upvote": False,
        }

        response = client.post("/vote", json=vote_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["upvote"] is False
        assert data["count"] == 2

    def test_auth_setup_endpoint(self):
        """Test auth setup endpoint"""
        response = client.get("/auth_setup")

        assert response.status_code == 200
        data = response.json()
        assert "auth_enabled" in data
        assert "auth_type" in data
        assert isinstance(data["auth_enabled"], bool)


class TestStaticEndpoints:
    """Test static file serving endpoints"""

    def test_index_endpoint(self):
        """Test index page"""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Chat Application" in response.text

    def test_redirect_endpoint(self):
        """Test redirect endpoint"""
        response = client.get("/redirect")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "redirect"
        assert data["status"] == "success"

    def test_health_check_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "chat-application"
        assert "version" in data

    def test_favicon_endpoint_not_found(self):
        """Test favicon endpoint when file doesn't exist"""
        response = client.get("/favicon.ico")

        # Should return 404 if favicon doesn't exist
        assert response.status_code == 404

    def test_assets_endpoint_not_found(self):
        """Test assets endpoint with non-existent file"""
        response = client.get("/assets/nonexistent.css")

        assert response.status_code == 404

    def test_assets_endpoint_invalid_path(self):
        """Test assets endpoint with invalid path"""
        # Use URL-encoded path to ensure it reaches our endpoint
        response = client.get("/assets/..%2F..%2F..%2Fetc%2Fpasswd")

        # Path validation should prevent directory traversal and return 400
        assert response.status_code == 400
        assert "Invalid file path" in response.json()["detail"]

    def test_content_endpoint_not_found(self):
        """Test content endpoint with non-existent file"""
        response = client.get("/content/nonexistent.pdf")

        assert response.status_code == 404

    def test_content_endpoint_invalid_path(self):
        """Test content endpoint with invalid path"""
        # Use URL-encoded path to ensure it reaches our endpoint
        response = client.get("/content/..%2F..%2F..%2Fetc%2Fpasswd")

        # Path validation should prevent directory traversal and return 400
        assert response.status_code == 400
        assert "Invalid file path" in response.json()["detail"]

    def test_content_endpoint_with_page_number(self):
        """Test content endpoint with page number in path"""
        response = client.get("/content/document.pdf#page=5")

        # Should still return 404 for non-existent file, but path should be processed
        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling"""

    def test_404_endpoint(self):
        """Test non-existent endpoint"""
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test method not allowed"""
        response = client.delete("/chat")

        assert response.status_code == 405
