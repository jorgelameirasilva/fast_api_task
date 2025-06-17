"""Tests for chat endpoint"""

import pytest
from fastapi.testclient import TestClient


def test_chat_basic_functionality(client: TestClient, sample_chat_request):
    """Test basic chat functionality"""
    response = client.post("/chat", json=sample_chat_request)

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "message" in data
    assert "role" in data["message"]
    assert "content" in data["message"]
    assert data["message"]["role"] == "assistant"
    assert len(data["message"]["content"]) > 0

    # Check context is present
    if "context" in data["message"]:
        context = data["message"]["context"]
        assert isinstance(context.get("data_points", []), list)
        assert isinstance(context.get("followup_questions", []), list)


def test_chat_with_stream(client: TestClient):
    """Test chat with streaming enabled"""
    request_data = {
        "messages": [{"role": "user", "content": "How do I report an illness?"}],
        "context": {},
        "stream": True,
    }

    response = client.post("/chat", json=request_data)

    # Streaming should return 200 with different content type
    assert response.status_code == 200
    # Note: TestClient doesn't handle streaming well, but we can check status


def test_chat_with_context(client: TestClient):
    """Test chat with additional context"""
    request_data = {
        "messages": [{"role": "user", "content": "What are the safety guidelines?"}],
        "context": {"department": "HR", "policy_version": "2024"},
        "stream": False,
    }

    response = client.post("/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"]["role"] == "assistant"


def test_chat_multiple_messages(client: TestClient):
    """Test chat with conversation history"""
    request_data = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help you?"},
            {"role": "user", "content": "How do I report sick leave?"},
        ],
        "context": {},
        "stream": False,
    }

    response = client.post("/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"]["role"] == "assistant"


def test_chat_empty_messages(client: TestClient):
    """Test chat with empty messages"""
    request_data = {"messages": [], "context": {}, "stream": False}

    response = client.post("/chat", json=request_data)

    # Should handle empty messages gracefully
    assert response.status_code in [200, 400, 422]


def test_chat_invalid_request(client: TestClient):
    """Test chat with invalid request format"""
    # Missing required fields
    response = client.post("/chat", json={})

    assert response.status_code == 422  # Validation error


def test_chat_invalid_message_format(client: TestClient):
    """Test chat with invalid message format"""
    request_data = {
        "messages": [{"role": "invalid_role", "content": "test"}],
        "context": {},
        "stream": False,
    }

    response = client.post("/chat", json=request_data)

    # Should still process but may give different response
    assert response.status_code in [200, 400, 422]
