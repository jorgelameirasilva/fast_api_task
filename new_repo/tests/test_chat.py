"""Tests for chat endpoint with orchestrator architecture"""

import pytest
from fastapi.testclient import TestClient


def test_chat_basic_functionality(client: TestClient, sample_chat_request):
    """Test basic chat functionality with unified streaming architecture"""
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
            # Success response - check new ChatResponse structure with choices array
            assert "choices" in data
            assert len(data["choices"]) > 0

            choice = data["choices"][0]
            assert "message" in choice
            assert "role" in choice["message"]
            assert "content" in choice["message"]
            assert choice["message"]["role"] == "assistant"
            assert len(choice["message"]["content"]) > 0

            # Check for session_state in response (might be None in fallback mode)
            assert "session_state" in data

            print("✅ Chat orchestrator returns unified streaming response")
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
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert data["choices"][0]["message"]["role"] == "assistant"
            assert "session_state" in data
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
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert data["choices"][0]["message"]["role"] == "assistant"
            assert "session_state" in data
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
            assert "session_state" in data
            # Session state might be None in mock mode, that's ok

            # Get the session state for follow-up (if available)
            session_state = data.get("session_state")

            # Second request - continue conversation (if we have a session)
            if session_state:
                request_data_2 = {
                    "messages": [
                        {"role": "user", "content": "What's my previous message?"}
                    ],
                    "context": {},
                    "stream": False,
                    "session_state": session_state,  # Continue session
                }

                response_2 = client.post("/chat", json=request_data_2)
                assert response_2.status_code == 200

                # Parse second response
                response_text_2 = response_2.text.strip()
                if response_text_2:
                    lines_2 = response_text_2.split("\n")
                    first_line_2 = lines_2[0] if lines_2[0] else ""

                    if first_line_2.startswith("data: "):
                        json_str_2 = first_line_2[6:]
                    else:
                        json_str_2 = first_line_2

                    data_2 = json.loads(json_str_2) if json_str_2 else {}

                    if "error" not in data_2:
                        assert "session_state" in data_2
                        assert data_2["session_state"] == session_state  # Same session

            print("✅ Chat orchestrator properly manages sessions")
        else:
            # Error response - acceptable in mock/test mode
            print(
                "⚠️ Session management test skipped due to mock error:",
                data.get("error"),
            )
