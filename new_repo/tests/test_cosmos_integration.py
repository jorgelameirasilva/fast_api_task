"""Integration tests for cosmos service with real MongoDB"""

import pytest
import asyncio
from datetime import datetime, timedelta

from app.services.cosmos_service import CosmosService
from app.models.session import ChatSession, SessionSummary, SessionSearchRequest
from app.models.chat import ChatMessage


@pytest.fixture(scope="module")
def integration_service():
    """Create cosmos service with real MongoDB connection"""
    service = CosmosService(
        connection_string="mongodb://localhost:27017/",
        database_name="test_integration",
        collection_name="sessions",
    )
    yield service

    # Cleanup: Drop test collection after tests
    try:
        service.collection.drop()
    except:
        pass

    # Close connection
    asyncio.run(service.close())


@pytest.fixture
def sample_message():
    """Sample chat message for testing"""
    return ChatMessage(
        role="user",
        content="Hello, this is a test message for integration testing!",
        timestamp=datetime.utcnow(),
    )


class TestCosmosIntegration:
    """Integration tests with real MongoDB"""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, integration_service, sample_message):
        """Test complete session lifecycle with real database"""
        # Create session
        session = await integration_service.create_session(
            user_id="integration-user-1",
            title="Integration Test Session",
            context={"test_type": "integration"},
        )

        assert session.user_id == "integration-user-1"
        assert session.title == "Integration Test Session"
        assert session.context["test_type"] == "integration"
        assert session.is_active is True

        # Add message to session
        updated_session = await integration_service.add_message(
            session.id,
            session.user_id,
            sample_message,
            {"message_context": "integration_test"},
        )

        assert updated_session is not None
        assert len(updated_session.messages) == 1
        assert updated_session.messages[0].content == sample_message.content
        assert updated_session.context["message_context"] == "integration_test"

        # Retrieve session
        retrieved_session = await integration_service.get_session(
            session.id, session.user_id
        )

        assert retrieved_session is not None
        assert retrieved_session.id == session.id
        assert len(retrieved_session.messages) == 1

        # List user sessions
        user_sessions = await integration_service.list_sessions("integration-user-1")

        assert len(user_sessions) >= 1
        session_ids = [s.id for s in user_sessions]
        assert session.id in session_ids

        # Soft delete session
        deleted = await integration_service.delete_session(session.id, session.user_id)

        assert deleted is True

        # Verify session is marked inactive
        deleted_session = await integration_service.get_session(
            session.id, session.user_id
        )
        assert deleted_session.is_active is False

    @pytest.mark.asyncio
    async def test_message_trimming_with_database(self, integration_service):
        """Test message trimming with real database operations"""
        # Create session with small message limit
        session = await integration_service.create_session(
            user_id="integration-user-2", title="Message Trimming Test", max_messages=3
        )

        # Add system message
        system_msg = ChatMessage(
            role="system",
            content="System message for testing",
            timestamp=datetime.utcnow(),
        )
        await integration_service.add_message(session.id, session.user_id, system_msg)

        # Add multiple user messages
        for i in range(5):
            user_msg = ChatMessage(
                role="user", content=f"User message {i}", timestamp=datetime.utcnow()
            )
            await integration_service.add_message(session.id, session.user_id, user_msg)

        # Retrieve session and verify trimming
        final_session = await integration_service.get_session(
            session.id, session.user_id
        )

        assert len(final_session.messages) == 3
        assert final_session.messages[0].role == "system"
        assert final_session.messages[1].content == "User message 3"
        assert final_session.messages[2].content == "User message 4"

        # Cleanup
        await integration_service.delete_session(session.id, session.user_id)

    @pytest.mark.asyncio
    async def test_session_search_with_database(self, integration_service):
        """Test session search functionality with real database"""
        # Create multiple sessions
        session1 = await integration_service.create_session(
            "integration-user-3", "Python Tutorial"
        )

        session2 = await integration_service.create_session(
            "integration-user-3", "JavaScript Guide"
        )

        session3 = await integration_service.create_session(
            "integration-user-4", "Different User Session"
        )

        # Add messages to make search more interesting
        python_msg = ChatMessage(
            role="user",
            content="Tell me about Python programming",
            timestamp=datetime.utcnow(),
        )
        await integration_service.add_message(
            session1.id, "integration-user-3", python_msg
        )

        # Search for user-3 sessions
        search_request = SessionSearchRequest(
            user_id="integration-user-3", limit=10, offset=0
        )

        results = await integration_service.search_sessions(search_request)

        assert len(results) == 2
        user_ids = [r.user_id for r in results]
        assert all(uid == "integration-user-3" for uid in user_ids)

        # Search for Python-related sessions
        search_request.query = "Python"
        python_results = await integration_service.search_sessions(search_request)

        assert len(python_results) == 1
        assert "Python" in python_results[0].title

        # Cleanup
        for session in [session1, session2, session3]:
            await integration_service.delete_session(session.id, session.user_id)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, integration_service):
        """Test concurrent database operations"""
        # Create multiple sessions concurrently
        tasks = []
        for i in range(5):
            task = integration_service.create_session(
                user_id=f"concurrent-user-{i}", title=f"Concurrent Session {i}"
            )
            tasks.append(task)

        # Execute all tasks concurrently
        sessions = await asyncio.gather(*tasks)

        # Verify all sessions were created
        assert len(sessions) == 5
        assert all(s.is_active for s in sessions)

        # Cleanup
        cleanup_tasks = []
        for session in sessions:
            task = integration_service.delete_session(session.id, session.user_id)
            cleanup_tasks.append(task)

        await asyncio.gather(*cleanup_tasks)

    @pytest.mark.asyncio
    async def test_database_error_handling(self, integration_service):
        """Test database error handling"""
        # Try to get a non-existent session
        result = await integration_service.get_session("non-existent-id", "user-123")
        assert result is None

        # Try to delete a non-existent session
        deleted = await integration_service.delete_session(
            "non-existent-id", "user-123"
        )
        assert deleted is False

        # Try to add message to non-existent session
        message = ChatMessage(
            role="user", content="Test message", timestamp=datetime.utcnow()
        )
        result = await integration_service.add_message(
            "non-existent-id", "user-123", message
        )
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
