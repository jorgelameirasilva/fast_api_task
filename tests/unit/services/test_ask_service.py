import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.ask_service import AskService
from app.schemas.chat import AskRequest, AskResponse


class TestAskService:
    """Unit tests for AskService"""

    @pytest.mark.asyncio
    async def test_process_ask_success(self, sample_ask_request):
        """Test successful ask processing"""
        # Arrange
        ask_service = AskService()

        with patch("app.services.ask_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "TestApproach"
            mock_approach.run = AsyncMock(
                return_value={
                    "content": "Test ask response",
                    "sources": [{"title": "Source 1", "url": "/test.pdf"}],
                    "context": {"relevance": 0.95},
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask(sample_ask_request)

            # Assert
            assert isinstance(response, AskResponse)
            assert response.chatbot_response == "Test ask response"
            assert response.user_query == sample_ask_request.user_query
            assert response.context["approach_used"] == "TestApproach"
            assert len(response.sources) == 1
            assert response.count == 1

    @pytest.mark.asyncio
    async def test_process_ask_with_streaming(self, sample_ask_request):
        """Test ask processing with streaming"""
        # Arrange
        ask_service = AskService()

        async def mock_stream():
            yield {"partial": "content"}
            yield {"content": "Final streaming response", "sources": []}

        with patch("app.services.ask_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "StreamingApproach"
            mock_approach.run = AsyncMock(return_value=mock_stream())
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask(sample_ask_request, stream=True)

            # Assert
            assert response.context["streaming"] is True
            assert response.chatbot_response == "Final streaming response"

    @pytest.mark.asyncio
    async def test_process_ask_with_approach(self, sample_ask_request):
        """Test ask processing with specific approach"""
        # Arrange
        ask_service = AskService()

        with patch("app.services.ask_service.get_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "SpecificApproach"
            mock_approach.run = AsyncMock(
                return_value={
                    "content": "Specific approach response",
                    "sources": [],
                    "context": {},
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask_with_approach(
                sample_ask_request, "specific_approach", stream=False
            )

            # Assert
            assert response.context["approach_used"] == "SpecificApproach"
            assert (
                response.context["explicit_approach_requested"] == "specific_approach"
            )
            mock_get_approach.assert_called_once_with("specific_approach")

    @pytest.mark.asyncio
    async def test_process_ask_approach_failure(self, sample_ask_request):
        """Test ask processing when approach fails"""
        # Arrange
        ask_service = AskService()

        with patch("app.services.ask_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "FailingApproach"
            mock_approach.run = AsyncMock(side_effect=Exception("Approach failed"))
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask(sample_ask_request)

            # Assert
            assert response.context["error"] == "approach_execution_failed"
            assert response.context["fallback_used"] is True
            assert "I apologize" in response.chatbot_response

    @pytest.mark.asyncio
    async def test_create_messages_with_chatbot_response(self, ask_service):
        """Test creating messages with existing chatbot response"""
        # Arrange
        request = AskRequest(
            user_query="Follow-up question", chatbot_response="Previous response"
        )

        # Act
        messages = ask_service._create_messages(request)

        # Assert
        assert len(messages) == 2
        assert messages[0] == {"role": "assistant", "content": "Previous response"}
        assert messages[1] == {"role": "user", "content": "Follow-up question"}

    @pytest.mark.asyncio
    async def test_create_messages_without_chatbot_response(self, ask_service):
        """Test creating messages without existing chatbot response"""
        # Arrange
        request = AskRequest(user_query="New question")

        # Act
        messages = ask_service._create_messages(request)

        # Assert
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "New question"}

    @pytest.mark.asyncio
    async def test_get_best_approach(self, ask_service, sample_ask_request):
        """Test getting best approach for ask request"""
        # Arrange
        messages = [{"role": "user", "content": "Test query"}]

        with patch("app.services.ask_service.get_best_approach") as mock_get_best:
            mock_approach = Mock()
            mock_approach.name = "BestApproach"
            mock_get_best.return_value = mock_approach

            # Act
            result = ask_service._get_best_approach(sample_ask_request, messages)

            # Assert
            assert result == mock_approach
            mock_get_best.assert_called_once_with(
                query=sample_ask_request.user_query,
                context={"request": sample_ask_request},
                message_count=1,
            )

    @pytest.mark.asyncio
    async def test_prepare_context(self, ask_service, sample_ask_request):
        """Test context preparation for ask request"""
        # Act
        context = ask_service._prepare_context(sample_ask_request)

        # Assert
        assert context["overrides"] == {}
        assert context["auth_claims"] is None
        assert context["request_metadata"]["count"] == sample_ask_request.count
        assert context["request_metadata"]["upvote"] == sample_ask_request.upvote
        assert (
            context["request_metadata"]["user_query_vector"]
            == sample_ask_request.user_query_vector
        )

    @pytest.mark.asyncio
    async def test_execute_approach_non_streaming(self, ask_service):
        """Test executing approach without streaming"""
        # Arrange
        mock_approach = Mock()
        expected_result = {"content": "Response", "sources": []}
        mock_approach.run = AsyncMock(return_value=expected_result)
        messages = [{"role": "user", "content": "Query"}]
        context = {}

        # Act
        result = await ask_service._execute_approach(
            mock_approach, messages, False, context
        )

        # Assert
        assert result == expected_result
        mock_approach.run.assert_called_once_with(
            messages=messages, stream=False, session_state=None, context=context
        )

    @pytest.mark.asyncio
    async def test_execute_approach_streaming(self, ask_service):
        """Test executing approach with streaming"""

        # Arrange
        async def mock_stream():
            yield {"partial": "content"}
            yield {"content": "Final", "sources": []}

        mock_approach = Mock()
        mock_approach.run = AsyncMock(return_value=mock_stream())
        messages = [{"role": "user", "content": "Query"}]
        context = {}

        # Act
        result = await ask_service._execute_approach(
            mock_approach, messages, True, context
        )

        # Assert
        assert result["content"] == "Final"
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_build_response(self, ask_service, sample_ask_request):
        """Test building ask response"""
        # Arrange
        result = {
            "content": "Response content",
            "sources": [{"title": "Source", "url": "/test.pdf"}],
            "context": {"custom": "value"},
        }
        mock_approach = Mock()
        mock_approach.name = "TestApproach"

        # Act
        response = ask_service._build_response(
            result, sample_ask_request, mock_approach, True
        )

        # Assert
        assert response.user_query == sample_ask_request.user_query
        assert response.chatbot_response == "Response content"
        assert response.sources == result["sources"]
        assert response.context["approach_used"] == "TestApproach"
        assert response.context["streaming"] is True
        assert "query_processed_at" in response.context

    @pytest.mark.asyncio
    async def test_build_fallback_response(self, ask_service, sample_ask_request):
        """Test building fallback response"""
        # Act
        response = ask_service._build_fallback_response(sample_ask_request)

        # Assert
        assert response.user_query == sample_ask_request.user_query
        assert "I apologize" in response.chatbot_response
        assert sample_ask_request.user_query in response.chatbot_response
        assert response.context["error"] == "approach_execution_failed"
        assert response.context["fallback_used"] is True
        assert response.sources == []

    @pytest.mark.asyncio
    async def test_process_ask_with_various_queries(self, test_queries):
        """Test ask processing with various query types"""
        # Arrange
        ask_service = AskService()

        with patch("app.services.ask_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "TestApproach"
            mock_approach.run = AsyncMock(
                return_value={"content": "Response", "sources": [], "context": {}}
            )
            mock_get_approach.return_value = mock_approach

            # Test each query type
            for query_type, query_text in test_queries.items():
                if query_text:  # Skip empty queries for this test
                    request = AskRequest(user_query=query_text)

                    # Act
                    response = await ask_service.process_ask(request)

                    # Assert
                    assert isinstance(response, AskResponse)
                    assert response.user_query == query_text

    @pytest.mark.asyncio
    async def test_process_ask_empty_query(self):
        """Test ask processing with minimal query"""
        # Arrange
        ask_service = AskService()
        request = AskRequest(user_query="?")  # Minimal valid query

        with patch("app.services.ask_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "TestApproach"
            mock_approach.run = AsyncMock(
                return_value={
                    "content": "Please provide a more specific question",
                    "sources": [],
                    "context": {},
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask(request)

            # Assert
            assert response.user_query == "?"
            assert isinstance(response, AskResponse)

    @pytest.mark.asyncio
    async def test_process_ask_with_explicit_approach_streaming(
        self, sample_ask_request
    ):
        """Test ask processing with explicit approach and streaming"""
        # Arrange
        ask_service = AskService()

        async def mock_stream():
            yield {"content": "Streaming response", "sources": []}

        with patch("app.services.ask_service.get_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "ExplicitStreamingApproach"
            mock_approach.run = AsyncMock(return_value=mock_stream())
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask_with_approach(
                sample_ask_request, "explicit_streaming", stream=True
            )

            # Assert
            assert response.context["streaming"] is True
            assert (
                response.context["explicit_approach_requested"] == "explicit_streaming"
            )
            assert response.chatbot_response == "Streaming response"
