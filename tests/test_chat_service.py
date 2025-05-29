import pytest
from datetime import datetime
from app.services.chat_service import ChatService
from app.schemas.chat import (
    ChatRequest,
    ChatMessage,
    ChatResponse,
    AskRequest,
    VoteRequest,
)


class TestChatService:
    """Test ChatService functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.chat_service = ChatService()

    @pytest.mark.asyncio
    async def test_process_chat_success(self):
        """Test successful chat processing"""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello, how are you?")]
        )

        response = await self.chat_service.process_chat(request)

        assert isinstance(response, ChatResponse)
        assert response.message.role == "assistant"
        assert len(response.message.content) > 0
        assert "approach_used" in response.context

    @pytest.mark.asyncio
    async def test_process_chat_with_specific_approach(self):
        """Test chat processing with specific approach"""
        request = ChatRequest(
            messages=[
                ChatMessage(role="user", content="What is AI?"),
                ChatMessage(role="assistant", content="AI is artificial intelligence."),
                ChatMessage(role="user", content="Tell me more"),
            ]
        )

        response = await self.chat_service.process_chat(
            request, approach_name="chat_read_retrieve_read"
        )

        assert response.context["approach_used"] == "ChatReadRetrieveRead"
        assert "chat_processed_at" in response.context

    @pytest.mark.asyncio
    async def test_process_chat_with_streaming(self):
        """Test chat processing with streaming"""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Explain quantum computing")]
        )

        response = await self.chat_service.process_chat(request, stream=True)

        assert response.context["streaming"] is True

    @pytest.mark.asyncio
    async def test_process_chat_session_management(self):
        """Test chat processing with session state"""
        session_id = "test-session-123"
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            session_state=session_id,
        )

        response = await self.chat_service.process_chat(request)

        assert response.session_state == session_id
        assert response.context["session_updated"] is True
        # Check that session was stored
        assert session_id in self.chat_service.session_storage
        assert "approach_used" in self.chat_service.session_storage[session_id]

    @pytest.mark.asyncio
    async def test_process_chat_multi_turn_conversation(self):
        """Test chat processing with multi-turn conversation"""
        request = ChatRequest(
            messages=[
                ChatMessage(role="user", content="What is machine learning?"),
                ChatMessage(role="assistant", content="ML is a subset of AI..."),
                ChatMessage(role="user", content="Can you give examples?"),
                ChatMessage(role="assistant", content="Sure, examples include..."),
                ChatMessage(role="user", content="How does deep learning relate?"),
            ]
        )

        response = await self.chat_service.process_chat(request)

        # Multi-turn conversation should likely use ChatReadRetrieveRead
        assert response.context["approach_used"] in [
            "ChatReadRetrieveRead",
            "RetrieveThenRead",
        ]
        assert "sources_count" in response.context

    @pytest.mark.asyncio
    async def test_process_chat_approach_selection(self):
        """Test automatic approach selection for chat"""
        # Simple query
        simple_request = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")]
        )

        simple_response = await self.chat_service.process_chat(simple_request)
        assert "approach_used" in simple_response.context

        # Complex conversational query
        complex_request = ChatRequest(
            messages=[
                ChatMessage(role="user", content="What is AI?"),
                ChatMessage(role="assistant", content="AI is..."),
                ChatMessage(role="user", content="Can you elaborate on that?"),
            ]
        )

        complex_response = await self.chat_service.process_chat(complex_request)
        # Should likely use ChatReadRetrieveRead for contextual query
        assert complex_response.context["approach_used"] in [
            "ChatReadRetrieveRead",
            "RetrieveThenRead",
        ]

    @pytest.mark.asyncio
    async def test_process_chat_with_context(self):
        """Test chat processing with request context"""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="What is our policy?")],
            context={"category": "policy", "department": "HR"},
        )

        response = await self.chat_service.process_chat(request)

        # Original context should be preserved and enhanced
        assert "category" in response.context
        assert "department" in response.context
        assert "approach_used" in response.context

    @pytest.mark.asyncio
    async def test_process_chat_error_handling(self):
        """Test chat error handling and fallback"""
        # Test with invalid approach name - should still work with fallback
        request = ChatRequest(messages=[ChatMessage(role="user", content="Hello")])

        response = await self.chat_service.process_chat(
            request, approach_name="nonexistent_approach"
        )

        # Should fallback gracefully
        assert isinstance(response, ChatResponse)
        assert "approach_used" in response.context

    @pytest.mark.asyncio
    async def test_process_chat_no_user_message(self):
        """Test chat processing with no user messages"""
        messages = [ChatMessage(role="system", content="You are a helpful assistant")]
        request = ChatRequest(messages=messages)

        with pytest.raises(ValueError, match="No user message found"):
            await self.chat_service.process_chat(request)

    @pytest.mark.asyncio
    async def test_process_chat_multiple_messages(self):
        """Test chat processing with multiple messages"""
        messages = [
            ChatMessage(role="system", content="You are a helpful assistant"),
            ChatMessage(role="user", content="What is AI?"),
            ChatMessage(role="assistant", content="AI is artificial intelligence"),
            ChatMessage(role="user", content="Tell me more"),
        ]
        request = ChatRequest(messages=messages)

        response = await self.chat_service.process_chat(request)

        assert response.message.role == "assistant"
        assert "Tell me more" in response.message.content

    @pytest.mark.asyncio
    async def test_process_chat_session_storage(self):
        """Test chat processing updates session storage"""
        messages = [ChatMessage(role="user", content="Hello")]
        request = ChatRequest(messages=messages, session_state="test-session-123")

        await self.chat_service.process_chat(request)

        assert "test-session-123" in self.chat_service.session_storage
        session_data = self.chat_service.session_storage["test-session-123"]
        assert "last_interaction" in session_data
        assert session_data["message_count"] == 2  # 1 user + 1 assistant

    @pytest.mark.asyncio
    async def test_process_ask_success(self):
        """Test successful ask processing"""
        request = AskRequest(user_query="What is the capital of France?", count=1)

        response = await self.chat_service.process_ask(request)

        assert response.user_query == "What is the capital of France?"
        assert "What is the capital of France?" in response.chatbot_response
        assert response.count == 1
        assert len(response.sources) == 2  # Mock sources
        assert "query_processed_at" in response.context

    @pytest.mark.asyncio
    async def test_process_ask_with_optional_fields(self):
        """Test ask processing with optional fields"""
        request = AskRequest(
            user_query="Tell me about AI",
            user_query_vector=[0.1, 0.2, 0.3],
            chatbot_response="Previous response",
            count=5,
            upvote=True,
        )

        response = await self.chat_service.process_ask(request)

        assert response.user_query == "Tell me about AI"
        assert response.count == 5
        assert len(response.sources) > 0

    @pytest.mark.asyncio
    async def test_process_vote_success(self):
        """Test successful vote processing"""
        request = VoteRequest(
            user_query="What is AI?",
            chatbot_response="AI is artificial intelligence",
            count=1,
            upvote=True,
        )

        response = await self.chat_service.process_vote(request)

        assert response.status == "success"
        assert response.upvote is True
        assert response.count == 1
        assert len(self.chat_service.vote_storage) == 1

    @pytest.mark.asyncio
    async def test_process_vote_downvote(self):
        """Test vote processing with downvote"""
        request = VoteRequest(
            user_query="What is AI?",
            chatbot_response="AI is artificial intelligence",
            count=2,
            upvote=False,
        )

        response = await self.chat_service.process_vote(request)

        assert response.status == "success"
        assert response.upvote is False
        assert response.count == 2

    @pytest.mark.asyncio
    async def test_process_vote_with_additional_fields(self):
        """Test vote processing with all additional fields"""
        request = VoteRequest(
            user_query="How do I report an illness?",
            chatbot_response="To report an illness, follow these steps:",
            count=1,
            upvote=True,
            downvote=False,
            reason_multiple_choice="Helpful",
            additional_comments="Very clear instructions",
            date="01/01/01",
            time="00:00:00",
            email_address="example.email@axax1.com",
        )

        response = await self.chat_service.process_vote(request)

        assert response.status == "success"
        assert response.upvote is True
        assert response.count == 1

        # Check that all fields were stored
        stored_vote = self.chat_service.vote_storage[0]
        assert stored_vote["reason_multiple_choice"] == "Helpful"
        assert stored_vote["additional_comments"] == "Very clear instructions"
        assert stored_vote["date"] == "01/01/01"
        assert stored_vote["time"] == "00:00:00"
        assert stored_vote["email_address"] == "example.email@axax1.com"

    @pytest.mark.asyncio
    async def test_process_vote_conflicting_votes(self):
        """Test vote processing with conflicting upvote/downvote"""
        request = VoteRequest(
            user_query="What is AI?",
            chatbot_response="AI is artificial intelligence",
            count=1,
            upvote=True,
            downvote=True,  # This should cause a conflict
        )

        with pytest.raises(ValueError, match="Vote cannot be both upvote and downvote"):
            await self.chat_service.process_vote(request)

    @pytest.mark.asyncio
    async def test_process_vote_downvote_priority(self):
        """Test that downvote field takes priority when both are provided but not conflicting"""
        request = VoteRequest(
            user_query="What is AI?",
            chatbot_response="AI is artificial intelligence",
            count=1,
            upvote=True,
            downvote=False,  # downvote=False should override upvote=True
        )

        response = await self.chat_service.process_vote(request)

        assert response.status == "success"
        assert response.upvote is True  # Should still be upvote since downvote=False
        assert response.count == 1

    @pytest.mark.asyncio
    async def test_process_vote_explicit_downvote(self):
        """Test explicit downvote with downvote field"""
        request = VoteRequest(
            user_query="What is AI?",
            chatbot_response="AI is artificial intelligence",
            count=1,
            upvote=False,
            downvote=True,
        )

        response = await self.chat_service.process_vote(request)

        assert response.status == "success"
        assert response.upvote is False
        assert response.count == 1

    @pytest.mark.asyncio
    async def test_vote_storage_accumulation(self):
        """Test that votes are stored and accumulated"""
        # First vote
        request1 = VoteRequest(
            user_query="Query 1", chatbot_response="Response 1", count=1, upvote=True
        )
        await self.chat_service.process_vote(request1)

        # Second vote
        request2 = VoteRequest(
            user_query="Query 2", chatbot_response="Response 2", count=2, upvote=False
        )
        await self.chat_service.process_vote(request2)

        assert len(self.chat_service.vote_storage) == 2
        assert self.chat_service.vote_storage[0]["upvote"] is True
        assert self.chat_service.vote_storage[1]["upvote"] is False

    @pytest.mark.asyncio
    async def test_get_auth_setup(self):
        """Test auth setup retrieval"""
        response = await self.chat_service.get_auth_setup()

        assert hasattr(response, "auth_enabled")
        assert hasattr(response, "auth_type")
        assert isinstance(response.auth_enabled, bool)

    @pytest.mark.asyncio
    async def test_generate_chat_response(self):
        """Test private method for generating chat responses"""
        response = await self.chat_service._generate_chat_response(
            "Hello", {"test": True}
        )

        assert isinstance(response, str)
        assert "Hello" in response

    @pytest.mark.asyncio
    async def test_generate_ask_response(self):
        """Test private method for generating ask responses"""
        response = await self.chat_service._generate_ask_response("What is AI?")

        assert isinstance(response, str)
        assert "What is AI?" in response

    @pytest.mark.asyncio
    async def test_get_relevant_sources(self):
        """Test private method for getting relevant sources"""
        sources = await self.chat_service._get_relevant_sources("AI query")

        assert isinstance(sources, list)
        assert len(sources) == 2  # Mock implementation returns 2 sources
        for source in sources:
            assert "title" in source
            assert "url" in source
            assert "relevance_score" in source
            assert "excerpt" in source
