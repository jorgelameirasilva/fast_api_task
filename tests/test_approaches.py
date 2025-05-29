"""
Tests for the approaches system.
"""

import pytest
from app.approaches import (
    get_approach,
    get_best_approach,
    list_available_approaches,
    register_approach,
    BaseApproach,
    ChatReadRetrieveReadApproach,
    RetrieveThenReadApproach,
)


class TestApproachRegistry:
    """Test approach registry functionality"""

    def test_list_available_approaches(self):
        """Test listing available approaches"""
        approaches = list_available_approaches()

        assert isinstance(approaches, dict)
        assert "retrieve_then_read" in approaches
        assert "chat_read_retrieve_read" in approaches
        assert "default" in approaches

    def test_get_default_approach(self):
        """Test getting default approach"""
        approach = get_approach()

        assert isinstance(approach, BaseApproach)
        assert approach.name == "RetrieveThenRead"

    def test_get_specific_approach(self):
        """Test getting specific approaches"""
        # Test RetrieveThenRead
        rtr_approach = get_approach("retrieve_then_read")
        assert isinstance(rtr_approach, RetrieveThenReadApproach)
        assert rtr_approach.name == "RetrieveThenRead"

        # Test ChatReadRetrieveRead
        crrr_approach = get_approach("chat_read_retrieve_read")
        assert isinstance(crrr_approach, ChatReadRetrieveReadApproach)
        assert crrr_approach.name == "ChatReadRetrieveRead"

    def test_get_approach_case_insensitive(self):
        """Test that approach names are case insensitive"""
        approach1 = get_approach("RETRIEVE_THEN_READ")
        approach2 = get_approach("retrieve_then_read")
        approach3 = get_approach("Retrieve_Then_Read")

        assert approach1.name == approach2.name == approach3.name

    def test_get_nonexistent_approach_fallback(self):
        """Test that non-existent approaches fall back to default"""
        approach = get_approach("nonexistent_approach")

        # Should fall back to default
        assert isinstance(approach, RetrieveThenReadApproach)
        assert approach.name == "RetrieveThenRead"

    def test_best_approach_selection(self):
        """Test automatic best approach selection"""
        # Simple query should use RetrieveThenRead
        simple_approach = get_best_approach("What is AI?", message_count=1)
        assert isinstance(simple_approach, RetrieveThenReadApproach)

        # Multi-turn conversation should use ChatReadRetrieveRead
        complex_approach = get_best_approach("Tell me more", message_count=5)
        assert isinstance(complex_approach, ChatReadRetrieveReadApproach)

        # Contextual query should use ChatReadRetrieveRead
        contextual_approach = get_best_approach(
            "Can you elaborate on that?", message_count=2
        )
        assert isinstance(contextual_approach, ChatReadRetrieveReadApproach)


class TestBaseApproach:
    """Test base approach functionality"""

    def test_build_filter_no_overrides(self):
        """Test filter building with no overrides"""
        approach = get_approach("retrieve_then_read")
        filter_result = approach.build_filter({})

        assert filter_result is None

    def test_build_filter_with_category(self):
        """Test filter building with category"""
        approach = get_approach("retrieve_then_read")
        overrides = {"selected_category": "technical"}
        filter_result = approach.build_filter(overrides)

        assert filter_result == "category eq 'technical'"

    def test_build_filter_with_none_category(self):
        """Test filter building with None category"""
        approach = get_approach("retrieve_then_read")
        overrides = {"selected_category": "none"}
        filter_result = approach.build_filter(overrides)

        assert filter_result is None

    def test_format_response(self):
        """Test response formatting"""
        approach = get_approach("retrieve_then_read")

        response = approach.format_response(
            content="Test response",
            sources=[{"title": "Test Doc", "url": "/test.pdf"}],
            context={"test": True},
        )

        assert response["content"] == "Test response"
        assert len(response["sources"]) == 1
        assert response["context"]["test"] is True
        assert response["approach"] == "RetrieveThenRead"
        assert "timestamp" in response


class TestRetrieveThenReadApproach:
    """Test RetrieveThenRead approach"""

    @pytest.mark.asyncio
    async def test_run_simple_query(self):
        """Test running a simple query"""
        approach = RetrieveThenReadApproach()
        messages = [{"role": "user", "content": "What is artificial intelligence?"}]

        result = await approach.run(messages)

        assert isinstance(result, dict)
        assert "content" in result
        assert "sources" in result
        assert "context" in result
        assert result["approach"] == "RetrieveThenRead"

    @pytest.mark.asyncio
    async def test_run_policy_query(self):
        """Test running a policy-related query"""
        approach = RetrieveThenReadApproach()
        messages = [
            {"role": "user", "content": "What is our company policy on remote work?"}
        ]

        result = await approach.run(messages)

        assert isinstance(result, dict)
        assert "policy" in result["content"].lower()
        assert len(result["sources"]) > 0

    @pytest.mark.asyncio
    async def test_run_technical_query(self):
        """Test running a technical query"""
        approach = RetrieveThenReadApproach()
        messages = [{"role": "user", "content": "How to implement authentication?"}]

        result = await approach.run(messages)

        assert isinstance(result, dict)
        assert "technical" in result["content"].lower()

    @pytest.mark.asyncio
    async def test_run_with_context_filtering(self):
        """Test running with context filtering"""
        approach = RetrieveThenReadApproach()
        messages = [{"role": "user", "content": "What are the guidelines?"}]
        context = {"overrides": {"selected_category": "policy"}, "auth_claims": None}

        result = await approach.run(messages, context=context)

        assert isinstance(result, dict)
        assert "policy" in result["content"].lower()


class TestChatReadRetrieveReadApproach:
    """Test ChatReadRetrieveRead approach"""

    @pytest.mark.asyncio
    async def test_run_with_conversation_context(self):
        """Test running with conversation context"""
        approach = ChatReadRetrieveReadApproach()
        messages = [
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is a subset of AI..."},
            {"role": "user", "content": "Can you tell me more about neural networks?"},
        ]

        result = await approach.run(messages)

        assert isinstance(result, dict)
        assert "content" in result
        assert "sources" in result
        assert result["context"]["chat_context"]["message_count"] == 3
        assert "neural networks" in result["context"]["query"].lower()

    @pytest.mark.asyncio
    async def test_conversation_summary(self):
        """Test conversation summary processing"""
        approach = ChatReadRetrieveReadApproach()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What is AI?"},
        ]

        chat_context = await approach._process_chat_context(messages, None)

        assert "User: Hello" in chat_context["conversation_summary"]
        assert "Assistant: Hi there!" in chat_context["conversation_summary"]
        assert chat_context["user_intent"] == "What is AI?"
        assert chat_context["message_count"] == 3

    @pytest.mark.asyncio
    async def test_extract_current_query(self):
        """Test extracting current query"""
        approach = ChatReadRetrieveReadApproach()
        messages = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
        ]

        query = await approach._extract_current_query(messages, {})

        assert query == "Second question"

    @pytest.mark.asyncio
    async def test_streaming_run(self):
        """Test streaming execution"""
        approach = ChatReadRetrieveReadApproach()
        messages = [{"role": "user", "content": "What is AI?"}]

        stream_generator = approach._run_streaming(messages, None, None)

        chunks = []
        async for chunk in stream_generator:
            chunks.append(chunk)

        assert len(chunks) > 1
        # Last chunk should be the final response
        final_chunk = chunks[-1]
        assert "content" in final_chunk
        assert "sources" in final_chunk


class TestApproachIntegration:
    """Test integration between approaches and other components"""

    @pytest.mark.asyncio
    async def test_approach_with_empty_messages(self):
        """Test approach with empty messages"""
        approach = get_approach("retrieve_then_read")
        messages = []

        result = await approach.run(messages)

        assert isinstance(result, dict)
        assert "No query found" in result["content"]

    @pytest.mark.asyncio
    async def test_approach_with_non_user_messages(self):
        """Test approach with only non-user messages"""
        approach = get_approach("retrieve_then_read")
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "assistant", "content": "How can I help you?"},
        ]

        result = await approach.run(messages)

        assert isinstance(result, dict)
        assert "No query found" in result["content"]

    def test_approach_string_representation(self):
        """Test string representation of approaches"""
        approach = get_approach("retrieve_then_read")

        str_repr = str(approach)
        assert "RetrieveThenReadApproach" in str_repr
        assert "RetrieveThenRead" in str_repr

        repr_str = repr(approach)
        assert "RetrieveThenReadApproach" in repr_str
