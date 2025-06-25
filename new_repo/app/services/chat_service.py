"""
Chat Service - Handles chat business logic following SOLID principles
Single Responsibility: Manage chat approach and process chat requests
"""

from typing import Any
from loguru import logger

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)
from app.core.setup import get_chat_approach


class ChatService:
    """Service focused solely on chat operations"""

    def __init__(
        self,
    ):
        self.session_storage: dict[str, Any] = {}

    async def process_chat(
        self, request: ChatRequest, context: dict[str, Any]
    ) -> ChatResponse:
        """Process a chat request using approaches as primary method"""
        logger.info(f"Processing chat with {len(request.messages)} messages")

        try:
            chat_approach = get_chat_approach()
            if not chat_approach:
                raise ValueError("No chat approach configured")

            session_state = None

            if hasattr(request, "session_state") and request.session_state:
                session_state = request.session_state

            # Convert ChatMessage objects to dictionaries for the approach
            messages_dict = [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ]

            approach_result = await chat_approach.run(
                messages=messages_dict,
                stream=request.stream or False,
                context=context,
                session_state=session_state,
            )

            return approach_result

        except Exception as e:
            logger.error(f"Approach processing failed: {e}")
            raise


# Create service instance
chat_service = ChatService()
