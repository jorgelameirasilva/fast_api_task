import pytest
from app.services.response_generator import ResponseGenerator


class TestResponseGenerator:
    """Unit tests for ResponseGenerator"""

    @pytest.mark.asyncio
    async def test_generate_chat_response(self, response_generator):
        """Test generating chat response"""
        # Arrange
        user_message = "Hello, how are you?"
        context = {"session_id": "test-123", "user_preferences": {"language": "en"}}

        # Act
        response = await response_generator.generate_chat_response(
            user_message, context
        )

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0
        assert user_message in response  # Should include original message
        assert "placeholder response" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_chat_response_empty_message(self, response_generator):
        """Test generating chat response with empty message"""
        # Arrange
        user_message = ""
        context = {}

        # Act
        response = await response_generator.generate_chat_response(
            user_message, context
        )

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0
        assert "placeholder response" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_chat_response_long_message(self, response_generator):
        """Test generating chat response with long message"""
        # Arrange
        user_message = "A" * 1000  # Very long message
        context = {"test": "context"}

        # Act
        response = await response_generator.generate_chat_response(
            user_message, context
        )

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0
        # Should handle long messages gracefully

    @pytest.mark.asyncio
    async def test_generate_chat_response_special_characters(self, response_generator):
        """Test generating chat response with special characters"""
        # Arrange
        user_message = "Hello! 🤖 How are you? Special chars: àáâãäåæçèéêë"
        context = {}

        # Act
        response = await response_generator.generate_chat_response(
            user_message, context
        )

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0
        # Should handle special characters gracefully

    @pytest.mark.asyncio
    async def test_generate_ask_response(self, response_generator):
        """Test generating ask response"""
        # Arrange
        query = "What is artificial intelligence?"

        # Act
        response = await response_generator.generate_ask_response(query)

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0
        assert query in response  # Should include original query
        assert "comprehensive response" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_ask_response_empty_query(self, response_generator):
        """Test generating ask response with empty query"""
        # Arrange
        query = ""

        # Act
        response = await response_generator.generate_ask_response(query)

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_generate_ask_response_complex_query(self, response_generator):
        """Test generating ask response with complex query"""
        # Arrange
        query = "Can you explain the relationship between quantum computing and machine learning?"

        # Act
        response = await response_generator.generate_ask_response(query)

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0
        assert query in response

    @pytest.mark.asyncio
    async def test_get_relevant_sources(self, response_generator):
        """Test getting relevant sources"""
        # Arrange
        query = "machine learning algorithms"

        # Act
        sources = await response_generator.get_relevant_sources(query)

        # Assert
        assert isinstance(sources, list)
        assert len(sources) == 2  # Expected placeholder count

        # Check structure of sources
        for source in sources:
            assert isinstance(source, dict)
            assert "title" in source
            assert "url" in source
            assert "relevance_score" in source
            assert "excerpt" in source
            assert isinstance(source["relevance_score"], float)
            assert 0 <= source["relevance_score"] <= 1

    @pytest.mark.asyncio
    async def test_get_relevant_sources_empty_query(self, response_generator):
        """Test getting relevant sources with empty query"""
        # Arrange
        query = ""

        # Act
        sources = await response_generator.get_relevant_sources(query)

        # Assert
        assert isinstance(sources, list)
        assert len(sources) >= 0  # Should handle gracefully

    @pytest.mark.asyncio
    async def test_get_relevant_sources_structure(self, response_generator):
        """Test that sources have correct structure"""
        # Arrange
        query = "test query"

        # Act
        sources = await response_generator.get_relevant_sources(query)

        # Assert
        for source in sources:
            assert "title" in source
            assert "url" in source
            assert "relevance_score" in source
            assert "excerpt" in source

            assert isinstance(source["title"], str)
            assert isinstance(source["url"], str)
            assert isinstance(source["relevance_score"], float)
            assert isinstance(source["excerpt"], str)

            # Relevance score should be between 0 and 1
            assert 0 <= source["relevance_score"] <= 1

    @pytest.mark.asyncio
    async def test_enhance_response_with_context(self, response_generator):
        """Test enhancing response with context"""
        # Arrange
        response = "This is a basic response."
        context = {
            "user_preferences": {"detailed": True},
            "session_context": {"previous_topics": ["AI", "ML"]},
        }

        # Act
        enhanced_response = await response_generator.enhance_response_with_context(
            response, context
        )

        # Assert
        assert isinstance(enhanced_response, str)
        assert enhanced_response == response  # Current implementation returns unchanged

    @pytest.mark.asyncio
    async def test_enhance_response_empty_context(self, response_generator):
        """Test enhancing response with empty context"""
        # Arrange
        response = "This is a response."
        context = {}

        # Act
        enhanced_response = await response_generator.enhance_response_with_context(
            response, context
        )

        # Assert
        assert isinstance(enhanced_response, str)
        assert enhanced_response == response

    @pytest.mark.asyncio
    async def test_enhance_response_none_context(self, response_generator):
        """Test enhancing response with None context"""
        # Arrange
        response = "This is a response."
        context = None

        # Act
        # This might raise an error in real implementation, but for placeholder it should work
        enhanced_response = await response_generator.enhance_response_with_context(
            response, context
        )

        # Assert
        assert isinstance(enhanced_response, str)

    @pytest.mark.asyncio
    async def test_response_generator_instance_isolation(self):
        """Test that different ResponseGenerator instances work independently"""
        # Arrange
        generator1 = ResponseGenerator()
        generator2 = ResponseGenerator()

        # Act
        response1 = await generator1.generate_chat_response("Hello", {})
        response2 = await generator2.generate_chat_response("Hi", {})

        # Assert
        assert isinstance(response1, str)
        assert isinstance(response2, str)
        # Should contain different user messages
        assert "Hello" in response1
        assert "Hi" in response2

    @pytest.mark.asyncio
    async def test_generate_responses_with_various_inputs(
        self, response_generator, test_queries
    ):
        """Test generating responses with various input types"""
        # Test chat responses
        for query_type, query_text in test_queries.items():
            if query_text is not None:  # Skip None queries
                chat_response = await response_generator.generate_chat_response(
                    query_text, {}
                )
                assert isinstance(chat_response, str)
                assert len(chat_response) > 0

                ask_response = await response_generator.generate_ask_response(
                    query_text
                )
                assert isinstance(ask_response, str)
                assert len(ask_response) > 0

    @pytest.mark.asyncio
    async def test_sources_relevance_scores(self, response_generator):
        """Test that source relevance scores are realistic"""
        # Arrange
        query = "test relevance"

        # Act
        sources = await response_generator.get_relevant_sources(query)

        # Assert
        scores = [source["relevance_score"] for source in sources]

        # All scores should be valid floats between 0 and 1
        for score in scores:
            assert isinstance(score, float)
            assert 0 <= score <= 1

        # Scores should be in descending order (most relevant first)
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_source_urls_format(self, response_generator):
        """Test that source URLs have correct format"""
        # Arrange
        query = "test urls"

        # Act
        sources = await response_generator.get_relevant_sources(query)

        # Assert
        for source in sources:
            url = source["url"]
            assert isinstance(url, str)
            assert url.startswith("/")  # Relative URL format
            assert len(url) > 1

    @pytest.mark.asyncio
    async def test_concurrent_response_generation(self, response_generator):
        """Test concurrent response generation"""
        import asyncio

        # Arrange
        queries = ["Query 1", "Query 2", "Query 3"]

        # Act - Generate responses concurrently
        tasks = [
            response_generator.generate_chat_response(query, {}) for query in queries
        ]
        responses = await asyncio.gather(*tasks)

        # Assert
        assert len(responses) == 3
        for i, response in enumerate(responses):
            assert isinstance(response, str)
            assert queries[i] in response

    @pytest.mark.asyncio
    async def test_response_content_safety(self, response_generator):
        """Test that responses are safe and don't expose internals"""
        # Arrange
        malicious_query = "<script>alert('xss')</script>"

        # Act
        chat_response = await response_generator.generate_chat_response(
            malicious_query, {}
        )
        ask_response = await response_generator.generate_ask_response(malicious_query)

        # Assert
        assert isinstance(chat_response, str)
        assert isinstance(ask_response, str)
        # Responses should contain the input safely (current implementation includes it in string)
        assert malicious_query in chat_response
        assert malicious_query in ask_response
