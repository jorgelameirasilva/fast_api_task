from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
)
from app.core.config import settings
from app.services.session_service import SessionService
from app.services.response_generator import ResponseGenerator


class ChatService:
    """Service focused solely on chat operations"""

    def __init__(
        self,
        session_service: SessionService = None,
        response_generator: ResponseGenerator = None,
    ):
        self.session_service = session_service or SessionService()
        self.response_generator = response_generator or ResponseGenerator()
        self.session_storage: Dict[str, Any] = {}

    async def process_chat(
        self, request: ChatRequest, stream: bool = False
    ) -> ChatResponse:
        """Process a chat request - simple legacy-style processing"""
        logger.info(f"Processing chat with {len(request.messages)} messages")

        # Validate request
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise ValueError("No user message found in chat request")

        # Get the last user message for processing
        last_user_message = user_messages[-1].content

        try:
            # Generate a simple response
            response_content = await self._generate_chat_response(
                last_user_message, request.context or {}
            )

            # Create response message
            response_message = ChatMessage(
                role="assistant", content=response_content, timestamp=datetime.now()
            )

            # Update session if needed
            if request.session_state:
                await self.session_service.update_session(
                    request.session_state, len(request.messages) + 1, "chat"
                )

            # Build context
            response_context = {
                **(request.context or {}),
                "streaming": stream,
                "session_updated": request.session_state is not None,
                "chat_processed_at": datetime.now().isoformat(),
            }

            return ChatResponse(
                message=response_message,
                session_state=request.session_state,
                context=response_context,
            )

        except Exception as e:
            logger.error(f"Error processing chat: {e}")
            return await self._build_fallback_response(request)

    async def _build_fallback_response(self, request: ChatRequest) -> ChatResponse:
        """Build fallback response when processing fails"""
        logger.warning("Using fallback response for chat request")

        fallback_content = (
            "I apologize, but I encountered an issue while processing your message. "
            "Please try rephrasing your question or contact support for assistance."
        )

        response_message = ChatMessage(
            role="assistant", content=fallback_content, timestamp=datetime.now()
        )

        return ChatResponse(
            message=response_message,
            session_state=request.session_state,
            context={
                "error": "chat_processing_failed",
                "fallback_used": True,
                "chat_processed_at": datetime.now().isoformat(),
            },
        )

    async def _generate_chat_response(
        self, user_message: str, context: Dict[str, Any]
    ) -> str:
        """
        Generate a response to user message using the response generator
        """
        try:
            # Use the response generator service
            response = await self.response_generator.generate_chat_response(
                user_message, context
            )
            return response
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            # Simple fallback response
            return f"Thank you for your message: '{user_message}'. How can I help you further?"


# Create service instance
chat_service = ChatService()
