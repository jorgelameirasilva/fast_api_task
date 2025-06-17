"""Session Manager for handling chat sessions"""

import logging
import uuid
from datetime import datetime
from typing import Any

from app.models.session import Session
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session manager for handling chat sessions
    Simplified implementation for the demo
    """

    def __init__(self):
        # In-memory storage for demo purposes
        self.sessions: dict[str, Session] = {}
        self.user_sessions: dict[str, list[str]] = {}

    async def create_session(
        self, user_id: str, context: dict[str, Any] = None
    ) -> Session:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())

        session = Session(
            id=session_id,
            user_id=user_id,
            context=context or {},
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Store session
        self.sessions[session_id] = session

        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_id)

        logger.info(f"Created session {session_id} for user {user_id}")
        return session

    async def get_session(self, session_id: str, user_id: str) -> Session | None:
        """Get a session by ID if it belongs to the user"""
        session = self.sessions.get(session_id)

        if session and session.user_id == user_id:
            return session

        return None

    async def update_session_context(
        self, session_id: str, user_id: str, context: dict[str, Any]
    ) -> Session | None:
        """Update session context"""
        session = await self.get_session(session_id, user_id)

        if session:
            session.context.update(context)
            session.updated_at = datetime.utcnow()
            logger.info(f"Updated context for session {session_id}")

        return session

    async def add_message_to_session(
        self, session_id: str, user_id: str, message: ChatMessage
    ) -> Session | None:
        """Add a message to the session"""
        session = await self.get_session(session_id, user_id)

        if session:
            session.messages.append(message)
            session.updated_at = datetime.utcnow()
            logger.info(f"Added message to session {session_id}")

        return session

    async def get_user_sessions(self, user_id: str) -> list[Session]:
        """Get all sessions for a user"""
        session_ids = self.user_sessions.get(user_id, [])
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions]

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session"""
        session = await self.get_session(session_id, user_id)

        if session:
            # Remove from sessions
            del self.sessions[session_id]

            # Remove from user sessions
            if user_id in self.user_sessions:
                self.user_sessions[user_id].remove(session_id)

            logger.info(f"Deleted session {session_id}")
            return True

        return False


# Global instance
session_manager = SessionManager()
