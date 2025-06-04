import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock

from app.services.chat_service import ChatService
from app.services.ask_service import AskService
from app.services.vote_service import VoteService
from app.schemas.chat import ChatRequest, AskRequest, VoteRequest, ChatMessage


class TestCompleteWorkflows:
    """End-to-end tests for complete user workflows"""

    @pytest.mark.asyncio
    async def test_simple_chat_workflow(self):
        """Test basic chat workflow with approaches"""
        # Arrange
        chat_service = ChatService()
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello, how are you?")]
        )

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "ChatReadRetrieveReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Hello! I'm doing well, thank you for asking. How can I help you today?",
                                "context": {
                                    "data_points": ["Greeting context..."],
                                    "thoughts": "Friendly greeting response...",
                                    "followup_questions": [
                                        "<<Is there something specific I can help with?>>"
                                    ],
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(request)

            # Assert
            assert response.context["approach_used"] == "chat_read_retrieve_read"
            assert "Hello" in response.message.content

    @pytest.mark.asyncio
    async def test_simple_ask_workflow(self):
        """Test basic ask workflow with approaches"""
        # Arrange
        ask_service = AskService()
        request = AskRequest(user_query="What is artificial intelligence?")

        with patch("app.core.setup.get_ask_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "RetrieveThenReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Artificial Intelligence (AI) is a field of computer science...",
                                "context": {
                                    "data_points": [
                                        "AI definition document...",
                                        "Historical context...",
                                    ],
                                    "thoughts": "Comprehensive AI explanation...",
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask(request)

            # Assert
            assert response.context["approach_used"] == "retrieve_then_read"
            assert "artificial intelligence" in response.chatbot_response.lower()

    @pytest.mark.asyncio
    async def test_ask_and_vote_workflow(self):
        """Test ask followed by vote workflow"""
        # Arrange
        ask_service = AskService()
        vote_service = VoteService()

        ask_request = AskRequest(user_query="What is machine learning?")

        with patch("app.core.setup.get_ask_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "RetrieveThenReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Machine learning is a subset of AI...",
                                "context": {
                                    "data_points": ["ML definition..."],
                                    "thoughts": "ML explanation...",
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act - Ask
            ask_response = await ask_service.process_ask(ask_request)

            # Act - Vote
            vote_request = VoteRequest(
                user_query=ask_request.user_query,
                chatbot_response=ask_response.chatbot_response,
                upvote=True,
                count=1,
            )
            vote_response = await vote_service.process_vote(vote_request)

            # Assert
            assert ask_response.context["approach_used"] == "retrieve_then_read"
            assert vote_response.status == "success"
            assert vote_response.upvote is True

    @pytest.mark.asyncio
    async def test_streaming_workflow(self):
        """Test streaming workflow"""
        # Arrange
        chat_service = ChatService()
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Explain quantum computing")]
        )

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "ChatReadRetrieveReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Quantum computing is a revolutionary technology...",
                                "context": {
                                    "data_points": ["Quantum physics principles..."],
                                    "thoughts": "Complex quantum explanation...",
                                    "followup_questions": [
                                        "<<Would you like to know about qubits?>>"
                                    ],
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(request, stream=True)

            # Assert
            assert response.context["streaming"] is True
            assert response.context["approach_used"] == "chat_read_retrieve_read"
            assert "quantum" in response.message.content.lower()

    @pytest.mark.asyncio
    async def test_fallback_workflow(self):
        """Test fallback workflow when approaches fail"""
        # Arrange
        chat_service = ChatService()
        request = ChatRequest(messages=[ChatMessage(role="user", content="Hello")])

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_get_approach.side_effect = Exception("Approach failed")

            # Act
            response = await chat_service.process_chat(request)

            # Assert
            assert response.context["approach_used"] == "simple_fallback"
            assert response.context["fallback_reason"] == "approach_processing_failed"
            assert "Thank you" in response.message.content

    def test_complete_chat_conversation_workflow(self, client):
        """Test complete chat conversation through API endpoints"""
        # Step 1: Initial chat message
        chat_request = {
            "messages": [
                {"role": "user", "content": "Hello, I need help with my account"}
            ]
        }

        response = client.post("/chat", json=chat_request)
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        assert data["context"]["approach_used"] == "chat_read_retrieve_read"

    def test_ask_and_vote_workflow(self, client):
        """Test ask question followed by voting"""
        # Step 1: Ask a question
        ask_request = {"user_query": "What are the company policies on remote work?"}

        ask_response = client.post("/ask", json=ask_request)
        assert ask_response.status_code == 200

        ask_data = ask_response.json()
        assert "chatbot_response" in ask_data
        assert ask_data["context"]["approach_used"] == "retrieve_then_read"

        # Step 2: Vote on the response
        vote_request = {
            "user_query": ask_request["user_query"],
            "chatbot_response": ask_data["chatbot_response"],
            "upvote": True,
            "count": 1,
        }

        vote_response = client.post("/vote", json=vote_request)
        assert vote_response.status_code == 200

        vote_data = vote_response.json()
        assert vote_data["status"] == "success"
        assert vote_data["upvote"] is True
