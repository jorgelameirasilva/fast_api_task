import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest, ChatMessage, ChatResponse


class TestChatService:
    """Unit tests for ChatService"""

    @pytest.mark.asyncio
    async def test_process_chat_success(
        self, sample_chat_request, mock_session_service, mock_response_generator
    ):
        """Test successful chat processing"""
        # Arrange
        chat_service = ChatService(mock_session_service, mock_response_generator)

        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "TestApproach"
            mock_approach.run = AsyncMock(
                return_value={"content": "Test response", "sources": [], "context": {}}
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(sample_chat_request)

            # Assert
            assert isinstance(response, ChatResponse)
            assert response.message.role == "assistant"
            assert response.message.content == "Test response"
            assert response.context["approach_used"] == "TestApproach"
            mock_session_service.update_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_with_explicit_approach(
        self, sample_chat_request, mock_session_service
    ):
        """Test chat processing with explicit approach"""
        # Arrange
        chat_service = ChatService(mock_session_service)

        with patch("app.services.chat_service.get_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "ExplicitApproach"
            mock_approach.run = AsyncMock(
                return_value={
                    "content": "Explicit response",
                    "sources": [],
                    "context": {},
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(
                sample_chat_request, approach_name="explicit_approach"
            )

            # Assert
            assert response.context["approach_used"] == "ExplicitApproach"
            mock_get_approach.assert_called_once_with("explicit_approach")

    @pytest.mark.asyncio
    async def test_process_chat_streaming(
        self, sample_chat_request, mock_session_service
    ):
        """Test chat processing with streaming"""
        # Arrange
        chat_service = ChatService(mock_session_service)

        async def mock_stream():
            yield {"partial": "content"}
            yield {"content": "Final content", "sources": []}

        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "StreamingApproach"
            mock_approach.run = AsyncMock(return_value=mock_stream())
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(sample_chat_request, stream=True)

            # Assert
            assert response.context["streaming"] is True
            assert response.message.content == "Final content"

    @pytest.mark.asyncio
    async def test_process_chat_no_user_message(self, mock_session_service):
        """Test chat processing with no user messages"""
        # Arrange
        chat_service = ChatService(mock_session_service)
        request = ChatRequest(
            messages=[ChatMessage(role="system", content="System message")]
        )

        # Act & Assert
        with pytest.raises(ValueError, match="No user message found"):
            await chat_service.process_chat(request)

    @pytest.mark.asyncio
    async def test_process_chat_approach_failure(
        self, sample_chat_request, mock_session_service
    ):
        """Test chat processing when approach fails"""
        # Arrange
        chat_service = ChatService(mock_session_service)

        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "FailingApproach"
            mock_approach.run = AsyncMock(side_effect=Exception("Approach failed"))
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(sample_chat_request)

            # Assert
            assert response.context["error"] == "chat_approach_execution_failed"
            assert response.context["fallback_used"] is True
            assert "I apologize" in response.message.content

    @pytest.mark.asyncio
    async def test_convert_messages(self, chat_service):
        """Test message conversion from ChatMessage to dict"""
        # Arrange
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
        ]

        # Act
        result = chat_service._convert_messages(messages)

        # Assert
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there!"}

    @pytest.mark.asyncio
    async def test_prepare_context(self, chat_service, sample_chat_request):
        """Test context preparation"""
        # Arrange
        messages = [{"role": "user", "content": "Hello"}]

        # Act
        context = chat_service._prepare_context(sample_chat_request, messages)

        # Assert
        assert context["overrides"] == {"test": "context"}
        assert context["auth_claims"] is None
        assert context["request_metadata"]["session_state"] == "test-session-123"
        assert context["request_metadata"]["message_count"] == 1
        assert context["request_metadata"]["chat_context"] is True

    @pytest.mark.asyncio
    async def test_get_approach_explicit(self, chat_service, sample_chat_request):
        """Test getting explicit approach"""
        # Arrange
        last_message = ChatMessage(role="user", content="Hello")

        with patch("app.services.chat_service.get_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "ExplicitApproach"
            mock_get_approach.return_value = mock_approach

            # Act
            result = chat_service._get_approach(
                sample_chat_request, "explicit_approach", last_message
            )

            # Assert
            assert result == mock_approach
            mock_get_approach.assert_called_once_with("explicit_approach")

    @pytest.mark.asyncio
    async def test_get_approach_automatic(self, chat_service, sample_chat_request):
        """Test automatic approach selection"""
        # Arrange
        last_message = ChatMessage(role="user", content="Hello")

        with patch("app.services.chat_service.get_best_approach") as mock_get_best:
            mock_approach = Mock()
            mock_approach.name = "AutoApproach"
            mock_get_best.return_value = mock_approach

            # Act
            result = chat_service._get_approach(sample_chat_request, None, last_message)

            # Assert
            assert result == mock_approach
            mock_get_best.assert_called_once_with(
                query="Hello", context={"request": sample_chat_request}, message_count=1
            )

    @pytest.mark.asyncio
    async def test_build_response_with_session(
        self, chat_service, sample_chat_request, mock_session_service
    ):
        """Test building response with session update"""
        # Arrange
        chat_service.session_service = mock_session_service
        result = {
            "content": "Response content",
            "sources": [{"title": "Source 1"}],
            "context": {"custom": "value"},
        }
        mock_approach = Mock()
        mock_approach.name = "TestApproach"

        # Act
        response = await chat_service._build_response(
            result, sample_chat_request, mock_approach, False
        )

        # Assert
        assert response.message.content == "Response content"
        assert response.session_state == "test-session-123"
        assert response.context["approach_used"] == "TestApproach"
        assert response.context["sources_count"] == 1
        assert response.context["session_updated"] is True
        mock_session_service.update_session.assert_called_once_with(
            "test-session-123", 2, "TestApproach"
        )

    @pytest.mark.asyncio
    async def test_build_response_without_session(
        self, chat_service, mock_session_service
    ):
        """Test building response without session"""
        # Arrange
        chat_service.session_service = mock_session_service
        request = ChatRequest(messages=[ChatMessage(role="user", content="Hello")])
        result = {"content": "Response", "sources": [], "context": {}}
        mock_approach = Mock()
        mock_approach.name = "TestApproach"

        # Act
        response = await chat_service._build_response(
            result, request, mock_approach, False
        )

        # Assert
        assert response.session_state is None
        assert response.context["session_updated"] is False
        mock_session_service.update_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_fallback_response(self, chat_service, sample_chat_request):
        """Test building fallback response"""
        # Act
        response = await chat_service._build_fallback_response(sample_chat_request)

        # Assert
        assert response.message.role == "assistant"
        assert "I apologize" in response.message.content
        assert response.context["error"] == "chat_approach_execution_failed"
        assert response.context["fallback_used"] is True
        assert "chat_processed_at" in response.context

    @pytest.mark.asyncio
    async def test_execute_approach_non_streaming(self, chat_service):
        """Test executing approach without streaming"""
        # Arrange
        mock_approach = Mock()
        expected_result = {"content": "Response"}
        mock_approach.run = AsyncMock(return_value=expected_result)
        messages = [{"role": "user", "content": "Hello"}]
        context = {}

        # Act
        result = await chat_service._execute_approach(
            mock_approach, messages, False, "session", context
        )

        # Assert
        assert result == expected_result
        mock_approach.run.assert_called_once_with(
            messages=messages, stream=False, session_state="session", context=context
        )

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(
        self, chat_service, multi_turn_conversation, mock_session_service
    ):
        """Test processing multi-turn conversation"""
        # Arrange
        chat_service.session_service = mock_session_service
        request = ChatRequest(messages=multi_turn_conversation)

        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "ChatReadRetrieveRead"
            mock_approach.run = AsyncMock(
                return_value={
                    "content": "Multi-turn response",
                    "sources": [],
                    "context": {},
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await chat_service.process_chat(request)

            # Assert
            assert response.message.content == "Multi-turn response"
            # Should use the last user message for approach selection
            mock_get_approach.assert_called_once()
            call_args = mock_get_approach.call_args[1]
            assert call_args["query"] == "How does machine learning relate?"
            assert call_args["message_count"] == 5
