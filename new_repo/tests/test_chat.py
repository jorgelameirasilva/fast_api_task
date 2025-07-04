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
    mock_session_service.get_session_messages.return_value = []  # No existing messages

    # Mock add_message to return a mock message
    mock_message = Mock()
    mock_message.id = "test-message-123"
    mock_session_service.add_message.return_value = mock_message

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
    # Session ID should be a UUID (we can't predict the exact value)
    assert len(data["session_id"]) > 20  # UUID should be long

    # Verify session service was called
    assert mock_session_service.add_message.call_count == 2  # User + Assistant messages


@pytest.mark.asyncio
@patch("app.services.chat_service.session_service")
async def test_chat_conversation_history_storage(
    mock_session_service, client, sample_chat_request
):
    """Test that conversation history is properly stored in collections"""

    # Mock existing conversation history
    mock_existing_messages = [
        Mock(
            id="msg-1",
            user_id="default_user",
            session_id="existing-session-123",
            message={"role": "user", "content": "Previous question"},
            created_at="2024-01-01T10:00:00Z",
        ),
        Mock(
            id="msg-2",
            user_id="default_user",
            session_id="existing-session-123",
            message={"role": "assistant", "content": "Previous answer"},
            created_at="2024-01-01T10:01:00Z",
        ),
    ]

    mock_session_service.get_session_messages.return_value = mock_existing_messages

    # Mock add_message to return new messages
    mock_new_message = Mock()
    mock_new_message.id = "new-message-123"
    mock_session_service.add_message.return_value = mock_new_message

    # Add session_id to request to test existing conversation
    chat_request_with_session = sample_chat_request.copy()
    chat_request_with_session["session_id"] = "existing-session-123"

    # Make request to chat endpoint
    response = await client.post("/chat", json=chat_request_with_session)

    # Verify successful response
    assert response.status_code == 200

    # Parse response
    response_text = response.text.strip()
    first_line = response_text.split("\n")[0]
    if first_line.startswith("data: "):
        json_str = first_line[6:]
    else:
        json_str = first_line
    data = json.loads(json_str)

    # Verify session_id is preserved
    assert data["session_id"] == "existing-session-123"

    # Verify conversation history was loaded
    mock_session_service.get_session_messages.assert_called_once_with(
        "existing-session-123", "default_user"
    )

    # Verify new messages were added to the collection
    assert mock_session_service.add_message.call_count == 2  # User + Assistant

    # Verify the structure of messages being stored
    add_message_calls = mock_session_service.add_message.call_args_list

    # First call should be the user message
    user_message_call = add_message_calls[0][0][0]  # First argument of first call
    assert user_message_call.user_id == "default_user"
    assert user_message_call.session_id == "existing-session-123"
    assert user_message_call.message["role"] == "user"
    assert (
        user_message_call.message["content"]
        == "What are the company's vacation policies?"
    )

    # Second call should be the assistant message
    assistant_message_call = add_message_calls[1][0][0]  # First argument of second call
    assert assistant_message_call.user_id == "default_user"
    assert assistant_message_call.session_id == "existing-session-123"
    assert assistant_message_call.message["role"] == "assistant"
    assert isinstance(assistant_message_call.message["content"], str)
    assert len(assistant_message_call.message["content"]) > 0


@pytest.mark.asyncio
@patch("app.services.chat_service.session_service")
async def test_new_conversation_creates_session_history(
    mock_session_service, client, sample_chat_request
):
    """Test that new conversations create proper session history from scratch"""

    # Mock no existing messages (new conversation)
    mock_session_service.get_session_messages.return_value = []

    # Mock add_message returns
    mock_message = Mock()
    mock_message.id = "new-msg-123"
    mock_session_service.add_message.return_value = mock_message

    # Make request without session_id (new conversation)
    response = await client.post("/chat", json=sample_chat_request)

    # Verify successful response
    assert response.status_code == 200

    # Parse response to get generated session_id
    response_text = response.text.strip()
    first_line = response_text.split("\n")[0]
    if first_line.startswith("data: "):
        json_str = first_line[6:]
    else:
        json_str = first_line
    data = json.loads(json_str)

    generated_session_id = data["session_id"]
    assert len(generated_session_id) > 20  # Should be a UUID

    # Verify no attempt to load existing history (new session)
    # get_session_messages should not be called for new sessions
    mock_session_service.get_session_messages.assert_not_called()

    # Verify messages were stored in the new session
    assert mock_session_service.add_message.call_count == 2

    # Verify both messages use the same generated session_id
    add_message_calls = mock_session_service.add_message.call_args_list

    user_message = add_message_calls[0][0][0]
    assistant_message = add_message_calls[1][0][0]

    assert user_message.session_id == generated_session_id
    assert assistant_message.session_id == generated_session_id
    assert user_message.user_id == "default_user"
    assert assistant_message.user_id == "default_user"

    # Verify message content structure
    assert user_message.message["role"] == "user"
    assert assistant_message.message["role"] == "assistant"
