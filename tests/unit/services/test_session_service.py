import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.session_service import SessionService


class TestSessionService:
    """Unit tests for SessionService"""

    @pytest.mark.asyncio
    async def test_update_session(self, session_service):
        """Test updating session with interaction details"""
        # Arrange
        session_id = "test-session-123"
        message_count = 5
        approach_used = "TestApproach"

        # Act
        await session_service.update_session(session_id, message_count, approach_used)

        # Assert
        assert session_id in session_service.session_storage
        session_data = session_service.session_storage[session_id]
        assert session_data["message_count"] == message_count
        assert session_data["interaction_type"] == approach_used

    @pytest.mark.asyncio
    async def test_update_session_overwrites_existing(self, session_service):
        """Test that updating session overwrites existing data"""
        # Arrange
        session_id = "test-session-123"

        # First update
        await session_service.update_session(session_id, 1, "FirstApproach")
        first_update_time = session_service.session_storage[session_id][
            "last_interaction"
        ]

        # Small delay to ensure different timestamps
        import asyncio

        await asyncio.sleep(0.01)

        # Second update
        await session_service.update_session(session_id, 3, "SecondApproach")

        # Assert
        session_data = session_service.session_storage[session_id]
        assert session_data["message_count"] == 3
        assert session_data["interaction_type"] == "SecondApproach"

    @pytest.mark.asyncio
    async def test_get_session_existing(self, session_service):
        """Test getting existing session data"""
        # Arrange
        session_id = "test-session-123"
        await session_service.update_session(session_id, 2, "TestApproach")

        # Act
        session_data = await session_service.get_session(session_id)

        # Assert
        assert session_data["message_count"] == 2
        assert session_data["interaction_type"] == "TestApproach"

    @pytest.mark.asyncio
    async def test_get_session_nonexistent(self, session_service):
        """Test getting nonexistent session data"""
        # Act
        session_data = await session_service.get_session("nonexistent-session")

        # Assert
        assert session_data == {}

    @pytest.mark.asyncio
    async def test_delete_session_existing(self, session_service):
        """Test deleting existing session"""
        # Arrange
        session_id = "test-session-123"
        await session_service.update_session(session_id, 1, "TestApproach")
        assert session_id in session_service.session_storage

        # Act
        result = await session_service.delete_session(session_id)

        # Assert
        assert result is True
        assert session_id not in session_service.session_storage

    @pytest.mark.asyncio
    async def test_delete_session_nonexistent(self, session_service):
        """Test deleting nonexistent session"""
        # Act
        result = await session_service.delete_session("nonexistent-session")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_no_sessions(self, session_service):
        """Test cleanup with no sessions"""
        # Act
        removed_count = await session_service.cleanup_expired_sessions()

        # Assert
        assert removed_count == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_no_expired(self, session_service):
        """Test cleanup with no expired sessions"""
        # Arrange - Add recent sessions
        await session_service.update_session("session1", 1, "Approach1")
        await session_service.update_session("session2", 2, "Approach2")

        # Act
        removed_count = await session_service.cleanup_expired_sessions(max_age_hours=24)

        # Assert
        assert removed_count == 0
        assert len(session_service.session_storage) == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_with_expired(self, session_service):
        """Test cleanup with expired sessions"""
        # Arrange - Mock datetime to create old sessions
        old_time = datetime.now() - timedelta(hours=25)
        recent_time = datetime.now()

        # Add old session manually
        session_service.session_storage["old-session"] = {
            "last_interaction": old_time,
            "message_count": 1,
            "interaction_type": "OldApproach",
        }

        # Add recent session
        await session_service.update_session("recent-session", 2, "RecentApproach")

        # Act
        removed_count = await session_service.cleanup_expired_sessions(max_age_hours=24)

        # Assert
        assert removed_count == 1
        assert "old-session" not in session_service.session_storage
        assert "recent-session" in session_service.session_storage

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_all_expired(self, session_service):
        """Test cleanup when all sessions are expired"""
        # Arrange - Add old sessions manually
        old_time = datetime.now() - timedelta(hours=48)

        for i in range(3):
            session_service.session_storage[f"old-session-{i}"] = {
                "last_interaction": old_time,
                "message_count": 1,
                "interaction_type": f"OldApproach{i}",
            }

        # Act
        removed_count = await session_service.cleanup_expired_sessions(max_age_hours=24)

        # Assert
        assert removed_count == 3
        assert len(session_service.session_storage) == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_custom_max_age(self, session_service):
        """Test cleanup with custom max age"""
        # Arrange - Add session that's 2 hours old
        old_time = datetime.now() - timedelta(hours=2)
        session_service.session_storage["medium-old-session"] = {
            "last_interaction": old_time,
            "message_count": 1,
            "interaction_type": "MediumOldApproach",
        }

        # Act with 1 hour max age
        removed_count = await session_service.cleanup_expired_sessions(max_age_hours=1)

        # Assert
        assert removed_count == 1
        assert len(session_service.session_storage) == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_no_last_interaction(self, session_service):
        """Test cleanup with sessions missing last_interaction"""
        # Arrange - Add session without last_interaction
        session_service.session_storage["invalid-session"] = {
            "message_count": 1,
            "interaction_type": "InvalidApproach",
            # Missing last_interaction
        }

        # Act
        removed_count = await session_service.cleanup_expired_sessions(max_age_hours=24)

        # Assert
        assert removed_count == 0  # Session without last_interaction is not removed
        assert "invalid-session" in session_service.session_storage

    @pytest.mark.asyncio
    async def test_multiple_sessions_different_ages(self, session_service):
        """Test cleanup with multiple sessions of different ages"""
        # Arrange
        current_time = datetime.now()

        # Recent session (1 hour old)
        session_service.session_storage["recent"] = {
            "last_interaction": current_time - timedelta(hours=1),
            "message_count": 1,
            "interaction_type": "RecentApproach",
        }

        # Medium old session (12 hours old)
        session_service.session_storage["medium"] = {
            "last_interaction": current_time - timedelta(hours=12),
            "message_count": 2,
            "interaction_type": "MediumApproach",
        }

        # Old session (30 hours old)
        session_service.session_storage["old"] = {
            "last_interaction": current_time - timedelta(hours=30),
            "message_count": 3,
            "interaction_type": "OldApproach",
        }

        # Act
        removed_count = await session_service.cleanup_expired_sessions(max_age_hours=24)

        # Assert
        assert removed_count == 1
        assert "recent" in session_service.session_storage
        assert "medium" in session_service.session_storage
        assert "old" not in session_service.session_storage

    @pytest.mark.asyncio
    async def test_session_storage_isolation(self):
        """Test that different SessionService instances have isolated storage"""
        # Arrange
        service1 = SessionService()
        service2 = SessionService()

        # Act
        await service1.update_session("session1", 1, "Approach1")
        await service2.update_session("session2", 2, "Approach2")

        # Assert
        assert "session1" in service1.session_storage
        assert "session1" not in service2.session_storage
        assert "session2" in service2.session_storage
        assert "session2" not in service1.session_storage

    @pytest.mark.asyncio
    async def test_session_data_structure(self, session_service):
        """Test that session data has correct structure"""
        # Arrange
        session_id = "test-session"
        message_count = 10
        approach_used = "ComplexApproach"

        # Act
        await session_service.update_session(session_id, message_count, approach_used)

        # Assert
        session_data = session_service.session_storage[session_id]
        assert set(session_data.keys()) == {
            "last_interaction",
            "message_count",
            "interaction_type",
        }
        assert isinstance(session_data["last_interaction"], datetime)
        assert isinstance(session_data["message_count"], int)
        assert isinstance(session_data["interaction_type"], str)
