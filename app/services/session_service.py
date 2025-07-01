"""
Session Service - Simple conversation history storage in Cosmos DB
Only handles saving and retrieving conversation messages
"""

import uuid
from datetime import datetime
from typing import List
from loguru import logger
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from ..core.database import get_sessions_collection
from ..schemas.session import SessionMessage, SessionMessageCreate


class SessionService:
    """Simple service for conversation history storage"""

    def __init__(self):
        self.collection: Collection = get_sessions_collection()

    def add_message(self, message_create: SessionMessageCreate) -> SessionMessage:
        """Save a conversation message to database"""
        try:
            message_id = str(uuid.uuid4())
            message_data = {
                "_id": message_id,
                "user_id": message_create.user_id,
                "session_id": message_create.session_id,
                "message": message_create.message,
                "created_at": datetime.utcnow(),
            }

            self.collection.insert_one(message_data)
            logger.info(f"Saved message to session {message_create.session_id}")

            return SessionMessage(**message_data)
        except PyMongoError as e:
            logger.error(f"Failed to save message: {e}")
            raise

    def get_session_messages(
        self, session_id: str, user_id: str
    ) -> List[SessionMessage]:
        """Get conversation history for a session"""
        try:
            messages_data = self.collection.find(
                {"session_id": session_id, "user_id": user_id}
            ).sort("created_at", 1)

            messages = [SessionMessage(**msg) for msg in messages_data]
            logger.info(f"Retrieved {len(messages)} messages for session {session_id}")

            return messages
        except PyMongoError as e:
            logger.error(f"Failed to get session messages: {e}")
            raise


# Global session service instance
session_service = SessionService()
