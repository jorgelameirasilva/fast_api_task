"""
Tests for ChatService helper methods that follow SOLID principles
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from app.services.chat_service import ChatService
from app.schemas.chat import (
    ChatMessage,
    ChatContext,
    Overrides,
    ChatChoice,
    ChatDelta,
    ChatContentData,
    ChatResponse,
)
from app.auth.models import AuthUser


class TestChatServiceHelpers:
    """Test the helper methods that implement Single Responsibility Principle"""

    def setup_method(self):
        """Setup for each test"""
        self.chat_service = ChatService()

    def test_convert_messages_for_approach(self):
        """Test message conversion for approach system"""
        # Arrange
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there"),
            ChatMessage(role="user", content="How are you?"),
        ]

        # Act
        result = self.chat_service._convert_messages_for_approach(messages)

        # Assert
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]
        assert result == expected

    def test_extract_overrides_with_context(self):
        """Test override extraction with valid context"""
        # Arrange
        overrides = Overrides(
            selected_category="test_category",
            top=5,
            retrieval_mode="hybrid",
            semantic_ranker=True,
        )
        context = ChatContext(overrides=overrides)

        # Act
        result = self.chat_service._extract_overrides(context)

        # Assert
        assert result["selected_category"] == "test_category"
        assert result["top"] == 5
        assert result["retrieval_mode"] == "hybrid"
        assert result["semantic_ranker"] is True

    def test_extract_overrides_without_context(self):
        """Test override extraction without context"""
        # Act
        result = self.chat_service._extract_overrides(None)

        # Assert
        assert result == {}

    def test_extract_overrides_empty_context(self):
        """Test override extraction with empty context"""
        # Arrange
        context = ChatContext()

        # Act
        result = self.chat_service._extract_overrides(context)

        # Assert
        assert result == {}

    @pytest.mark.asyncio
    async def test_update_session_if_needed_with_session(self):
        """Test session update when session_state is provided"""
        # Arrange
        mock_session_service = Mock()
        mock_session_service.update_session = AsyncMock()
        self.chat_service.session_service = mock_session_service

        # Act
        await self.chat_service._update_session_if_needed(
            "test-session-123", 5, "chat_approach"
        )

        # Assert
        mock_session_service.update_session.assert_called_once_with(
            "test-session-123", 5, "chat_approach"
        )

    @pytest.mark.asyncio
    async def test_update_session_if_needed_without_session(self):
        """Test session update when no session_state is provided"""
        # Arrange
        mock_session_service = Mock()
        self.chat_service.session_service = mock_session_service

        # Act
        await self.chat_service._update_session_if_needed(None, 5, "chat_approach")

        # Assert
        mock_session_service.update_session.assert_not_called()

    def test_create_chat_choice_from_approach_streaming(self):
        """Test creating ChatChoice for streaming responses"""
        # Arrange
        message_content = "This is a test response"
        message_context = {
            "data_points": ["point1", "point2"],
            "thoughts": "Processing user request",
        }
        choice = {"finish_reason": "stop"}

        # Act
        result = self.chat_service._create_chat_choice_from_approach(
            message_content, message_context, choice, stream=True
        )

        # Assert
        assert result.delta is not None
        assert result.delta.role == "assistant"
        assert result.delta.content == message_content
        assert result.message is None
        assert result.content.data_points == ["point1", "point2"]
        assert result.content.thoughts == "Processing user request"
        assert result.finish_reason == "stop"

    def test_create_chat_choice_from_approach_non_streaming(self):
        """Test creating ChatChoice for non-streaming responses"""
        # Arrange
        message_content = "This is a test response"
        message_context = {
            "data_points": ["point1", "point2"],
            "thoughts": "Processing user request",
        }
        choice = {"finish_reason": "stop"}

        # Act
        result = self.chat_service._create_chat_choice_from_approach(
            message_content, message_context, choice, stream=False
        )

        # Assert
        assert result.message is not None
        assert result.message.role == "assistant"
        assert result.message.content == message_content
        assert isinstance(result.message.timestamp, datetime)
        assert result.delta is None
        assert result.content.data_points == ["point1", "point2"]
        assert result.content.thoughts == "Processing user request"
        assert result.finish_reason == "stop"

    def test_create_simple_chat_choice_streaming(self):
        """Test creating simple ChatChoice for streaming"""
        # Arrange
        response_content = "Simple streaming response"

        # Act
        result = self.chat_service._create_simple_chat_choice(
            response_content, stream=True
        )

        # Assert
        assert result.delta is not None
        assert result.delta.role == "assistant"
        assert result.delta.content == response_content
        assert result.message is None

    def test_create_simple_chat_choice_non_streaming(self):
        """Test creating simple ChatChoice for non-streaming"""
        # Arrange
        response_content = "Simple non-streaming response"

        # Act
        result = self.chat_service._create_simple_chat_choice(
            response_content, stream=False
        )

        # Assert
        assert result.message is not None
        assert result.message.role == "assistant"
        assert result.message.content == response_content
        assert isinstance(result.message.timestamp, datetime)
        assert result.delta is None

    def test_build_response_context_with_overrides(self):
        """Test building response context with overrides"""
        # Arrange
        overrides = {
            "selected_category": "test",
            "top": 3,
            "retrieval_mode": "vector",
        }

        # Act
        result = self.chat_service._build_response_context(overrides)

        # Assert
        assert isinstance(result, ChatContext)
        assert result.overrides is not None
        assert result.overrides.selected_category == "test"
        assert result.overrides.top == 3
        assert result.overrides.retrieval_mode == "vector"

    def test_build_response_context_without_overrides(self):
        """Test building response context without overrides"""
        # Act
        result = self.chat_service._build_response_context({})

        # Assert
        assert isinstance(result, ChatContext)
        assert result.overrides is None

    def test_create_chat_response_from_approach_invalid_format(self):
        """Test creating ChatResponse with invalid approach result"""
        # Arrange
        from app.schemas.chat import ChatRequest

        invalid_result = {"invalid": "format"}
        request = ChatRequest(messages=[ChatMessage(role="user", content="test")])
        overrides = {}

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid approach result format"):
            self.chat_service._create_chat_response_from_approach(
                invalid_result, request, overrides, stream=False
            )

    def test_create_chat_response_from_approach_valid(self):
        """Test creating ChatResponse with valid approach result"""
        # Arrange
        from app.schemas.chat import ChatRequest

        approach_result = {
            "choices": [
                {
                    "message": {
                        "content": "Test response",
                        "context": {
                            "data_points": ["data1"],
                            "thoughts": "test thoughts",
                        },
                    },
                    "finish_reason": "stop",
                }
            ]
        }
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            session_state="test-session",
        )
        overrides = {"top": 3}

        # Act
        result = self.chat_service._create_chat_response_from_approach(
            approach_result, request, overrides, stream=False
        )

        # Assert
        assert isinstance(result, ChatResponse)
        assert len(result.choices) == 1
        assert result.choices[0].message.content == "Test response"
        assert result.session_state == "test-session"
        assert result.context.overrides.top == 3

    def test_create_simple_chat_response(self):
        """Test creating simple ChatResponse"""
        # Arrange
        from app.schemas.chat import ChatRequest

        response_content = "Simple response"
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            session_state="simple-session",
            context=ChatContext(),
        )

        # Act
        result = self.chat_service._create_simple_chat_response(
            response_content, request, stream=False
        )

        # Assert
        assert isinstance(result, ChatResponse)
        assert len(result.choices) == 1
        assert result.choices[0].message.content == "Simple response"
        assert result.session_state == "simple-session"
        assert result.context is not None


class TestChatServiceSeparationOfConcerns:
    """Test that the refactored service maintains separation of concerns"""

    def test_helper_methods_are_focused(self):
        """Test that each helper method has a single responsibility"""
        chat_service = ChatService()

        # Each method should be focused on one specific task
        methods_and_responsibilities = {
            "_convert_messages_for_approach": "Message format conversion",
            "_extract_overrides": "Context override extraction",
            "_update_session_if_needed": "Session management",
            "_create_chat_choice_from_approach": "ChatChoice creation from approach",
            "_create_simple_chat_choice": "Simple ChatChoice creation",
            "_build_response_context": "Response context building",
            "_create_chat_response_from_approach": "ChatResponse from approach result",
            "_create_simple_chat_response": "Simple ChatResponse creation",
        }

        # Verify all helper methods exist
        for method_name in methods_and_responsibilities.keys():
            assert hasattr(
                chat_service, method_name
            ), f"Method {method_name} should exist"

    def test_methods_follow_single_responsibility_principle(self):
        """Test that methods follow SRP by having clear, single purposes"""
        chat_service = ChatService()

        # Test that message conversion only handles message format
        messages = [ChatMessage(role="user", content="test")]
        converted = chat_service._convert_messages_for_approach(messages)
        assert isinstance(converted, list)
        assert all(isinstance(msg, dict) for msg in converted)

        # Test that override extraction only handles context extraction
        context = ChatContext(overrides=Overrides(top=5))
        overrides = chat_service._extract_overrides(context)
        assert isinstance(overrides, dict)
        assert "top" in overrides

        # Test that context building only handles context creation
        result_context = chat_service._build_response_context({"top": 3})
        assert isinstance(result_context, ChatContext)
