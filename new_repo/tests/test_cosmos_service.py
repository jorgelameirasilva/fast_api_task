"""One simple test for the cosmos service using real MongoDB"""

import pytest
from datetime import datetime

from app.services.cosmos_service import CosmosService
from app.models.chat import ChatMessage


@pytest.mark.asyncio
async def test_cosmos_service_basic_functionality():
    """Test basic cosmos service functionality with real MongoDB"""

    # Create service
    service = CosmosService(
        connection_string="mongodb://localhost:27017/",
        database_name="test_simple",
        collection_name="test_sessions",
    )

    try:
        # 1. Create a session
        session = await service.create_session(
            user_id="test_user", title="Test Session"
        )
        assert session.user_id == "test_user"
        assert session.title == "Test Session"

        # 2. Add a message
        message = ChatMessage(
            role="user", content="Hello world!", timestamp=datetime.utcnow()
        )
        updated_session = await service.add_message(session.id, "test_user", message)
        assert len(updated_session.messages) == 1
        assert updated_session.messages[0].content == "Hello world!"

        # 3. Get the session back
        retrieved_session = await service.get_session(session.id, "test_user")
        assert retrieved_session.id == session.id
        assert len(retrieved_session.messages) == 1

        # 4. List sessions
        sessions = await service.list_sessions("test_user")
        assert len(sessions) == 1
        assert sessions[0].title == "Test Session"

        # 5. Delete session
        success = await service.delete_session(session.id, "test_user")
        assert success is True

        print("✅ All basic functionality works!")

    finally:
        # Clean up
        try:
            service.collection.drop()
        except:
            pass
        await service.close()
