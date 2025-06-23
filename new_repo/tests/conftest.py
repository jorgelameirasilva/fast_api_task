"""Test configuration and fixtures"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.core.config import settings


@pytest.fixture(scope="session")
def test_app():
    """Create test FastAPI app"""
    import os

    # Override settings for testing
    settings.use_mock_clients = True
    settings.debug = True
    # Disable authentication for testing using environment variable
    os.environ["REQUIRE_AUTHENTICATION"] = "0"

    return app


@pytest.fixture(scope="session")
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


@pytest_asyncio.fixture
async def async_client(test_app):
    """Create async test client"""
    async with AsyncClient(app=test_app, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing with new ChatRequest format"""
    return {
        "messages": [{"role": "user", "content": "How do I report an illness?"}],
        "context": {},
        "stream": False,
        "session_state": None,  # New session
    }


@pytest.fixture
def sample_vote_request():
    """Sample vote request for testing"""
    return {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 1,
        "downvote": 0,
        "count": 1,
    }
