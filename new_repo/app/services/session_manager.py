"""
Session Management Service - Handles all session-related business logic
Follows Single Responsibility Principle
"""

import logging
from typing import Dict, Any, Optional, List
from app.models.chat import ChatMessage, ChatRequest
from app.models.session import ChatSession
from app.services.cosmos_service import cosmos_session_service

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Handles all session management logic
    Single responsibility: Manage conversation sessions
    """

    def __init__(self):
        self.cosmos_service = cosmos_session_service

    async def get_or_create_session(
        self,
        session_id: Optional[str],
        user_id: str,
        request_context: Dict[str, Any] = None,
    ) -> ChatSession:
        """
        Get existing session or create new one

        Args:
            session_id: Optional session ID to continue
            user_id: User identifier for session ownership
            request_context: Additional context from request

        Returns:
            ChatSession: The session to use for conversation
        """
        try:
            if session_id:
                # Try to get existing session
                existing_session = await self.cosmos_service.get_session(
                    session_id, user_id
                )
                if existing_session:
                    logger.info(f"Continuing existing session: {session_id}")
                    return existing_session
                else:
                    logger.warning(
                        f"Session {session_id} not found, creating new session"
                    )

            # Create new session
            logger.info(f"Creating new session for user: {user_id}")
            return await self.cosmos_service.create_session(
                user_id=user_id, context=request_context or {}
            )

        except Exception as e:
            logger.error(f"Session management error: {str(e)}")
            raise

    async def add_user_messages_to_session(
        self,
        session: ChatSession,
        messages: List[ChatMessage],
        context_update: Dict[str, Any] = None,
    ) -> ChatSession:
        """
        Add user messages to session

        Args:
            session: The session to update
            messages: List of messages to add
            context_update: Optional context updates

        Returns:
            Updated ChatSession
        """
        try:
            updated_session = session

            # Add each user message
            for message in messages:
                if message.role == "user":
                    updated_session = await self.cosmos_service.add_message_to_session(
                        session_id=session.id,
                        user_id=session.user_id,
                        message=message,
                        update_context=context_update,
                    )

            return updated_session

        except Exception as e:
            logger.error(f"Error adding messages to session: {str(e)}")
            raise

    async def add_assistant_message_to_session(
        self, session: ChatSession, message: ChatMessage
    ) -> None:
        """
        Add assistant response to session

        Args:
            session: The session to update
            message: Assistant message to add
        """
        try:
            await self.cosmos_service.add_message_to_session(
                session_id=session.id, user_id=session.user_id, message=message
            )
            logger.debug(f"Added assistant message to session {session.id}")

        except Exception as e:
            logger.error(f"Error adding assistant message to session: {str(e)}")
            raise

    def prepare_conversation_context(
        self, session: ChatSession, request: ChatRequest, auth_claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare context for AI conversation

        Args:
            session: The conversation session
            request: The chat request
            auth_claims: Authentication claims

        Returns:
            Context dictionary for AI processing
        """
        context = session.context.copy()
        context.update(request.context)
        context["auth_claims"] = auth_claims
        context["session_id"] = session.id

        return context

    def get_conversation_history(self, session: ChatSession) -> List[Dict[str, str]]:
        """
        Extract conversation history for AI processing

        Args:
            session: The conversation session

        Returns:
            List of message dictionaries for AI
        """
        return [{"role": msg.role, "content": msg.content} for msg in session.messages]


# Global instance
session_manager = SessionManager()
