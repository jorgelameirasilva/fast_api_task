from datetime import datetime
from typing import Dict, Any
from loguru import logger


class SessionService:
    """Service focused solely on session management"""

    def __init__(self):
        self.session_storage: Dict[str, Any] = {}

    async def update_session(
        self, session_id: str, message_count: int, interaction_type: str = "chat"
    ) -> None:
        """Update session with interaction details"""
        logger.debug(
            f"Updating session {session_id} with interaction type {interaction_type}"
        )

        self.session_storage[session_id] = {
            "last_interaction": datetime.now(),
            "message_count": message_count,
            "interaction_type": interaction_type,
        }

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session data by ID"""
        return self.session_storage.get(session_id, {})

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and return True if it existed"""
        return self.session_storage.pop(session_id, None) is not None

    async def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Remove sessions older than max_age_hours and return count of removed sessions"""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session_data in self.session_storage.items():
            last_interaction = session_data.get("last_interaction")
            if last_interaction:
                age_hours = (current_time - last_interaction).total_seconds() / 3600
                if age_hours > max_age_hours:
                    expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.session_storage[session_id]

        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)


# Create singleton instance
session_service = SessionService()
