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
        """Process a chat request using approaches as primary method"""
        logger.info(f"Processing chat with {len(request.messages)} messages")

        # Validate request
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise ValueError("No user message found in chat request")

        try:
            # Primary: Use approaches (matching old code structure)
            return await self._process_with_approaches(request, stream)

        except Exception as e:
            logger.error(f"Approach processing failed: {e}")
            # Only fallback to simple processing if approaches completely fail
            logger.warning("Falling back to simple processing due to approach failure")
            return await self._process_simple(request, stream)

    async def _process_with_approaches(
        self, request: ChatRequest, stream: bool
    ) -> ChatResponse:
        """Process chat using the approach system - primary method"""
        logger.info("Using approach system for chat processing")

        try:
            from app.core.setup import get_chat_approach

            chat_approach = get_chat_approach()
            if not chat_approach:
                raise ValueError("No chat approach configured")

            # Convert messages to the format expected by approaches
            messages = []
            for msg in request.messages:
                messages.append({"role": msg.role, "content": msg.content})

            # Prepare context for approach - match old code structure
            context = {
                "overrides": request.context or {},
                "auth_claims": {},
            }

            # Add any additional context from request
            if hasattr(request, "session_state") and request.session_state:
                context["session_state"] = request.session_state

            # Run the approach based on streaming preference
            if stream:
                approach_result = await chat_approach.run_with_streaming(
                    messages=messages,
                    overrides=context.get("overrides", {}),
                    auth_claims=context.get("auth_claims", {}),
                    session_state=request.session_state,
                )
            else:
                approach_result = await chat_approach.run_without_streaming(
                    messages=messages,
                    overrides=context.get("overrides", {}),
                    auth_claims=context.get("auth_claims", {}),
                    session_state=request.session_state,
                )

            # Convert approach result to ChatResponse
            if isinstance(approach_result, dict) and "choices" in approach_result:
                choice = approach_result["choices"][0]
                message_content = choice["message"]["content"]
                message_context = choice["message"].get("context", {})

                response_message = ChatMessage(
                    role="assistant", content=message_content, timestamp=datetime.now()
                )

                # Update session if needed
                if request.session_state:
                    await self.session_service.update_session(
                        request.session_state,
                        len(request.messages) + 1,
                        "chat_approach",
                    )

                # Build response context - include approach details
                response_context = {
                    **(request.context or {}),
                    "approach_used": "chat_read_retrieve_read",
                    "approach_type": chat_approach.__class__.__name__,
                    "streaming": stream,
                    "session_updated": request.session_state is not None,
                    "chat_processed_at": datetime.now().isoformat(),
                    **message_context,
                }

                return ChatResponse(
                    message=response_message,
                    session_state=request.session_state,
                    context=response_context,
                )

            else:
                raise ValueError("Invalid approach result format")

        except Exception as e:
            logger.error(f"Approach processing failed: {e}")
            raise

    async def _process_simple(self, request: ChatRequest, stream: bool) -> ChatResponse:
        """Process chat using simple response generation - fallback only"""
        logger.warning(
            "Using simple response generation for chat processing (fallback)"
        )

        # Get the last user message for processing
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        last_user_message = user_messages[-1].content

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
                request.session_state, len(request.messages) + 1, "chat_simple"
            )

        # Build context
        response_context = {
            **(request.context or {}),
            "approach_used": "simple_fallback",
            "streaming": stream,
            "session_updated": request.session_state is not None,
            "chat_processed_at": datetime.now().isoformat(),
            "fallback_reason": "approach_processing_failed",
        }

        return ChatResponse(
            message=response_message,
            session_state=request.session_state,
            context=response_context,
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
