"""
Chat Orchestrator - Orchestrates chat requests following SOLID principles
Single Responsibility: Coordinates between services and handles response formatting
"""

import logging
from typing import Any, Dict

from app.schemas.chat import ChatRequest
from app.services.chat_service import chat_service
from app.services.session_service import session_service

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    Orchestrates chat requests following SOLID principles
    Single Responsibility: Coordinate chat processing and response formatting
    """

    def __init__(self):
        pass

    async def process_chat_request(
        self, request: ChatRequest, current_user: dict[str, Any]
    ):
        """
        Process chat request - orchestrates the flow
        Returns ChatResponse directly
        """
        try:
            logger.info(f"Chat request from user: {current_user.get('oid', 'unknown')}")

            # Prepare context
            context = self._prepare_context(request, current_user)

            # Get result from chat service
            user_id = current_user.get("oid", "default_user")
            result = await chat_service.process_chat(request, context, user_id)

            return result

        except Exception as e:
            logger.error(f"Chat processing failed: {str(e)}")
            raise

    async def get_user_sessions(self, current_user: dict[str, Any]):
        """Get user's active sessions"""
        try:
            user_id = current_user.get("oid", "default_user")
            sessions = await session_service.get_user_sessions(user_id)
            return sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            raise

    async def get_conversation_history(
        self, session_id: str, current_user: dict[str, Any]
    ):
        """Get conversation history for a session"""
        try:
            user_id = current_user.get("oid", "default_user")
            messages = await session_service.get_session_messages(session_id, user_id)

            return {
                "session_id": session_id,
                "messages": messages,
                "total_messages": len(messages),
            }
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            raise

    async def delete_session(self, session_id: str, current_user: dict[str, Any]):
        """Delete a session"""
        try:
            user_id = current_user.get("oid", "default_user")
            success = await session_service.delete_session(session_id, user_id)

            if not success:
                return {"success": False, "message": "Session not found"}

            return {"success": True, "message": "Session deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            raise

    def _prepare_context(
        self, request: ChatRequest, current_user: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare context for chat processing"""
        # Handle both dict and Pydantic model contexts
        if hasattr(request.context, "model_copy"):
            # It's a Pydantic model
            context = request.context.model_copy() if request.context else {}
        elif hasattr(request.context, "copy"):
            # It's a regular dict
            context = request.context.copy() if request.context else {}
        else:
            # Fallback
            context = dict(request.context) if request.context else {}

        context["auth_claims"] = current_user
        return context


# Global instance
chat_orchestrator = ChatOrchestrator()
