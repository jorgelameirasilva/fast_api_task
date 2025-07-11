"""Test configuration and fixtures"""

import os
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient

# Set environment variables BEFORE importing app
os.environ["REQUIRE_AUTHENTICATION"] = "0"
os.environ["USE_MOCK_CLIENTS"] = "true"
# Set SECURE_GPT variables to prevent None model issues
os.environ["SECURE_GPT_DEPLOYMENT_ID"] = "gpt-4"
os.environ["SECURE_GPT_EMB_DEPLOYMENT_ID"] = "text-embedding-ada-002"
os.environ["SECURE_GPT_CLIENT_ID"] = "test-client-id"
os.environ["SECURE_GPT_CLIENT_SECRET"] = "test-client-secret"
os.environ["SECURE_GPT_API_VERSION"] = "2024-02-01"
os.environ["APIM_KEY"] = "test-apim-key"
os.environ["APIM_ONELOGIN_URL"] = "https://test-onelogin.com"
os.environ["APIM_BASE_URL"] = "https://test-apim.azure-api.net"
# Set MongoDB URL to prevent connection issues
os.environ["MONGODB_URL"] = "mongodb://localhost:27017/test_db"

from app.main import app


@pytest.fixture(autouse=True)
def mock_model_validation():
    """Mock model validation to prevent model name errors"""
    with patch("app.core.modelhelper.get_oai_chatmodel_tiktoken", return_value="gpt-4"):
        yield


@pytest.fixture(autouse=True)
def mock_openai_client():
    """Mock OpenAI client to return a simple response"""
    mock_client = AsyncMock()

    # Mock chat completion response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        "This is a test response about vacation policies. You get 15 days of PTO annually."
    )
    mock_response.choices[0].message.role = "assistant"

    mock_client.chat.completions.create.return_value = mock_response

    with patch(
        "app.utils.mock_clients.get_mock_openai_client", return_value=mock_client
    ):
        yield mock_client


@pytest.fixture(autouse=True)
def mock_search_client():
    """Mock search client to return simple search results"""
    mock_client = AsyncMock()

    # Mock search results
    mock_results = [
        {
            "content": "Vacation policy: Employees get 15 days of PTO annually.",
            "sourcepage": "hr-policy.pdf",
        }
    ]

    mock_client.search.return_value = mock_results

    with patch(
        "app.utils.mock_clients.get_mock_search_client", return_value=mock_client
    ):
        yield mock_client


@pytest_asyncio.fixture
async def client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing"""
    return {
        "messages": [
            {"role": "user", "content": "What are the company's vacation policies?"}
        ],
        "stream": False,
        "context": {},
    }


@pytest.fixture
def sample_vote_request():
    """Sample vote request for testing"""
    return {
        "user_query": "What are the company's vacation policies?",
        "chatbot_response": "Employees get 15 days of PTO annually according to company policy.",
        "upvote": 1,
        "downvote": 0,
        "count": 1,
        "reason_multiple_choice": None,
        "additional_comments": None,
    }


@pytest.fixture
def sample_downvote_request():
    """Sample downvote request for testing"""
    return {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 1,
        "count": 1,
        "reason_multiple_choice": "Other",
        "additional_comments": "More comments",
    }


@pytest.fixture
def sample_empty_vote_request():
    """Sample empty vote request for testing"""
    return {
        "user_query": {},
        "chatbot_response": {},
        "upvote": 0,
        "downvote": 0,
        "count": 1,
    }


@pytest.fixture
def invalid_vote_inputs():
    """Various invalid vote inputs for testing"""
    return [
        # Invalid upvote/downvote combinations
        {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 1,
            "downvote": 1,  # Both set to 1
            "count": 1,
        },
        # Invalid count values
        {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 1,
            "downvote": 0,
            "count": 2,  # Invalid count
        },
        # Invalid upvote value
        {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": "input",  # Invalid type
            "downvote": 0,
            "count": 1,
        },
        # Neither upvote nor downvote set
        {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 0,  # Both are 0
            "count": 1,
        },
    ]


@pytest.fixture
def more_vote_inputs():
    """Additional vote test cases"""
    return [
        # Valid upvote case
        {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 1,
            "downvote": 0,
            "count": 1,
            "data": "01/01/01",
            "time": "00:00:00",
            "email_address": "example.email@email.com",
        },
        # Valid downvote removal case
        {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": -1,  # Removal
            "reason_multiple_choice": "input",
        },
    ]


@pytest.fixture
def sample_feedback_request():
    """Sample feedback request for testing"""
    return {
        "feedback": "Great application!",
        "comment": "The chatbot is very helpful and provides accurate responses.",
        "name": "Test User",
    }
