"""
Session Service - Bridges between API schemas and CosmosService
"""

import logging
from typing import List
from app.schemas.session import SessionMessage, SessionMessageCreate
from app.models.document import MessageCreateRequest, MessageContent
from app.services.cosmos_service import create_cosmos_service

logger = logging.getLogger(__name__)


class SessionService:
    """Service that handles session operations using CosmosService backend"""

    def __init__(self):
        self.cosmos_service = create_cosmos_service()

    async def get_session_messages(
        self, session_id: str, user_id: str
    ) -> List[SessionMessage]:
        """Get all messages for a session"""
        try:
            # Get messages from CosmosService
            messages = await self.cosmos_service.get_conversation(session_id, user_id)

            # Convert to schema format
            session_messages = []
            for msg in messages:
                session_msg = SessionMessage(
                    id=msg.id,
                    user_id=msg.user_id,
                    session_id=msg.session_id,
                    message={"role": msg.message.role, "content": msg.message.content},
                    created_at=msg.created_at,
                )
                session_messages.append(session_msg)

            return session_messages
        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return []

    async def add_message(self, message_create: SessionMessageCreate) -> SessionMessage:
        """Add a message to a session"""
        try:
            # Convert schema format to CosmosService format
            cosmos_request = MessageCreateRequest(
                session_id=message_create.session_id,
                message=MessageContent(
                    role=message_create.message["role"],
                    content=message_create.message["content"],
                ),
                knowledge_base=None,  # Will be set by context if needed
            )

            # Create message using CosmosService
            created_msg = await self.cosmos_service.create_message(
                cosmos_request, message_create.user_id
            )

            # Convert back to schema format
            session_msg = SessionMessage(
                id=created_msg.id,
                user_id=created_msg.user_id,
                session_id=created_msg.session_id,
                message={
                    "role": created_msg.message.role,
                    "content": created_msg.message.content,
                },
                created_at=created_msg.created_at,
            )

            return session_msg
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise

    async def get_user_sessions(self, user_id: str):
        """Get all sessions for a user"""
        try:
            return await self.cosmos_service.get_user_sessions(user_id)
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session"""
        try:
            return await self.cosmos_service.delete_session(session_id, user_id)
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False


# Global instance
session_service = SessionService()
