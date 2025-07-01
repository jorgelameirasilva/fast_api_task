import uuid
from datetime import datetime
from typing import List, Optional
from loguru import logger
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from ..core.database import get_sessions_collection
from ..schemas.session import SessionMessage, SessionMessageCreate


class SessionService:
    def __init__(self):
        self.collection: Collection = get_sessions_collection()

    def add_message(self, message_create: SessionMessageCreate) -> SessionMessage:
        """Add a new message"""
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
            logger.info(
                f"Added message {message_id} to session: {message_create.session_id}"
            )

            return SessionMessage(**message_data)
        except PyMongoError as e:
            logger.error(f"Failed to add message: {e}")
            raise

    def get_session_messages(
        self, session_id: str, user_id: str
    ) -> List[SessionMessage]:
        """Get all messages for a session"""
        try:
            messages_data = self.collection.find(
                {"session_id": session_id, "user_id": user_id}
            ).sort("created_at", 1)

            messages = [SessionMessage(**msg) for msg in messages_data]
            logger.info(f"Retrieved {len(messages)} messages for session: {session_id}")

            return messages
        except PyMongoError as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            raise


# Global session service instance
session_service = SessionService()
