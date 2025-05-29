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
        # Check that approach information is included
        assert "approach_used" in data["context"]

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
        # Check that approach information is included
        assert "approach_used" in data["context"]

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

    def test_ask_endpoint_with_specific_approach(self):
        """Test ask request with specific approach"""
        ask_data = {"user_query": "What is artificial intelligence?", "count": 1}

        response = client.post("/ask?approach=retrieve_then_read", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        assert data["user_query"] == "What is artificial intelligence?"
        assert "chatbot_response" in data
        assert data["context"]["approach_used"] == "RetrieveThenRead"
        assert data["context"]["explicit_approach_requested"] == "retrieve_then_read"

    def test_ask_endpoint_with_chat_approach(self):
        """Test ask request with chat approach"""
        ask_data = {
            "user_query": "Tell me more about that",
            "chatbot_response": "AI is a field of computer science",
            "count": 1,
        }

        response = client.post("/ask?approach=chat_read_retrieve_read", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        assert data["context"]["approach_used"] == "ChatReadRetrieveRead"

    def test_ask_endpoint_with_invalid_approach(self):
        """Test ask request with invalid approach (should fallback)"""
        ask_data = {"user_query": "What is AI?", "count": 1}

        response = client.post("/ask?approach=nonexistent_approach", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        # Should fallback to default approach
        assert "approach_used" in data["context"]

    def test_ask_endpoint_with_streaming(self):
        """Test ask request with streaming enabled"""
        ask_data = {"user_query": "What is machine learning?", "count": 1}

        response = client.post("/ask?stream=true", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        assert data["context"]["streaming"] is True

    def test_ask_endpoint_approach_selection_simple_query(self):
        """Test that simple queries select RetrieveThenRead approach"""
        ask_data = {"user_query": "What is the weather today?", "count": 1}

        response = client.post("/ask", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        # Simple query should use RetrieveThenRead
        assert data["context"]["approach_used"] == "RetrieveThenRead"

    def test_ask_endpoint_approach_selection_policy_query(self):
        """Test that policy queries are handled appropriately"""
        ask_data = {
            "user_query": "What is our company policy on remote work?",
            "count": 1,
        }

        response = client.post("/ask", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        assert "policy" in data["chatbot_response"].lower()
        assert len(data["sources"]) > 0

    def test_ask_endpoint_with_previous_context(self):
        """Test ask request with previous chatbot response for context"""
        ask_data = {
            "user_query": "Can you elaborate on neural networks?",
            "chatbot_response": "Machine learning is a subset of artificial intelligence...",
            "count": 2,
        }

        response = client.post("/ask", json=ask_data)

        assert response.status_code == 200
        data = response.json()
        assert "chatbot_response" in data
        assert "context" in data

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

    def test_vote_endpoint_with_additional_fields(self):
        """Test vote request with all optional fields"""
        vote_data = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "count": 1,
            "upvote": True,
            "downvote": False,
            "reason_multiple_choice": "Helpful",
            "additional_comments": "Very clear instructions",
            "date": "01/01/01",
            "time": "00:00:00",
            "email_address": "example.email@axax1.com",
        }

        response = client.post("/vote", json=vote_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["upvote"] is True
        assert data["count"] == 1

    def test_vote_endpoint_downvote_with_additional_fields(self):
        """Test downvote with additional feedback fields"""
        vote_data = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "count": 1,
            "upvote": False,
            "downvote": True,
            "reason_multiple_choice": "Other",
            "additional_comments": "More comments",
        }

        response = client.post("/vote", json=vote_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["upvote"] is False
        assert data["count"] == 1

    def test_vote_endpoint_invalid_inputs(self):
        """Test vote endpoint with various invalid inputs"""
        # Test with invalid count types - negative numbers should be rejected by validation
        negative_counts = [-123, -1]
        for invalid_count in negative_counts:
            vote_data = {
                "user_query": "How do I report an illness?",
                "chatbot_response": "To report an illness, follow these steps:",
                "upvote": True,
                "downvote": False,
                "count": invalid_count,
            }

            response = client.post("/vote", json=vote_data)
            assert (
                response.status_code == 422
            ), f"Expected validation error for negative count: {invalid_count}"

        # Test with invalid data types for count
        invalid_type_counts = [1.23, "not_a_number", [1, 2, 3], (1, 2, 3)]
        for invalid_count in invalid_type_counts:
            vote_data = {
                "user_query": "How do I report an illness?",
                "chatbot_response": "To report an illness, follow these steps:",
                "upvote": True,
                "downvote": False,
                "count": invalid_count,
            }

            response = client.post("/vote", json=vote_data)
            assert (
                response.status_code == 422
            ), f"Expected validation error for invalid type count: {invalid_count}"

        # Test with valid but unusual counts (should pass)
        valid_counts = [0, 1, 2, 123, 1000]
        for valid_count in valid_counts:
            vote_data = {
                "user_query": "How do I report an illness?",
                "chatbot_response": "To report an illness, follow these steps:",
                "upvote": True,
                "count": valid_count,
            }

            response = client.post("/vote", json=vote_data)
            assert (
                response.status_code == 200
            ), f"Expected success for valid count: {valid_count}"

    def test_vote_endpoint_invalid_string_inputs(self):
        """Test vote endpoint with invalid string inputs"""
        str_invalid_inputs = [123, 1.23, {1: 2, 3: 4}, [1, 2, 3], (1, 2, 3)]

        for invalid_input in str_invalid_inputs:
            vote_data = {
                "user_query": "How do I report an illness?",
                "chatbot_response": "To report an illness, follow these steps:",
                "upvote": False,
                "downvote": True,
                "count": 1,
                "reason_multiple_choice": invalid_input,
            }

            response = client.post("/vote", json=vote_data)
            assert (
                response.status_code == 422
            ), f"Expected validation error for input: {invalid_input}"

    def test_vote_endpoint_empty_post(self):
        """Test vote endpoint with empty POST data"""
        response = client.post("/vote", json={})
        assert (
            response.status_code == 422
        )  # Validation error for missing required fields

    def test_vote_endpoint_conflicting_votes(self):
        """Test vote endpoint with conflicting upvote/downvote"""
        vote_data = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "count": 1,
            "upvote": True,
            "downvote": True,  # This should cause a conflict
        }

        response = client.post("/vote", json=vote_data)
        assert (
            response.status_code == 400
        )  # Should return bad request for conflicting votes

    def test_vote_endpoint_missing_required_fields(self):
        """Test vote endpoint with missing required fields"""
        # Missing user_query
        vote_data = {
            "chatbot_response": "To report an illness, follow these steps:",
            "count": 1,
            "upvote": True,
        }

        response = client.post("/vote", json=vote_data)
        assert response.status_code == 422

        # Missing chatbot_response
        vote_data = {
            "user_query": "How do I report an illness?",
            "count": 1,
            "upvote": True,
        }

        response = client.post("/vote", json=vote_data)
        assert response.status_code == 422

        # Missing count
        vote_data = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": True,
        }

        response = client.post("/vote", json=vote_data)
        assert response.status_code == 422

    def test_auth_setup_endpoint(self):
        """Test auth setup endpoint"""
        response = client.get("/auth_setup")

        assert response.status_code == 200
        data = response.json()
        assert "auth_enabled" in data
        assert "auth_type" in data
        assert isinstance(data["auth_enabled"], bool)

    def test_vote_endpoint_empty_strings(self):
        """Test vote endpoint with empty strings (should fail validation)"""
        # Test empty user_query
        vote_data = {
            "user_query": "",
            "chatbot_response": "To report an illness, follow these steps:",
            "count": 1,
            "upvote": True,
        }

        response = client.post("/vote", json=vote_data)
        assert response.status_code == 422  # Should fail min_length validation

        # Test empty chatbot_response
        vote_data = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "",
            "count": 1,
            "upvote": True,
        }

        response = client.post("/vote", json=vote_data)
        assert response.status_code == 422  # Should fail min_length validation

    def test_chat_endpoint_with_specific_approach(self):
        """Test chat request with specific approach"""
        chat_data = {
            "messages": [
                {"role": "user", "content": "What is AI?"},
                {"role": "assistant", "content": "AI is artificial intelligence."},
                {"role": "user", "content": "Tell me more about machine learning"},
            ],
            "session_state": "test-session-456",
        }

        response = client.post("/chat?approach=chat_read_retrieve_read", json=chat_data)

        assert response.status_code == 200
        data = response.json()
        assert data["context"]["approach_used"] == "ChatReadRetrieveRead"
        assert "chat_processed_at" in data["context"]

    def test_chat_endpoint_with_streaming(self):
        """Test chat request with streaming enabled"""
        chat_data = {
            "messages": [{"role": "user", "content": "Explain quantum computing"}],
            "session_state": "stream-session",
        }

        response = client.post("/chat?stream=true", json=chat_data)

        assert response.status_code == 200
        data = response.json()
        assert data["context"]["streaming"] is True

    def test_chat_endpoint_with_invalid_approach(self):
        """Test chat request with invalid approach (should fallback)"""
        chat_data = {"messages": [{"role": "user", "content": "Hello"}]}

        response = client.post("/chat?approach=nonexistent_approach", json=chat_data)

        assert response.status_code == 200
        data = response.json()
        # Should fallback to default approach
        assert "approach_used" in data["context"]

    def test_chat_endpoint_conversation_context(self):
        """Test chat with multiple messages for conversation context"""
        chat_data = {
            "messages": [
                {"role": "user", "content": "What is artificial intelligence?"},
                {
                    "role": "assistant",
                    "content": "AI refers to computer systems that can perform tasks typically requiring human intelligence.",
                },
                {"role": "user", "content": "Can you give me examples?"},
                {
                    "role": "assistant",
                    "content": "Examples include image recognition, natural language processing, and game playing.",
                },
                {"role": "user", "content": "How does machine learning fit into this?"},
            ]
        }

        response = client.post("/chat", json=chat_data)

        assert response.status_code == 200
        data = response.json()
        # With multiple messages, it should likely use ChatReadRetrieveRead
        assert data["context"]["approach_used"] in [
            "ChatReadRetrieveRead",
            "RetrieveThenRead",
        ]
        assert data["context"]["sources_count"] >= 0

    def test_chat_endpoint_session_management(self):
        """Test chat session state management"""
        chat_data = {
            "messages": [{"role": "user", "content": "Hello"}],
            "session_state": "session-management-test",
        }

        response = client.post("/chat", json=chat_data)

        assert response.status_code == 200
        data = response.json()
        assert data["session_state"] == "session-management-test"
        assert data["context"]["session_updated"] is True

    def test_chat_endpoint_approach_selection_complex_conversation(self):
        """Test that complex conversations get appropriate approach selection"""
        chat_data = {
            "messages": [
                {"role": "user", "content": "What is deep learning?"},
                {
                    "role": "assistant",
                    "content": "Deep learning is a subset of machine learning...",
                },
                {"role": "user", "content": "Can you elaborate on neural networks?"},
            ]
        }

        response = client.post("/chat", json=chat_data)

        assert response.status_code == 200
        data = response.json()
        # Complex conversation should likely use ChatReadRetrieveRead
        assert "approach_used" in data["context"]
        assert "chat_processed_at" in data["context"]


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
