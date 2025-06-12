"""
Test Suite for Clean Architecture Implementation
Demonstrates the testability benefits of the new architecture
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from app.repositories.search_repository import (
    SearchQuery,
    SearchResult,
    MockSearchRepository,
)
from app.repositories.llm_repository import (
    LLMRequest,
    LLMMessage,
    LLMResponse,
    MockLLMRepository,
)
from app.services.domain.query_processing_service import QueryProcessingService
from app.services.domain.response_generation_service import ResponseGenerationService
from app.services.orchestration.ask_orchestration_service import AskOrchestrationService
from app.services.orchestration.chat_orchestration_service import (
    ChatOrchestrationService,
)


class TestSearchRepository:
    """Test search repository implementations"""

    @pytest.mark.asyncio
    async def test_mock_search_repository(self):
        """Test mock search repository returns expected results"""
        repo = MockSearchRepository()

        query = SearchQuery(text="FastAPI framework", top_k=3)
        results = await repo.search(query)

        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        assert any("fastapi" in r.content.lower() for r in results)

    @pytest.mark.asyncio
    async def test_search_health_check(self):
        """Test search repository health check"""
        repo = MockSearchRepository()
        health = await repo.health_check()

        assert health["status"] == "healthy"
        assert health["service"] == "Mock Search"


class TestLLMRepository:
    """Test LLM repository implementations"""

    @pytest.mark.asyncio
    async def test_mock_llm_repository(self):
        """Test mock LLM repository generates responses"""
        repo = MockLLMRepository()

        request = LLMRequest(
            messages=[LLMMessage(role="user", content="What is FastAPI?")]
        )

        response = await repo.generate_response(request)

        assert isinstance(response, LLMResponse)
        assert response.content
        assert response.model == "mock-llm-v1"
        assert response.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_llm_pattern_matching(self):
        """Test LLM repository pattern-based responses"""
        repo = MockLLMRepository()

        request = LLMRequest(
            messages=[
                LLMMessage(role="user", content="Tell me about clean architecture")
            ]
        )

        response = await repo.generate_response(request)

        assert "clean architecture" in response.content.lower()


class TestQueryProcessingService:
    """Test query processing domain service"""

    @pytest.fixture
    def search_repository(self):
        """Mock search repository fixture"""
        return MockSearchRepository()

    @pytest.fixture
    def service(self, search_repository):
        """Query processing service fixture"""
        return QueryProcessingService(search_repository)

    @pytest.mark.asyncio
    async def test_query_processing_basic(self, service):
        """Test basic query processing"""
        result = await service.process_query("What is FastAPI?")

        assert result.original_query == "What is FastAPI?"
        assert result.enhanced_query
        assert result.search_results
        assert result.metadata

    @pytest.mark.asyncio
    async def test_query_enhancement_with_context(self, service):
        """Test query enhancement with context"""
        context = {"user_role": "developer", "domain": "web_frameworks"}

        result = await service.process_query("How do I create APIs?", context=context)

        assert result.metadata["context_used"] is True
        assert (
            "developer" in result.enhanced_query
            or "web_frameworks" in result.enhanced_query
        )

    @pytest.mark.asyncio
    async def test_technical_term_expansion(self, service):
        """Test technical term expansion"""
        result = await service.process_query("What is an API?")

        # Should expand "API" to include full term
        assert "application programming interface" in result.enhanced_query.lower()


class TestResponseGenerationService:
    """Test response generation domain service"""

    @pytest.fixture
    def llm_repository(self):
        """Mock LLM repository fixture"""
        return MockLLMRepository()

    @pytest.fixture
    def service(self, llm_repository):
        """Response generation service fixture"""
        return ResponseGenerationService(llm_repository)

    @pytest.fixture
    def sample_search_results(self):
        """Sample search results fixture"""
        return [
            SearchResult(
                content="FastAPI is a modern web framework",
                score=0.9,
                metadata={"type": "documentation"},
                source="FastAPI Docs",
            ),
            SearchResult(
                content="FastAPI supports async operations",
                score=0.8,
                metadata={"type": "feature"},
                source="Tutorial",
            ),
        ]

    @pytest.mark.asyncio
    async def test_response_generation(self, service, sample_search_results):
        """Test basic response generation"""
        result = await service.generate_response(
            query="What is FastAPI?", search_results=sample_search_results
        )

        assert result.content
        assert result.confidence > 0
        assert result.sources_used
        assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_chat_response_generation(self, service, sample_search_results):
        """Test chat response generation with history"""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
        ]

        result = await service.generate_chat_response(
            message="Tell me about FastAPI",
            conversation_history=history,
            search_results=sample_search_results,
            conversation_id="test-123",
        )

        assert result.content
        assert result.confidence > 0


class TestAskOrchestrationService:
    """Test ask orchestration service - demonstrates easy mocking"""

    @pytest.fixture
    def mock_query_service(self):
        """Mock query processing service"""
        service = AsyncMock()
        service.process_query.return_value = Mock(
            original_query="test query",
            enhanced_query="enhanced test query",
            search_results=[
                SearchResult(
                    content="Test content",
                    score=0.9,
                    metadata={"relevance_tier": "high"},
                    source="Test Source",
                )
            ],
            metadata={"results_count": 1},
        )
        return service

    @pytest.fixture
    def mock_response_service(self):
        """Mock response generation service"""
        service = AsyncMock()
        service.generate_response.return_value = Mock(
            content="Test response",
            confidence=0.8,
            sources_used=["Test Source"],
            processing_time_ms=100,
            model_info={"model": "test-model", "tokens_used": 50},
        )
        return service

    @pytest.fixture
    def orchestration_service(self, mock_query_service, mock_response_service):
        """Ask orchestration service with mocked dependencies"""
        return AskOrchestrationService(mock_query_service, mock_response_service)

    @pytest.mark.asyncio
    async def test_ask_orchestration(
        self, orchestration_service, mock_query_service, mock_response_service
    ):
        """Test complete ask orchestration workflow"""
        result = await orchestration_service.process_ask("What is FastAPI?")

        # Verify service interactions
        mock_query_service.process_query.assert_called_once()
        mock_response_service.generate_response.assert_called_once()

        # Verify response structure
        assert result["answer"] == "Test response"
        assert result["confidence"] == 0.8
        assert result["sources"]
        assert result["processing_time_ms"] > 0
        assert result["metadata"]

    @pytest.mark.asyncio
    async def test_ask_orchestration_with_context(
        self, orchestration_service, mock_query_service
    ):
        """Test ask orchestration with context"""
        context = {"user_role": "developer"}

        await orchestration_service.process_ask("How to use FastAPI?", context=context)

        # Verify context was passed to query service
        mock_query_service.process_query.assert_called_with(
            query="How to use FastAPI?", context=context, max_results=5
        )


class TestChatOrchestrationService:
    """Test chat orchestration service"""

    @pytest.fixture
    def mock_query_service(self):
        """Mock query processing service"""
        service = AsyncMock()
        service.process_query.return_value = Mock(
            search_results=[
                SearchResult(
                    content="Chat test content",
                    score=0.8,
                    metadata={"title": "Test Source"},
                    source="Chat Test",
                )
            ]
        )
        return service

    @pytest.fixture
    def mock_response_service(self):
        """Mock response generation service"""
        service = AsyncMock()
        service.generate_chat_response.return_value = Mock(
            content="Chat response", model_info={"model": "chat-model"}
        )
        return service

    @pytest.fixture
    def chat_service(self, mock_query_service, mock_response_service):
        """Chat orchestration service with mocked dependencies"""
        return ChatOrchestrationService(mock_query_service, mock_response_service)

    @pytest.mark.asyncio
    async def test_chat_orchestration(self, chat_service):
        """Test chat orchestration workflow"""
        result = await chat_service.process_chat("Hello, what is FastAPI?")

        assert result["response"] == "Chat response"
        assert result["conversation_id"]
        assert result["sources"]
        assert result["processing_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_conversation_history_management(self, chat_service):
        """Test conversation history management"""
        conversation_id = "test-conversation"

        # Send first message
        result1 = await chat_service.process_chat(
            "Hello", conversation_id=conversation_id
        )

        # Send second message
        result2 = await chat_service.process_chat(
            "What is FastAPI?", conversation_id=conversation_id
        )

        # Check history
        history = await chat_service.get_conversation_history(conversation_id)

        assert len(history) == 4  # 2 user messages + 2 assistant responses
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "What is FastAPI?"


class TestDependencyInjection:
    """Test dependency injection benefits"""

    def test_easy_service_replacement(self):
        """Demonstrate how easy it is to replace services for testing"""
        # Create mock repositories
        mock_search_repo = MockSearchRepository()
        mock_llm_repo = MockLLMRepository()

        # Create services with injected dependencies
        query_service = QueryProcessingService(mock_search_repo)
        response_service = ResponseGenerationService(mock_llm_repo)

        # Create orchestration service
        ask_service = AskOrchestrationService(query_service, response_service)

        # All dependencies are clearly defined and easily replaceable
        assert ask_service.query_processing_service == query_service
        assert ask_service.response_generation_service == response_service
        assert query_service.search_repository == mock_search_repo
        assert response_service.llm_repository == mock_llm_repo

    def test_service_isolation(self):
        """Test that services are properly isolated"""
        # Each service only depends on its direct dependencies
        search_repo = MockSearchRepository()
        query_service = QueryProcessingService(search_repo)

        # Query service doesn't know about LLM repositories
        assert not hasattr(query_service, "llm_repository")

        # LLM service doesn't know about search repositories
        llm_repo = MockLLMRepository()
        response_service = ResponseGenerationService(llm_repo)

        assert not hasattr(response_service, "search_repository")


# Integration test example
class TestIntegration:
    """Integration tests using real mock implementations"""

    @pytest.mark.asyncio
    async def test_full_ask_workflow_integration(self):
        """Test complete ask workflow with real mock services"""
        # Create real mock services (not mocked with AsyncMock)
        search_repo = MockSearchRepository()
        llm_repo = MockLLMRepository()

        query_service = QueryProcessingService(search_repo)
        response_service = ResponseGenerationService(llm_repo)
        ask_service = AskOrchestrationService(query_service, response_service)

        # Execute real workflow
        result = await ask_service.process_ask("What is clean architecture?")

        # Verify real integration
        assert result["answer"]
        assert "clean architecture" in result["answer"].lower()
        assert result["sources"]
        assert result["confidence"] > 0
        assert result["metadata"]["original_query"] == "What is clean architecture?"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
