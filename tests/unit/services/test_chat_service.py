import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage, ChatContext
from app.auth.models import AuthUser


class TestChatService:
    """Unit tests for ChatService"""

    @pytest.mark.asyncio
    async def test_process_chat_success(self, sample_chat_request):
        """Test successful chat processing"""
        # Arrange
        chat_service = ChatService()
        test_user = AuthUser(sub="test-user-123", email="test@example.com")

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "TestApproach"
            mock_approach.__class__.__name__ = "ChatReadRetrieveReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Based on conversation context and retrieved documents, here's the answer...",
                                "context": {
                                    "data_points": [
                                        "Conversation context...",
                                        "Retrieved documents...",
                                    ],
                                    "thoughts": "Conversation: ... Answer: ...",
                                    "followup_questions": [
                                        "<<Question 1?>>",
                                        "<<Question 2?>>",
                                    ],
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(
                request=sample_chat_request, current_user=test_user
            )

            # Assert
            assert isinstance(response, ChatResponse)
            assert len(response.choices) > 0
            choice = response.choices[0]
            assert choice.message.role == "assistant"
            assert "conversation context" in choice.message.content
            # Context is now in the choice content
            assert choice.content is not None
            assert len(choice.content.data_points) > 0
            assert choice.content.thoughts is not None

    @pytest.mark.asyncio
    async def test_process_chat_with_session_state(self, sample_chat_request):
        """Test chat processing with session state"""
        # Arrange
        chat_service = ChatService()
        test_user = AuthUser(sub="test-user-123", email="test@example.com")
        sample_chat_request.session_state = "test-session-123"

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "ChatReadRetrieveReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Session-aware response",
                                "context": {
                                    "data_points": ["Session context..."],
                                    "thoughts": "Using session state...",
                                    "followup_questions": [],
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(
                request=sample_chat_request, current_user=test_user
            )

            # Assert
            assert response.session_state == "test-session-123"
            # Context is now a ChatContext object, not a dict
            assert response.context is not None
            assert isinstance(response.context, ChatContext)

    @pytest.mark.asyncio
    async def test_process_chat_streaming(self, sample_chat_request):
        """Test chat processing with streaming"""
        # Arrange
        chat_service = ChatService()
        test_user = AuthUser(sub="test-user-123", email="test@example.com")

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "ChatReadRetrieveReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Streaming chat response",
                                "context": {
                                    "data_points": ["Streaming data..."],
                                    "thoughts": "Streaming thoughts...",
                                    "followup_questions": ["<<Follow up?>>"],
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(
                request=sample_chat_request, stream=True, current_user=test_user
            )

            # Assert
            assert response.context is not None
            assert len(response.choices) > 0
            choice = response.choices[0]
            # For streaming, we should have delta instead of message
            assert choice.delta is not None
            assert "Streaming chat response" in choice.delta.content

    @pytest.mark.asyncio
    async def test_process_chat_approach_failure(self, sample_chat_request):
        """Test chat processing when approach fails"""
        # Arrange
        chat_service = ChatService()
        test_user = AuthUser(sub="test-user-123", email="test@example.com")

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_get_approach.side_effect = Exception("Approach failed")

            # Act
            response = await chat_service.process_chat(
                request=sample_chat_request, current_user=test_user
            )

            # Assert
            # When approach fails, it falls back to simple processing
            assert response.context is not None
            assert len(response.choices) > 0
            choice = response.choices[0]
            assert choice.message is not None
            assert "Thank you for your message" in choice.message.content

    @pytest.mark.asyncio
    async def test_process_chat_empty_messages(self):
        """Test chat processing with empty messages"""
        # Arrange
        chat_service = ChatService()
        test_user = AuthUser(sub="test-user-123", email="test@example.com")
        request = ChatRequest(messages=[])

        # Act & Assert
        with pytest.raises(ValueError, match="No user message found"):
            await chat_service.process_chat(request=request, current_user=test_user)

    @pytest.mark.asyncio
    async def test_process_chat_no_user_messages(self):
        """Test chat processing with no user messages"""
        # Arrange
        chat_service = ChatService()
        test_user = AuthUser(sub="test-user-123", email="test@example.com")
        request = ChatRequest(
            messages=[
                ChatMessage(role="assistant", content="Hello"),
                ChatMessage(role="system", content="System message"),
            ]
        )

        # Act & Assert
        with pytest.raises(ValueError, match="No user message found"):
            await chat_service.process_chat(request=request, current_user=test_user)

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self):
        """Test processing multi-turn conversation"""
        # Arrange
        chat_service = ChatService()
        test_user = AuthUser(sub="test-user-123", email="test@example.com")
        messages = [
            ChatMessage(role="user", content="What is AI?"),
            ChatMessage(role="assistant", content="AI is artificial intelligence..."),
            ChatMessage(role="user", content="How does machine learning relate?"),
        ]
        request = ChatRequest(messages=messages)

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "ChatReadRetrieveReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Machine learning is a subset of AI that...",
                                "context": {
                                    "data_points": ["Previous conversation context..."],
                                    "thoughts": "Building on previous AI discussion...",
                                    "followup_questions": [
                                        "<<Would you like examples?>>"
                                    ],
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(
                request=request, current_user=test_user
            )

            # Assert
            assert isinstance(response, ChatResponse)
            assert len(response.choices) > 0
            choice = response.choices[0]
            assert choice.message is not None
            assert "machine learning" in choice.message.content.lower()

    @pytest.mark.asyncio
    async def test_process_chat_with_context(self):
        """Test chat processing with additional context"""
        # Arrange
        chat_service = ChatService()
        test_user = AuthUser(sub="test-user-123", email="test@example.com")

        # Create proper ChatContext with overrides
        from app.schemas.chat import ChatContext, Overrides

        context = ChatContext(overrides=Overrides(selected_category="test", top=5))

        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            context=context,
        )

        with patch("app.core.setup.get_chat_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "ChatReadRetrieveReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Hello! How can I help you today?",
                                "context": {
                                    "data_points": ["User context considered..."],
                                    "thoughts": "Responding with user preferences...",
                                    "followup_questions": [],
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(
                request=request, current_user=test_user
            )

            # Assert
            assert response.context is not None
            assert len(response.choices) > 0
            choice = response.choices[0]
            assert choice.message is not None
            assert "Hello" in choice.message.content
