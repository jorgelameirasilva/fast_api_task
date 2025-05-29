import pytest
from datetime import datetime
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest, ChatMessage, AskRequest, VoteRequest


class TestChatService:
    """Test ChatService functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.chat_service = ChatService()

    @pytest.mark.asyncio
    async def test_process_chat_success(self):
        """Test successful chat processing"""
        messages = [ChatMessage(role="user", content="Hello, how are you?")]
        request = ChatRequest(
            messages=messages, context={"test": True}, session_state="test-session"
        )

        response = await self.chat_service.process_chat(request)

        assert response.message.role == "assistant"
        assert "Hello, how are you?" in response.message.content
        assert response.session_state == "test-session"
        assert response.context == {"test": True}

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
