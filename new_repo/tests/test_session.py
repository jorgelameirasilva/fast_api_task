"""
Tests for session management functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.services.session_service import SessionService
from app.schemas.session import SessionMessageCreate, SessionMessage


@pytest.mark.asyncio
async def test_basic_message_operations():
    """Test basic message add and retrieve operations"""

    # Mock collection
    mock_collection = MagicMock()

    with patch(
        "app.services.session_service.get_sessions_collection",
        return_value=mock_collection,
    ):
        service = SessionService()

        # Test adding a message
        mock_collection.insert_one.return_value = None

        message_create = SessionMessageCreate(
            user_id="test_user",
            session_id="session-123",
            message={"role": "user", "content": "Hello"},
        )

        message = service.add_message(message_create)

        # Verify message was created correctly
        assert message.user_id == "test_user"
        assert message.session_id == "session-123"
        assert message.message["role"] == "user"
        assert message.message["content"] == "Hello"
        assert isinstance(message.id, str)

        # Verify database insert was called
        mock_collection.insert_one.assert_called_once()

        # Test getting messages
        mock_messages_data = [
            {
                "_id": "message-1",
                "user_id": "test_user",
                "session_id": "session-123",
                "message": {"role": "user", "content": "Hello"},
                "created_at": datetime.utcnow(),
            }
        ]

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_messages_data
        mock_collection.find.return_value = mock_cursor

        messages = service.get_session_messages("session-123", "test_user")

        # Verify messages were retrieved
        assert len(messages) == 1
        assert messages[0].message["content"] == "Hello"

        # Verify database query was called
        mock_collection.find.assert_called_once_with(
            {"session_id": "session-123", "user_id": "test_user"}
        )


@pytest.mark.asyncio
async def test_service_collection_initialization():
    """Test that the service properly initializes with the collection"""

    mock_collection = MagicMock()

    with patch(
        "app.services.session_service.get_sessions_collection",
        return_value=mock_collection,
    ) as mock_get_collection:
        service = SessionService()

        # Verify the collection getter was called
        mock_get_collection.assert_called_once()

        # Verify the service has the collection
        assert service.collection == mock_collection
