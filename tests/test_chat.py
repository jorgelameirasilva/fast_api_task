"""
Simple test for chat endpoint with session management
"""

import json
import pytest
from unittest.mock import Mock, patch


@pytest.mark.asyncio
@patch("app.services.chat_service.session_service")
async def test_chat_endpoint_with_session(
    mock_session_service, client, sample_chat_request
):
    """Test chat endpoint with session management - mock database"""

    # Mock session service responses
    mock_session = Mock()
    mock_session.id = "test-session-123"
    mock_session.messages = []
    mock_session_service.get_session.return_value = None  # No existing session
    mock_session_service.create_session.return_value = mock_session
    mock_session_service.add_message_to_session.return_value = mock_session

    # Make request to chat endpoint
    response = await client.post("/chat", json=sample_chat_request)

    # Verify we get a successful response
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/json-lines"

    # Parse the NDJSON response
    response_text = response.text.strip()
    lines = response_text.split("\n")
    first_line = lines[0] if lines else ""

    # Remove "data: " prefix if present
    if first_line.startswith("data: "):
        json_str = first_line[6:]
    else:
        json_str = first_line

    # Parse JSON response
    data = json.loads(json_str)

    # Verify response structure
    assert "message" in data
    assert "role" in data["message"]
    assert "content" in data["message"]
    assert data["message"]["role"] == "assistant"
    assert isinstance(data["message"]["content"], str)
    assert len(data["message"]["content"]) > 0

    # Verify session integration
    assert "session_id" in data
    assert data["session_id"] == "test-session-123"

    # Verify session service was called
    mock_session_service.create_session.assert_called_once()
    assert (
        mock_session_service.add_message_to_session.call_count == 2
    )  # User + Assistant messages
