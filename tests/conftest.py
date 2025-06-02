import pytest
from typing import Generator
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from fastapi.testclient import TestClient
from app.main import app
from app.schemas.chat import ChatMessage, ChatRequest, AskRequest, VoteRequest
from app.services import (
    ChatService,
    AskService,
    VoteService,
    AuthService,
    SessionService,
    ResponseGenerator,
)


@pytest.fixture(scope="function")
def client() -> Generator:
    """
    Create a test client for the FastAPI application.
    """
    with TestClient(app) as client:
        yield client


# Service Fixtures
@pytest.fixture
def chat_service():
    """Create a fresh ChatService instance for testing."""
    return ChatService()


@pytest.fixture
def ask_service():
    """Create a fresh AskService instance for testing."""
    return AskService()


@pytest.fixture
def vote_service():
    """Create a fresh VoteService instance for testing."""
    return VoteService()


@pytest.fixture
def auth_service():
    """Create a fresh AuthService instance for testing."""
    return AuthService()


@pytest.fixture
def session_service():
    """Create a fresh SessionService instance for testing."""
    return SessionService()


@pytest.fixture
def response_generator():
    """Create a fresh ResponseGenerator instance for testing."""
    return ResponseGenerator()


# Mock Fixtures
@pytest.fixture
def mock_approach():
    """Create a mock approach for testing."""
    mock = Mock()
    mock.name = "TestApproach"
    mock.run = AsyncMock(
        return_value={
            "content": "Test response content",
            "sources": [{"title": "Test Source", "url": "/test.pdf"}],
            "context": {"test_key": "test_value"},
        }
    )
    return mock


@pytest.fixture
def mock_session_service():
    """Create a mock SessionService for testing."""
    mock = AsyncMock(spec=SessionService)
    mock.update_session = AsyncMock()
    mock.get_session = AsyncMock(return_value={})
    mock.delete_session = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_response_generator():
    """Create a mock ResponseGenerator for testing."""
    mock = AsyncMock(spec=ResponseGenerator)
    mock.generate_chat_response = AsyncMock(return_value="Mock chat response")
    mock.generate_ask_response = AsyncMock(return_value="Mock ask response")
    mock.get_relevant_sources = AsyncMock(return_value=[])
    return mock


# Data Fixtures
@pytest.fixture
def sample_chat_message():
    """Create a sample ChatMessage for testing."""
    return ChatMessage(
        role="user", content="Hello, how are you?", timestamp=datetime.now()
    )


@pytest.fixture
def sample_chat_request(sample_chat_message):
    """Create a sample ChatRequest for testing."""
    return ChatRequest(
        messages=[sample_chat_message],
        session_state="test-session-123",
        context={"test": "context"},
    )


@pytest.fixture
def sample_ask_request():
    """Create a sample AskRequest for testing."""
    return AskRequest(
        user_query="What is artificial intelligence?",
        chatbot_response="AI is a field of computer science...",
        count=1,
        upvote=True,
    )


@pytest.fixture
def sample_vote_request():
    """Create a sample VoteRequest for testing."""
    return VoteRequest(
        user_query="Test query",
        chatbot_response="Test response",
        upvote=True,
        count=1,
        reason_multiple_choice="helpful",
        additional_comments="Great response!",
    )


@pytest.fixture
def multi_turn_conversation():
    """Create a multi-turn conversation for testing."""
    return [
        ChatMessage(role="user", content="What is AI?"),
        ChatMessage(role="assistant", content="AI is artificial intelligence..."),
        ChatMessage(role="user", content="Can you give examples?"),
        ChatMessage(role="assistant", content="Sure, examples include..."),
        ChatMessage(role="user", content="How does machine learning relate?"),
    ]


# Test Data Collections
@pytest.fixture
def test_queries():
    """Provide various test queries for comprehensive testing."""
    return {
        "simple": "Hello",
        "question": "What is the capital of France?",
        "complex": "Can you explain the relationship between quantum computing and artificial intelligence?",
        "conversational": "Thanks for that explanation, can you tell me more?",
        "empty": "",
        "long": "A" * 1000,
        "special_chars": "What about émojis 🤖 and spëcial cháracters?",
    }


@pytest.fixture
def test_session_ids():
    """Provide various session IDs for testing."""
    return [
        "session-123",
        "user-456-session",
        "temp-session-789",
        "long-session-id-with-many-characters-12345",
        "",
    ]


# Error Scenarios
@pytest.fixture
def failing_approach():
    """Create a mock approach that fails for error testing."""
    mock = Mock()
    mock.name = "FailingApproach"
    mock.run = AsyncMock(side_effect=Exception("Approach execution failed"))
    return mock


@pytest.fixture
def streaming_approach():
    """Create a mock approach that returns streaming results."""
    mock = Mock()
    mock.name = "StreamingApproach"

    async def mock_stream():
        yield {"partial": "content"}
        yield {"content": "Final streaming content", "sources": []}

    mock.run = AsyncMock(return_value=mock_stream())
    return mock
