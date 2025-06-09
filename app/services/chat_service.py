from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    ChatContext,
    Overrides,
    ChatChoice,
    ChatDelta,
    ChatContentData,
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

            # Extract overrides from structured context
            overrides = {}
            if request.context and request.context.overrides:
                overrides = request.context.overrides.model_dump(exclude_none=True)

            # Prepare context for approach - match old code structure
            context = {
                "overrides": overrides,
                "auth_claims": {},
            }

            # Add any additional context from request
            if hasattr(request, "session_state") and request.session_state:
                context["session_state"] = request.session_state

            # Run the approach based on streaming preference
            if stream:
                # For now, treat streaming the same as non-streaming for response structure
                # The streaming functionality can be enhanced later for actual streaming responses
                approach_result = await chat_approach.run_without_streaming(
                    messages=messages,
                    overrides=overrides,
                    auth_claims=context.get("auth_claims", {}),
                    session_state=request.session_state,
                )
            else:
                approach_result = await chat_approach.run_without_streaming(
                    messages=messages,
                    overrides=overrides,
                    auth_claims=context.get("auth_claims", {}),
                    session_state=request.session_state,
                )

            # Convert approach result to ChatResponse
            if isinstance(approach_result, dict) and "choices" in approach_result:
                choice = approach_result["choices"][0]
                message_content = choice["message"]["content"]
                message_context = choice["message"].get("context", {})

                # Create the choice object based on whether it's streaming or not
                if stream:
                    # For streaming responses, use delta format
                    chat_choice = ChatChoice(
                        delta=ChatDelta(role="assistant", content=message_content),
                        content=ChatContentData(
                            data_points=message_context.get("data_points", []),
                            thoughts=message_context.get("thoughts", ""),
                        ),
                        function_call=None,
                        tool_calls=None,
                        finish_reason=choice.get("finish_reason"),
                    )
                else:
                    # For non-streaming responses, use complete message format
                    response_message = ChatMessage(
                        role="assistant",
                        content=message_content,
                        timestamp=datetime.now(),
                    )

                    chat_choice = ChatChoice(
                        message=response_message,
                        content=ChatContentData(
                            data_points=message_context.get("data_points", []),
                            thoughts=message_context.get("thoughts", ""),
                        ),
                        function_call=None,
                        tool_calls=None,
                        finish_reason=choice.get("finish_reason"),
                    )

                # Update session if needed
                if request.session_state:
                    await self.session_service.update_session(
                        request.session_state,
                        len(request.messages) + 1,
                        "chat_approach",
                    )

                # Build response context - include approach details and preserve structure
                response_overrides = Overrides(**overrides) if overrides else None
                response_context = ChatContext(overrides=response_overrides)

                return ChatResponse(
                    choices=[chat_choice],
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
        context_dict = {}
        if request.context and request.context.overrides:
            context_dict = request.context.overrides.model_dump(exclude_none=True)

        response_content = await self._generate_chat_response(
            last_user_message, context_dict
        )

        # Create choice object
        if stream:
            chat_choice = ChatChoice(
                delta=ChatDelta(role="assistant", content=response_content),
                function_call=None,
                tool_calls=None,
            )
        else:
            response_message = ChatMessage(
                role="assistant", content=response_content, timestamp=datetime.now()
            )
            chat_choice = ChatChoice(
                message=response_message, function_call=None, tool_calls=None
            )

        # Update session if needed
        if request.session_state:
            await self.session_service.update_session(
                request.session_state, len(request.messages) + 1, "chat_simple"
            )

        # Build context - preserve the original structure if it exists
        response_context = request.context or ChatContext()

        return ChatResponse(
            choices=[chat_choice],
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
