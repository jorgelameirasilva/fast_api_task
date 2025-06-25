"""Test configuration and fixtures"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

# Set environment variables BEFORE importing app
os.environ["REQUIRE_AUTHENTICATION"] = "0"
os.environ["USE_MOCK_CLIENTS"] = "true"
# Set SECURE_GPT variables to prevent None model issues
os.environ["SECURE_GPT_DEPLOYMENT_ID"] = "gpt-4o-test"
os.environ["SECURE_GPT_EMB_DEPLOYMENT_ID"] = "text-embedding-ada-002-test"
os.environ["SECURE_GPT_CLIENT_ID"] = "test-client-id"
os.environ["SECURE_GPT_CLIENT_SECRET"] = "test-client-secret"
os.environ["SECURE_GPT_API_VERSION"] = "2024-02-01"
os.environ["APIM_KEY"] = "test-apim-key"
os.environ["APIM_ONELOGIN_URL"] = "https://test-onelogin.com"
os.environ["APIM_BASE_URL"] = "https://test-apim.azure-api.net"

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


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


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
