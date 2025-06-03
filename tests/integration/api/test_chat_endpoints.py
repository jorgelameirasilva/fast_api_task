import pytest
from fastapi.testclient import TestClient


class TestChatEndpoints:
    """Integration tests for chat API endpoints"""

    def test_chat_endpoint_basic_conversation(self, client):
        """Test basic chat conversation functionality using approaches"""
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

        # Should always use approach-based responses now
        assert "Chat-Read-Retrieve-Read approach" in data["message"]["content"]

        # Validate approach integration
        assert "context" in data
        assert data["context"]["streaming"] is False
        assert data["context"]["approach_used"] == "chat_read_retrieve_read"
        assert data["context"]["approach_type"] == "ChatReadRetrieveReadApproach"

        # Validate approach-specific context
        assert "data_points" in data["context"]
        assert "thoughts" in data["context"]
        assert "followup_questions" in data["context"]

    def test_chat_endpoint_with_session_state(self, client):
        """Test chat endpoint maintains session state with approaches"""
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

        # Ensure approach is used
        assert data["context"]["approach_used"] == "chat_read_retrieve_read"
        assert data["context"]["approach_type"] == "ChatReadRetrieveReadApproach"

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
        """Test basic ask functionality using approaches"""
        # Arrange
        ask_request = {"user_query": "What is artificial intelligence?"}

        # Act
        response = client.post("/ask", json=ask_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_query"] == "What is artificial intelligence?"

        # Should always use approach-based responses now
        assert "Retrieve-Then-Read approach" in data["chatbot_response"]

        # Validate approach integration
        assert len(data["sources"]) >= 1
        assert data["count"] == 0
        assert data["context"]["approach_used"] == "retrieve_then_read"
        assert data["context"]["approach_type"] == "RetrieveThenReadApproach"

        # Validate approach-specific context
        assert "data_points" in data["context"]
        assert "thoughts" in data["context"]

    def test_ask_endpoint_with_context(self, client):
        """Test ask endpoint with previous context using approaches"""
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

        # Ensure approach is used
        assert data["context"]["approach_used"] == "retrieve_then_read"
        assert data["context"]["approach_type"] == "RetrieveThenReadApproach"

    def test_ask_endpoint_empty_query(self, client):
        """Test ask endpoint rejects empty queries"""
        # Arrange
        invalid_request = {"user_query": ""}

        # Act
        response = client.post("/ask", json=invalid_request)

        # Assert
        assert response.status_code == 422  # Pydantic validation error for min_length=1

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
        """Test streaming parameter works for both endpoints with approaches"""
        # Test chat with streaming
        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}
        response = client.post("/chat", json=chat_request, params={"stream": True})
        assert response.status_code == 200
        data = response.json()
        assert data["context"]["streaming"] is True
        assert data["context"]["approach_used"] == "chat_read_retrieve_read"

        # Test ask with streaming
        ask_request = {"user_query": "What is Python?"}
        response = client.post("/ask", json=ask_request, params={"stream": True})
        assert response.status_code == 200
        data = response.json()
        assert data["context"]["streaming"] is True
        assert data["context"]["approach_used"] == "retrieve_then_read"

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
        """Test proper content type handling with approaches"""
        # Valid request with explicit content type
        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}
        response = client.post(
            "/chat", json=chat_request, headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        # Ensure approach is used
        data = response.json()
        assert data["context"]["approach_used"] == "chat_read_retrieve_read"

    def test_large_content_handling(self, client):
        """Test handling of reasonably large content with approaches"""
        # Create a moderately large message (1KB)
        large_content = "A" * 1000
        chat_request = {"messages": [{"role": "user", "content": large_content}]}

        response = client.post("/chat", json=chat_request)
        assert response.status_code == 200
        # Should handle large content gracefully and use approach
        data = response.json()
        assert data["context"]["approach_used"] == "chat_read_retrieve_read"

    def test_special_characters_in_content(self, client):
        """Test handling of special characters and unicode with approaches"""
        # Test with special characters and unicode
        special_content = "Hello! 🤖 Can you help with émojis and spëcial chars?"
        ask_request = {"user_query": special_content}

        response = client.post("/ask", json=ask_request)
        assert response.status_code == 200
        data = response.json()
        assert data["user_query"] == special_content
        # Ensure approach is used
        assert data["context"]["approach_used"] == "retrieve_then_read"

    def test_approach_primary_integration(self, client):
        """Test that approaches are the primary processing method (not fallbacks)"""
        # Test chat approach is primary
        chat_request = {
            "messages": [{"role": "user", "content": "Tell me about health insurance"}]
        }
        response = client.post("/chat", json=chat_request)

        assert response.status_code == 200
        data = response.json()

        # Should always use chat approach as primary
        assert data["context"]["approach_used"] == "chat_read_retrieve_read"
        assert data["context"]["approach_type"] == "ChatReadRetrieveReadApproach"

        # Should have rich approach context
        assert "data_points" in data["context"]
        assert "thoughts" in data["context"]
        assert "followup_questions" in data["context"]
        assert len(data["context"]["followup_questions"]) > 0

        # Test ask approach is primary
        ask_request = {"user_query": "What are my benefits?"}
        response = client.post("/ask", json=ask_request)

        assert response.status_code == 200
        data = response.json()

        # Should always use ask approach as primary
        assert data["context"]["approach_used"] == "retrieve_then_read"
        assert data["context"]["approach_type"] == "RetrieveThenReadApproach"

        # Should have rich approach context
        assert "data_points" in data["context"]
        assert "thoughts" in data["context"]
        assert len(data["sources"]) > 0

        # Validate source structure
        for source in data["sources"]:
            assert "title" in source
            assert "url" in source
            assert "relevance_score" in source
            assert "excerpt" in source

    def test_approach_response_structure(self, client):
        """Test that approach responses have the expected rich structure"""
        # Test chat approach response structure
        chat_request = {
            "messages": [
                {"role": "user", "content": "Explain employee handbook policies"}
            ]
        }
        response = client.post("/chat", json=chat_request)

        assert response.status_code == 200
        data = response.json()

        # Validate chat response structure
        assert "message" in data
        assert "session_state" in data
        assert "context" in data

        # Validate context has approach metadata
        context = data["context"]
        required_fields = [
            "approach_used",
            "approach_type",
            "streaming",
            "session_updated",
            "chat_processed_at",
            "data_points",
            "thoughts",
            "followup_questions",
        ]
        for field in required_fields:
            assert field in context, f"Missing required field: {field}"

        # Test ask approach response structure
        ask_request = {"user_query": "What is my health plan coverage?"}
        response = client.post("/ask", json=ask_request)

        assert response.status_code == 200
        data = response.json()

        # Validate ask response structure
        assert "user_query" in data
        assert "chatbot_response" in data
        assert "context" in data
        assert "sources" in data
        assert "count" in data

        # Validate context has approach metadata
        context = data["context"]
        required_fields = [
            "approach_used",
            "approach_type",
            "streaming",
            "query_processed_at",
            "data_points",
            "thoughts",
        ]
        for field in required_fields:
            assert field in context, f"Missing required field: {field}"
