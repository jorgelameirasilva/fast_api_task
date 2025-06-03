import pytest
from fastapi.testclient import TestClient


class TestChatEndpoints:
    """Integration tests for chat API endpoints"""

    def test_chat_endpoint_basic_conversation(self, client):
        """Test basic chat conversation functionality"""
        # Arrange
        chat_request = {
            "messages": [{"role": "user", "content": "Hello, how are you?"}]
        }

        # Act
        response = client.post("/chat", json=chat_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        assert (
            "Chat-Read-Retrieve-Read approach" in data["message"]["content"]
            or "How can I help you today?" in data["message"]["content"]
        )
        assert "context" in data
        assert data["context"]["streaming"] is False
        assert "approach_used" in data["context"]

    def test_chat_endpoint_with_session_state(self, client):
        """Test chat endpoint maintains session state"""
        # Arrange
        chat_request = {
            "messages": [{"role": "user", "content": "Remember my name is John"}],
            "session_state": "test-session-123",
        }

        # Act
        response = client.post("/chat", json=chat_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["session_state"] == "test-session-123"
        assert data["context"]["session_updated"] is True
        assert "approach_used" in data["context"]

    def test_chat_endpoint_empty_messages(self, client):
        """Test chat endpoint rejects empty messages"""
        # Arrange
        invalid_request = {"messages": []}

        # Act
        response = client.post("/chat", json=invalid_request)

        # Assert
        assert response.status_code == 400

    def test_chat_endpoint_missing_content(self, client):
        """Test chat endpoint rejects messages without content"""
        # Arrange
        invalid_request = {"messages": [{"role": "user"}]}

        # Act
        response = client.post("/chat", json=invalid_request)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_ask_endpoint_basic_question(self, client):
        """Test basic ask functionality"""
        # Arrange
        ask_request = {"user_query": "What is artificial intelligence?"}

        # Act
        response = client.post("/ask", json=ask_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_query"] == "What is artificial intelligence?"
        assert (
            "Retrieve-Then-Read approach" in data["chatbot_response"]
            or "helpful response" in data["chatbot_response"]
        )
        assert len(data["sources"]) >= 1
        assert data["count"] == 0
        assert "approach_used" in data["context"]

    def test_ask_endpoint_with_context(self, client):
        """Test ask endpoint with previous context"""
        # Arrange
        ask_request = {
            "user_query": "Can you explain more?",
            "chatbot_response": "AI is a technology...",
            "count": 5,
        }

        # Act
        response = client.post("/ask", json=ask_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 5
        assert "approach_used" in data["context"]

    def test_ask_endpoint_empty_query(self, client):
        """Test ask endpoint rejects empty queries"""
        # Arrange
        invalid_request = {"user_query": ""}

        # Act
        response = client.post("/ask", json=invalid_request)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_vote_endpoint_upvote(self, client):
        """Test successful upvote"""
        # Arrange
        vote_request = {
            "user_query": "What is machine learning?",
            "chatbot_response": "Machine learning is a subset of AI...",
            "upvote": True,
            "count": 1,
        }

        # Act
        response = client.post("/vote", json=vote_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["upvote"] is True
        assert data["count"] == 1
        assert "recorded successfully" in data["message"]

    def test_vote_endpoint_downvote(self, client):
        """Test successful downvote"""
        # Arrange
        vote_request = {
            "user_query": "Explain quantum computing",
            "chatbot_response": "This is a poor response...",
            "upvote": False,
            "count": 2,
        }

        # Act
        response = client.post("/vote", json=vote_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["upvote"] is False
        assert data["count"] == 2

    def test_vote_endpoint_with_additional_feedback(self, client):
        """Test vote with additional feedback fields"""
        # Arrange
        vote_request = {
            "user_query": "How does blockchain work?",
            "chatbot_response": "Blockchain is a distributed ledger...",
            "upvote": True,
            "count": 1,
            "reason_multiple_choice": "very_helpful",
            "additional_comments": "Great explanation, very clear!",
        }

        # Act
        response = client.post("/vote", json=vote_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_auth_setup_endpoint(self, client):
        """Test authentication setup configuration"""
        # Act
        response = client.get("/auth_setup")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["auth_enabled"] is False
        assert data["auth_type"] == "none"
        assert data["login_url"] is None
        assert data["logout_url"] is None

    def test_streaming_parameter(self, client):
        """Test streaming parameter works for both endpoints"""
        # Test chat with streaming
        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}
        response = client.post("/chat", json=chat_request, params={"stream": True})
        assert response.status_code == 200
        assert response.json()["context"]["streaming"] is True

        # Test ask with streaming
        ask_request = {"user_query": "What is Python?"}
        response = client.post("/ask", json=ask_request, params={"stream": True})
        assert response.status_code == 200
        assert response.json()["context"]["streaming"] is True

    def test_malformed_json_requests(self, client):
        """Test endpoints handle malformed JSON gracefully"""
        # Test malformed JSON
        response = client.post("/chat", data="invalid json")
        assert response.status_code == 422

        response = client.post("/ask", data="not json either")
        assert response.status_code == 422

        response = client.post("/vote", data="{broken json")
        assert response.status_code == 422

    def test_content_type_validation(self, client):
        """Test proper content type handling"""
        # Valid request with explicit content type
        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}
        response = client.post(
            "/chat", json=chat_request, headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200

    def test_large_content_handling(self, client):
        """Test handling of reasonably large content"""
        # Create a moderately large message (1KB)
        large_content = "A" * 1000
        chat_request = {"messages": [{"role": "user", "content": large_content}]}

        response = client.post("/chat", json=chat_request)
        assert response.status_code == 200
        # Should handle large content gracefully

    def test_special_characters_in_content(self, client):
        """Test handling of special characters and unicode"""
        # Test with special characters and unicode
        special_content = "Hello! 🤖 Can you help with émojis and spëcial chars?"
        ask_request = {"user_query": special_content}

        response = client.post("/ask", json=ask_request)
        assert response.status_code == 200
        data = response.json()
        assert data["user_query"] == special_content

    def test_approach_integration(self, client):
        """Test that approaches are properly integrated"""
        # Test chat with approach
        chat_request = {
            "messages": [{"role": "user", "content": "Tell me about health insurance"}]
        }
        response = client.post("/chat", json=chat_request)

        assert response.status_code == 200
        data = response.json()
        assert "approach_used" in data["context"]
        assert data["context"]["approach_used"] in ["chat_read_retrieve_read", "simple"]

        # Test ask with approach
        ask_request = {"user_query": "What are my benefits?"}
        response = client.post("/ask", json=ask_request)

        assert response.status_code == 200
        data = response.json()
        assert "approach_used" in data["context"]
        assert data["context"]["approach_used"] in ["retrieve_then_read", "simple"]
