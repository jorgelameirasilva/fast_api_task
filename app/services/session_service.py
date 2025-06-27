import uuid
from datetime import datetime
from typing import Optional
from loguru import logger
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from ..core.database import get_sessions_collection
from ..schemas.session import Session, SessionCreate, SessionUpdate, SessionMessage


class SessionService:
    def __init__(self):
        self.collection: Collection = get_sessions_collection()

    def create_session(self, session_create: SessionCreate) -> Session:
        """Create a new chat session"""
        try:
            session_id = str(uuid.uuid4())
            session_data = {
                "_id": session_id,
                "user_id": session_create.user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "messages": [],
            }

            self.collection.insert_one(session_data)
            logger.info(
                f"Created new session: {session_id} for user: {session_create.user_id}"
            )

            return Session(**session_data)
        except PyMongoError as e:
            logger.error(f"Failed to create session: {e}")
            raise

    def get_session(self, session_id: str, user_id: str) -> Optional[Session]:
        """Get a session by ID and user ID"""
        try:
            session_data = self.collection.find_one(
                {"_id": session_id, "user_id": user_id}
            )

            if session_data:
                return Session(**session_data)
            return None
        except PyMongoError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise

    def update_session(
        self, session_id: str, user_id: str, session_update: SessionUpdate
    ) -> Optional[Session]:
        """Update a session with new messages"""
        try:
            # Convert SessionMessage objects to dict for MongoDB
            messages_data = [
                {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                for msg in session_update.messages
            ]

            result = self.collection.update_one(
                {"_id": session_id, "user_id": user_id},
                {
                    "$set": {
                        "messages": messages_data,
                        "updated_at": session_update.updated_at,
                    }
                },
            )

            if result.modified_count > 0:
                logger.info(f"Updated session: {session_id}")
                return self.get_session(session_id, user_id)
            return None
        except PyMongoError as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise

    def add_message_to_session(
        self, session_id: str, user_id: str, message: SessionMessage
    ) -> Optional[Session]:
        """Add a single message to a session"""
        try:
            message_data = {
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp,
            }

            result = self.collection.update_one(
                {"_id": session_id, "user_id": user_id},
                {
                    "$push": {"messages": message_data},
                    "$set": {"updated_at": datetime.utcnow()},
                },
            )

            if result.modified_count > 0:
                logger.info(f"Added message to session: {session_id}")
                return self.get_session(session_id, user_id)
            return None
        except PyMongoError as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            raise


# Global session service instance
session_service = SessionService()
