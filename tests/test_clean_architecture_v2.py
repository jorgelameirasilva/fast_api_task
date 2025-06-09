"""
Comprehensive tests for Clean Architecture V2.
These tests demonstrate the testability benefits of the new architecture.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from app.schemas.chat import (
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    ChatMessage,
)
from app.repositories.search_repository import (
    SearchRepository,
    SearchQuery,
    SearchResult,
    MockSearchRepository,
)
from app.repositories.llm_repository import (
    LLMRepository,
    LLMRequest,
    LLMResponse,
    MockLLMRepository,
)
from app.services.query_processing_service import QueryProcessingService
from app.services.response_generation_service import ResponseGenerationService
from app.services.ask_orchestration_service import AskOrchestrationService
from app.services.chat_orchestration_service import ChatOrchestrationService


class TestRepositories:
    """Test repository interfaces and implementations"""

    @pytest.mark.asyncio
    async def test_mock_search_repository(self):
        """Test that mock search repository works correctly"""
        repo = MockSearchRepository()

        query = SearchQuery(query="test health benefits", top_k=3)
        results = await repo.search(query)

        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.relevance_score > 0 for r in results)

        # Test health check
        health = await repo.health_check()
        assert health is True

    @pytest.mark.asyncio
    async def test_mock_llm_repository(self):
        """Test that mock LLM repository works correctly"""
        custom_responses = ["Custom response 1", "Custom response 2"]
        repo = MockLLMRepository(responses=custom_responses)

        # Test response generation
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test question"}], temperature=0.7
        )
        response = await repo.generate_response(request)

        assert isinstance(response, LLMResponse)
        assert response.content in custom_responses
        assert response.usage_tokens["total"] > 0

        # Test health check
        health = await repo.health_check()
        assert health is True

    @pytest.mark.asyncio
    async def test_repository_abstraction(self):
        """Test that repositories properly abstract implementations"""
        search_repo = MockSearchRepository()
        llm_repo = MockLLMRepository()

        # Test that they implement the correct interfaces
        assert isinstance(search_repo, SearchRepository)
        assert isinstance(llm_repo, LLMRepository)

        # Test that methods work as expected
        search_results = await search_repo.search(SearchQuery("test"))
        assert len(search_results) > 0

        llm_response = await llm_repo.generate_response(
            LLMRequest(messages=[{"role": "user", "content": "test"}])
        )
        assert llm_response.content


class TestDomainServices:
    """Test domain services with mocked dependencies"""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories for testing"""
        search_repo = MockSearchRepository()
        llm_repo = MockLLMRepository(
            [
                "Enhanced query for employee benefits",
                "Based on the retrieved documents, here's your answer...",
            ]
        )
        return search_repo, llm_repo

    @pytest.mark.asyncio
    async def test_query_processing_service(self, mock_repositories):
        """Test query processing service"""
        search_repo, llm_repo = mock_repositories
        service = QueryProcessingService(search_repo, llm_repo)

        # Test query processing
        processed_query = await service.process_user_query(
            "health benefits", context={"request_type": "ask"}
        )

        assert isinstance(processed_query, SearchQuery)
        assert processed_query.query == "health benefits"  # Short query, no enhancement
        assert processed_query.top_k == 5

        # Test document search
        search_results = await service.search_documents(processed_query)
        assert len(search_results) > 0
        assert all(isinstance(r, SearchResult) for r in search_results)

    @pytest.mark.asyncio
    async def test_response_generation_service(self, mock_repositories):
        """Test response generation service"""
        _, llm_repo = mock_repositories
        service = ResponseGenerationService(llm_repo)

        # Create mock search results
        search_results = [
            SearchResult(
                content="Healthcare benefits include medical, dental, and vision",
                source="benefits_guide.pdf",
                title="Healthcare Benefits",
                relevance_score=0.95,
            )
        ]

        # Test response generation
        response = await service.generate_contextual_response(
            user_query="What healthcare benefits do we have?",
            search_results=search_results,
            response_type="ask",
        )

        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_query_enhancement(self, mock_repositories):
        """Test query enhancement for short queries"""
        search_repo, llm_repo = mock_repositories
        service = QueryProcessingService(search_repo, llm_repo)

        # Test with a short query that should be enhanced
        processed_query = await service.process_user_query("PTO", context={})

        # Should still work even if enhancement fails/is skipped
        assert isinstance(processed_query, SearchQuery)
        assert processed_query.query in ["PTO", "Enhanced query for employee benefits"]


class TestOrchestrationServices:
    """Test orchestration services that coordinate workflows"""

    @pytest.fixture
    def mock_services(self):
        """Create mock domain services for testing"""
        search_repo = MockSearchRepository()
        llm_repo = MockLLMRepository(
            [
                "Based on the employee handbook, here's information about your question: This is a comprehensive answer about healthcare benefits including medical, dental, and vision coverage."
            ]
        )

        query_processor = QueryProcessingService(search_repo, llm_repo)
        response_generator = ResponseGenerationService(llm_repo)

        return query_processor, response_generator

    @pytest.mark.asyncio
    async def test_ask_orchestration_service(self, mock_services):
        """Test ask orchestration end-to-end workflow"""
        query_processor, response_generator = mock_services
        orchestrator = AskOrchestrationService(query_processor, response_generator)

        # Create test request
        request = AskRequest(
            user_query="What healthcare benefits are available?", count=1
        )

        # Test orchestration
        response = await orchestrator.process_ask_request(request, stream=False)

        # Verify response structure
        assert isinstance(response, AskResponse)
        assert response.user_query == request.user_query
        assert len(response.chatbot_response) > 0
        assert response.context["approach"] == "retrieve_then_read"
        assert response.context["documents_found"] >= 0
        assert len(response.sources) > 0

    @pytest.mark.asyncio
    async def test_chat_orchestration_service(self, mock_services):
        """Test chat orchestration with conversation context"""
        query_processor, response_generator = mock_services
        orchestrator = ChatOrchestrationService(query_processor, response_generator)

        # Create test chat request with conversation history
        messages = [
            ChatMessage(role="user", content="Hi, I have questions about benefits"),
            ChatMessage(
                role="assistant", content="I'd be happy to help with benefit questions!"
            ),
            ChatMessage(role="user", content="What healthcare options do I have?"),
        ]

        request = ChatRequest(messages=messages, session_state="test-session-123")

        # Test orchestration
        response = await orchestrator.process_chat_request(request, stream=False)

        # Verify response structure
        assert isinstance(response, ChatResponse)
        assert response.message.role == "assistant"
        assert len(response.message.content) > 0
        assert response.session_state == request.session_state
        assert response.context["approach"] == "chat_read_retrieve_read"
        assert response.context["conversation_length"] == 3

    @pytest.mark.asyncio
    async def test_error_handling_in_orchestration(self, mock_services):
        """Test that orchestration services handle errors gracefully"""
        query_processor, response_generator = mock_services

        # Create a failing query processor
        failing_processor = Mock(spec=QueryProcessingService)
        failing_processor.process_user_query = AsyncMock(
            side_effect=Exception("Search failed")
        )

        orchestrator = AskOrchestrationService(failing_processor, response_generator)

        request = AskRequest(user_query="test query")
        response = await orchestrator.process_ask_request(request)

        # Should return error response, not raise exception
        assert isinstance(response, AskResponse)
        assert response.context["error"] is True
        assert "error_message" in response.context


class TestDependencyInjection:
    """Test dependency injection and service composition"""

    def test_service_composition(self):
        """Test that services can be composed with different dependencies"""
        # Create different repository implementations
        search_repo1 = MockSearchRepository()
        search_repo2 = MockSearchRepository()
        llm_repo = MockLLMRepository()

        # Create services with different dependencies
        query_processor1 = QueryProcessingService(search_repo1, llm_repo)
        query_processor2 = QueryProcessingService(search_repo2, llm_repo)

        # Verify services have different repository instances
        assert (
            query_processor1.search_repository is not query_processor2.search_repository
        )
        assert query_processor1.llm_repository is query_processor2.llm_repository

    def test_orchestration_service_composition(self):
        """Test that orchestration services can be composed with different domain services"""
        search_repo = MockSearchRepository()
        llm_repo1 = MockLLMRepository(["Response from LLM 1"])
        llm_repo2 = MockLLMRepository(["Response from LLM 2"])

        # Create different response generators
        response_gen1 = ResponseGenerationService(llm_repo1)
        response_gen2 = ResponseGenerationService(llm_repo2)

        query_processor = QueryProcessingService(search_repo, llm_repo1)

        # Create orchestrators with different response generators
        orchestrator1 = AskOrchestrationService(query_processor, response_gen1)
        orchestrator2 = AskOrchestrationService(query_processor, response_gen2)

        assert orchestrator1.response_generator is not orchestrator2.response_generator


class TestIntegration:
    """Integration tests that test the full flow"""

    @pytest.mark.asyncio
    async def test_full_ask_flow_with_mocks(self):
        """Test complete ask flow with all mock dependencies"""
        # Setup
        search_repo = MockSearchRepository()
        llm_repo = MockLLMRepository(
            [
                "Based on the employee documentation, healthcare benefits include comprehensive medical coverage, dental insurance, and vision care. You can enroll during open enrollment or within 30 days of hire."
            ]
        )

        # Create services
        query_processor = QueryProcessingService(search_repo, llm_repo)
        response_generator = ResponseGenerationService(llm_repo)
        orchestrator = AskOrchestrationService(query_processor, response_generator)

        # Execute
        request = AskRequest(user_query="What healthcare benefits do we offer?")
        response = await orchestrator.process_ask_request(request)

        # Verify complete flow
        assert response.user_query == request.user_query
        assert "healthcare" in response.chatbot_response.lower()
        assert len(response.sources) > 0
        assert response.context["approach"] == "retrieve_then_read"

    @pytest.mark.asyncio
    async def test_full_chat_flow_with_mocks(self):
        """Test complete chat flow with conversation context"""
        # Setup
        search_repo = MockSearchRepository()
        llm_repo = MockLLMRepository(
            [
                "Continuing our conversation about benefits, the 401k plan allows you to contribute up to $22,500 per year with company matching up to 6% of your salary."
            ]
        )

        # Create services
        query_processor = QueryProcessingService(search_repo, llm_repo)
        response_generator = ResponseGenerationService(llm_repo)
        orchestrator = ChatOrchestrationService(query_processor, response_generator)

        # Execute
        messages = [
            ChatMessage(role="user", content="Tell me about employee benefits"),
            ChatMessage(
                role="assistant", content="I can help with benefit information!"
            ),
            ChatMessage(role="user", content="What about retirement plans?"),
        ]
        request = ChatRequest(messages=messages)
        response = await orchestrator.process_chat_request(request)

        # Verify complete flow
        assert response.message.role == "assistant"
        assert (
            "401k" in response.message.content
            or "retirement" in response.message.content.lower()
        )
        assert response.context["conversation_length"] == 3


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
