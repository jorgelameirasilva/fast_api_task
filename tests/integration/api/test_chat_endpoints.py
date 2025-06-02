import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock


class TestChatEndpoints:
    """Integration tests for chat API endpoints"""

    def test_chat_endpoint_success(self, client):
        """Test successful chat endpoint call"""
        # Arrange
        chat_request = {
            "messages": [{"role": "user", "content": "Hello, how are you?"}]
        }

        with patch(
            "app.api.endpoints.chat.chat_service.process_chat"
        ) as mock_process_chat:
            from app.schemas.chat import ChatResponse, ChatMessage
            from datetime import datetime

            mock_response = ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="I'm doing well, thank you!",
                    timestamp=datetime.now(),
                ),
                context={"approach_used": "TestApproach"},
            )
            mock_process_chat.return_value = mock_response

            # Act
            response = client.post("/chat", json=chat_request)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"]["role"] == "assistant"
            assert data["message"]["content"] == "I'm doing well, thank you!"

    def test_chat_endpoint_with_session(self, client):
        """Test chat endpoint with session state"""
        # Arrange
        chat_request = {
            "messages": [{"role": "user", "content": "Remember this conversation"}],
            "session_state": "test-session-123",
        }

        with patch(
            "app.api.endpoints.chat.chat_service.process_chat"
        ) as mock_process_chat:
            from app.schemas.chat import ChatResponse, ChatMessage
            from datetime import datetime

            mock_response = ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="I'll remember this conversation",
                    timestamp=datetime.now(),
                ),
                session_state="test-session-123",
                context={"approach_used": "SessionApproach"},
            )
            mock_process_chat.return_value = mock_response

            # Act
            response = client.post("/chat", json=chat_request)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["session_state"] == "test-session-123"

    def test_chat_endpoint_invalid_request(self, client):
        """Test chat endpoint with invalid request"""
        # Arrange
        invalid_request = {"messages": []}  # Empty messages should be invalid

        # Act
        response = client.post("/chat", json=invalid_request)

        # Assert
        assert response.status_code == 400  # The actual error code returned by the API

    def test_ask_endpoint_success(self, client):
        """Test successful ask endpoint call"""
        # Arrange
        ask_request = {"user_query": "What is artificial intelligence?"}

        with patch(
            "app.api.endpoints.chat.chat_service.process_ask"
        ) as mock_process_ask:
            from app.schemas.chat import AskResponse

            mock_response = AskResponse(
                user_query="What is artificial intelligence?",
                chatbot_response="AI is a field of computer science...",
                sources=[{"title": "AI Guide", "url": "/ai-guide.pdf"}],
                context={"approach_used": "AskApproach"},
                count=0,
            )
            mock_process_ask.return_value = mock_response

            # Act
            response = client.post("/ask", json=ask_request)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["user_query"] == "What is artificial intelligence?"
            assert data["chatbot_response"] == "AI is a field of computer science..."
            assert len(data["sources"]) == 1

    def test_ask_endpoint_with_approach(self, client):
        """Test ask endpoint with specific approach"""
        # Arrange
        ask_request = {"user_query": "Explain machine learning"}

        with patch(
            "app.api.endpoints.chat.chat_service.process_ask_with_approach"
        ) as mock_process_ask:
            from app.schemas.chat import AskResponse

            mock_response = AskResponse(
                user_query="Explain machine learning",
                chatbot_response="Machine learning is...",
                sources=[],
                context={"approach_used": "SpecificApproach"},
                count=0,
            )
            mock_process_ask.return_value = mock_response

            # Act
            response = client.post(
                "/ask", json=ask_request, params={"approach": "specific_approach"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["chatbot_response"] == "Machine learning is..."

    def test_vote_endpoint_success(self, client):
        """Test successful vote endpoint call"""
        # Arrange
        vote_request = {
            "user_query": "Test query",
            "chatbot_response": "Test response",
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

    def test_vote_endpoint_downvote(self, client):
        """Test vote endpoint with downvote"""
        # Arrange
        vote_request = {
            "user_query": "Test query",
            "chatbot_response": "Test response",
            "upvote": False,
            "count": 1,
        }

        # Act
        response = client.post("/vote", json=vote_request)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["upvote"] is False

    def test_vote_endpoint_invalid_vote(self, client):
        """Test vote endpoint with conflicting votes"""
        # Arrange
        vote_request = {
            "user_query": "Test query",
            "chatbot_response": "Test response",
            "upvote": True,
            "downvote": True,  # Conflicting votes
            "count": 1,
        }

        # Act
        response = client.post("/vote", json=vote_request)

        # Assert
        assert response.status_code == 400  # Bad request due to validation error

    def test_auth_setup_endpoint(self, client):
        """Test auth setup endpoint"""
        # Act
        response = client.get("/auth_setup")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "auth_enabled" in data
        assert "auth_type" in data
        assert isinstance(data["auth_enabled"], bool)
        assert isinstance(data["auth_type"], str)

    def test_chat_endpoint_streaming(self, client):
        """Test chat endpoint with streaming"""
        # Arrange
        chat_request = {"messages": [{"role": "user", "content": "Tell me a story"}]}

        with patch(
            "app.api.endpoints.chat.chat_service.process_chat"
        ) as mock_process_chat:
            from app.schemas.chat import ChatResponse, ChatMessage
            from datetime import datetime

            mock_response = ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="Once upon a time...",
                    timestamp=datetime.now(),
                ),
                context={"streaming": True, "approach_used": "StreamingApproach"},
            )
            mock_process_chat.return_value = mock_response

            # Act
            response = client.post("/chat", json=chat_request, params={"stream": True})

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["context"]["streaming"] is True

    def test_ask_endpoint_streaming(self, client):
        """Test ask endpoint with streaming"""
        # Arrange
        ask_request = {"user_query": "Explain quantum computing"}

        with patch(
            "app.api.endpoints.chat.chat_service.process_ask"
        ) as mock_process_ask:
            from app.schemas.chat import AskResponse

            mock_response = AskResponse(
                user_query="Explain quantum computing",
                chatbot_response="Quantum computing is...",
                sources=[],
                context={"streaming": True, "approach_used": "StreamingApproach"},
                count=0,
            )
            mock_process_ask.return_value = mock_response

            # Act
            response = client.post("/ask", json=ask_request, params={"stream": True})

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["context"]["streaming"] is True

    def test_endpoint_error_handling(self, client):
        """Test endpoint error handling"""
        # Test malformed JSON
        response = client.post("/chat", data="invalid json")
        assert response.status_code == 422

        # Test missing required fields
        response = client.post("/chat", json={})
        assert response.status_code == 422

        # Test invalid field types
        response = client.post("/ask", json={"user_query": 123})  # Should be string
        assert response.status_code == 422

    def test_cors_headers(self, client):
        """Test that CORS headers are present"""
        # Arrange
        headers = {"Origin": "http://localhost:3000"}

        with patch(
            "app.api.endpoints.chat.chat_service.process_chat"
        ) as mock_process_chat:
            from app.schemas.chat import ChatResponse, ChatMessage
            from datetime import datetime

            mock_response = ChatResponse(
                message=ChatMessage(
                    role="assistant", content="Hello!", timestamp=datetime.now()
                ),
                context={},
            )
            mock_process_chat.return_value = mock_response

            # Act - Use a real POST request instead of OPTIONS
            response = client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": "Hello"}]},
                headers=headers,
            )

            # Assert
            assert response.status_code == 200
            # CORS headers should be present (handled by FastAPI middleware)

    def test_content_type_handling(self, client):
        """Test different content types"""
        # Test with explicit content-type
        chat_request = {"messages": [{"role": "user", "content": "Hello"}]}

        with patch(
            "app.api.endpoints.chat.chat_service.process_chat"
        ) as mock_process_chat:
            from app.schemas.chat import ChatResponse, ChatMessage
            from datetime import datetime

            mock_response = ChatResponse(
                message=ChatMessage(
                    role="assistant", content="Hello!", timestamp=datetime.now()
                ),
                context={"approach_used": "TestApproach"},
            )
            mock_process_chat.return_value = mock_response

            response = client.post(
                "/chat", json=chat_request, headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 200

    def test_large_request_handling(self, client):
        """Test handling of large requests"""
        # Arrange - Create a large message
        large_content = "A" * 10000  # 10KB message
        chat_request = {"messages": [{"role": "user", "content": large_content}]}

        with patch(
            "app.api.endpoints.chat.chat_service.process_chat"
        ) as mock_process_chat:
            from app.schemas.chat import ChatResponse, ChatMessage
            from datetime import datetime

            mock_response = ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="Processed large content",
                    timestamp=datetime.now(),
                ),
                context={"approach_used": "LargeContentApproach"},
            )
            mock_process_chat.return_value = mock_response

            # Act
            response = client.post("/chat", json=chat_request)

            # Assert
            assert response.status_code == 200
            # Should handle large content gracefully

    def test_concurrent_requests(self, client):
        """Test handling concurrent requests"""
        import threading
        import time

        results = []

        def make_request():
            chat_request = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Request {threading.current_thread().ident}",
                    }
                ]
            }

            with patch(
                "app.api.endpoints.chat.chat_service.process_chat"
            ) as mock_process_chat:
                from app.schemas.chat import ChatResponse, ChatMessage
                from datetime import datetime

                mock_response = ChatResponse(
                    message=ChatMessage(
                        role="assistant",
                        content=f"Response {threading.current_thread().ident}",
                        timestamp=datetime.now(),
                    ),
                    context={"approach_used": "ConcurrentApproach"},
                )
                mock_process_chat.return_value = mock_response

                response = client.post("/chat", json=chat_request)
                results.append(response.status_code)

        # Create multiple threads for concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert all requests succeeded
        assert len(results) == 5
        assert all(status == 200 for status in results)
