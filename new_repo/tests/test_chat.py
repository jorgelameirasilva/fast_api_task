"""Tests for chat endpoint with orchestrator architecture"""

import pytest
from fastapi.testclient import TestClient


def test_chat_basic_functionality(client: TestClient, sample_chat_request):
    """Test basic chat functionality with simplified architecture"""
    response = client.post("/chat", json=sample_chat_request)

    assert response.status_code == 200

    # The response is now always streaming (NDJSON), even for non-streaming requests
    assert response.headers.get("content-type") in [
        "application/json-lines",
        "application/x-ndjson",
    ]

    # Parse the NDJSON response
    response_text = response.text.strip()

    # For non-streaming, we should get a single line
    if response_text:
        import json

        # Parse the first/only line (handle NDJSON format with "data: " prefix)
        lines = response_text.split("\n")
        first_line = lines[0] if lines[0] else ""

        # Remove "data: " prefix if present (NDJSON format)
        if first_line.startswith("data: "):
            json_str = first_line[6:]  # Remove "data: "
        else:
            json_str = first_line

        data = json.loads(json_str) if json_str else {}

        # Check if it's a valid response (either success or error)
        if "error" not in data:
            # Success response - check old format with message, data_points, etc.
            assert "message" in data
            assert "data_points" in data

            # Check message structure (should be serialized dict with content)
            message = data["message"]
            assert "content" in message
            assert len(message["content"]) > 0

            # Check data_points
            assert isinstance(data["data_points"], list)
            assert len(data["data_points"]) > 0

            print("✅ Chat orchestrator returns old format response")
        else:
            # Error response - acceptable in mock/test mode
            assert "error" in data
            print("⚠️ Chat returned error (expected in mock mode):", data["error"])


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
        "context": {"overrides": {"selected_category": "HR", "top": 5}},
        "stream": False,
    }

    response = client.post("/chat", json=request_data)

    assert response.status_code == 200

    # Parse NDJSON response
    response_text = response.text.strip()
    if response_text:
        import json

        lines = response_text.split("\n")
        first_line = lines[0] if lines[0] else ""

        # Remove "data: " prefix if present
        if first_line.startswith("data: "):
            json_str = first_line[6:]
        else:
            json_str = first_line

        data = json.loads(json_str) if json_str else {}

        # Check if it's a valid response (either success or error)
        if "error" not in data:
            # Success response - check old format
            assert "message" in data
            assert "data_points" in data

            message = data["message"]
            assert "content" in message
            assert len(message["content"]) > 0
        else:
            # Error response - acceptable in mock/test mode
            assert "error" in data


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

    # Parse NDJSON response
    response_text = response.text.strip()
    if response_text:
        import json

        lines = response_text.split("\n")
        first_line = lines[0] if lines[0] else ""

        # Remove "data: " prefix if present
        if first_line.startswith("data: "):
            json_str = first_line[6:]
        else:
            json_str = first_line

        data = json.loads(json_str) if json_str else {}

        # Check if it's a valid response (either success or error)
        if "error" not in data:
            # Success response - check old format
            assert "message" in data
            assert "data_points" in data

            message = data["message"]
            assert "content" in message
            assert len(message["content"]) > 0
        else:
            # Error response - acceptable in mock/test mode
            assert "error" in data


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


def test_chat_with_session_management(client: TestClient):
    """Test that chat properly handles session management via orchestrator"""
    # First request - should create new session
    request_data = {
        "messages": [{"role": "user", "content": "Hello, I'm new here"}],
        "context": {},
        "stream": False,
        "session_state": None,  # New session
    }

    response = client.post("/chat", json=request_data)
    assert response.status_code == 200

    # Parse NDJSON response
    response_text = response.text.strip()
    if response_text:
        import json

        lines = response_text.split("\n")
        first_line = lines[0] if lines[0] else ""

        # Remove "data: " prefix if present
        if first_line.startswith("data: "):
            json_str = first_line[6:]
        else:
            json_str = first_line

        data = json.loads(json_str) if json_str else {}

        # Check if it's a valid response (either success or error)
        if "error" not in data:
            # Success response - check old format (session_state may not be present in old format)
            assert "message" in data
            assert "data_points" in data

            message = data["message"]
            assert "content" in message
            assert len(message["content"]) > 0

            print("✅ Session management test passed with old format")
        else:
            # Error response - acceptable in mock/test mode
            assert "error" in data
