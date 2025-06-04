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

        with patch("app.core.setup.get_ask_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "TestApproach"
            mock_approach.__class__.__name__ = "RetrieveThenReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Test ask response",
                                "context": {
                                    "data_points": [
                                        "Document 1: Information...",
                                        "Document 2: Context...",
                                    ],
                                    "thoughts": "Question: ... Answer: ...",
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask(sample_ask_request)

            # Assert
            assert isinstance(response, AskResponse)
            assert response.chatbot_response == "Test ask response"
            assert response.user_query == sample_ask_request.user_query
            assert response.context["approach_used"] == "retrieve_then_read"
            assert response.context["approach_type"] == "RetrieveThenReadApproach"
            assert len(response.sources) >= 1
            assert response.count == sample_ask_request.count or 0

    @pytest.mark.asyncio
    async def test_process_ask_with_streaming(self, sample_ask_request):
        """Test ask processing with streaming"""
        # Arrange
        ask_service = AskService()

        with patch("app.core.setup.get_ask_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "StreamingApproach"
            mock_approach.__class__.__name__ = "RetrieveThenReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "Streaming response",
                                "context": {
                                    "data_points": ["Streaming document data..."],
                                    "thoughts": "Streaming thoughts...",
                                },
                            }
                        }
                    ]
                }
            )
            mock_get_approach.return_value = mock_approach

            # Act
            response = await ask_service.process_ask(sample_ask_request, stream=True)

            # Assert
            assert response.context["streaming"] is True
            assert response.chatbot_response == "Streaming response"
            assert response.context["approach_used"] == "retrieve_then_read"

    @pytest.mark.asyncio
    async def test_process_ask_approach_failure(self, sample_ask_request):
        """Test ask processing when approach fails"""
        # Arrange
        ask_service = AskService()

        with patch("app.core.setup.get_ask_approach") as mock_get_approach:
            mock_get_approach.side_effect = Exception("Approach failed")

            # Act
            response = await ask_service.process_ask(sample_ask_request)

            # Assert
            assert response.context["approach_used"] == "simple_fallback"
            assert response.context["fallback_reason"] == "approach_processing_failed"
            assert "helpful response" in response.chatbot_response

    @pytest.mark.asyncio
    async def test_process_ask_minimal_query(self):
        """Test ask processing with minimal query"""
        # Arrange
        ask_service = AskService()
        request = AskRequest(user_query="?")  # Minimal valid query

        with patch("app.core.setup.get_ask_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "RetrieveThenReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "I need more information to help you.",
                                "context": {
                                    "data_points": [],
                                    "thoughts": "Minimal query received",
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
            assert isinstance(response, AskResponse)
            assert response.user_query == "?"
            assert response.context["approach_used"] == "retrieve_then_read"

    @pytest.mark.asyncio
    async def test_process_ask_with_context(self):
        """Test ask processing with previous context"""
        # Arrange
        ask_service = AskService()
        request = AskRequest(
            user_query="Can you explain more?",
            chatbot_response="AI is a technology...",
            count=5,
        )

        with patch("app.core.setup.get_ask_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "RetrieveThenReadApproach"
            mock_approach.run_without_streaming = AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "More detailed explanation...",
                                "context": {
                                    "data_points": ["Previous context considered..."],
                                    "thoughts": "Building on previous response...",
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
            assert response.count == 5
            assert response.context["approach_used"] == "retrieve_then_read"
            assert "More detailed explanation" in response.chatbot_response

    @pytest.mark.asyncio
    async def test_process_ask_various_queries(self):
        """Test ask processing with various query types"""
        ask_service = AskService()

        test_queries = [
            "What is machine learning?",
            "How does neural network work?",
            "Explain quantum computing",
            "What are the benefits of cloud computing?",
        ]

        with patch("app.core.setup.get_ask_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.__class__.__name__ = "RetrieveThenReadApproach"

            for query in test_queries:
                mock_approach.run_without_streaming = AsyncMock(
                    return_value={
                        "choices": [
                            {
                                "message": {
                                    "content": f"Detailed response about {query}",
                                    "context": {
                                        "data_points": [f"Information about {query}"],
                                        "thoughts": f"Analysis of {query}",
                                    },
                                }
                            }
                        ]
                    }
                )
                mock_get_approach.return_value = mock_approach

                # Act
                request = AskRequest(user_query=query)
                response = await ask_service.process_ask(request)

                # Assert
                assert isinstance(response, AskResponse)
                assert response.user_query == query
                assert response.context["approach_used"] == "retrieve_then_read"
                assert len(response.sources) >= 0
