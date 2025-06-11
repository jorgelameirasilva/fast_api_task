from datetime import datetime
from typing import Dict, Any, List, Optional
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
from app.auth.models import AuthUser
from app.core.config import settings
from app.services.session_service import SessionService
from app.services.response_generator import ResponseGenerator


class ChatService:
    """Service focused solely on chat operations with proper dependency injection"""

    def __init__(
        self,
        session_service: SessionService = None,
        response_generator: ResponseGenerator = None,
    ):
        self.session_service = session_service or SessionService()
        self.response_generator = response_generator or ResponseGenerator()
        self.session_storage: Dict[str, Any] = {}

    async def process_chat(
        self,
        request: ChatRequest,
        stream: bool = False,
        current_user: Optional[AuthUser] = None,
    ) -> ChatResponse:
        """
        Process a chat request using approaches as primary method.

        Args:
            request: The chat request with messages and context
            stream: Whether to stream the response
            current_user: Authenticated user from JWT token
        """
        logger.info(f"Processing chat with {len(request.messages)} messages")

        # Validate request
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise ValueError("No user message found in chat request")

        # Log user context for auditing (production-grade logging)
        if current_user:
            logger.info(f"Chat request from user: {current_user.user_id}")

        try:
            # Primary: Use approaches (matching old code structure)
            return await self._process_with_approaches(request, stream, current_user)

        except Exception as e:
            logger.error(f"Approach processing failed: {e}")
            # Only fallback to simple processing if approaches completely fail
            logger.warning("Falling back to simple processing due to approach failure")
            return await self._process_simple(request, stream, current_user)

    def _extract_auth_claims(
        self, current_user: Optional[AuthUser] = None
    ) -> Dict[str, Any]:
        """
        Extract auth claims from current user context.
        This centralizes the claim extraction logic and makes it easily testable.

        Args:
            current_user: The authenticated user model

        Returns:
            Dictionary with standardized auth claims for the approach system
        """
        if not current_user:
            return {}

        return {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "name": current_user.name,
            "preferred_username": current_user.preferred_username,
            "roles": current_user.roles,
            "groups": current_user.groups,
            "scope": current_user.scope,
            "token_valid": True,
            "iat": (
                int(current_user.issued_at.timestamp())
                if current_user.issued_at
                else None
            ),
            "exp": (
                int(current_user.expires_at.timestamp())
                if current_user.expires_at
                else None
            ),
        }

    async def _process_with_approaches(
        self,
        request: ChatRequest,
        stream: bool,
        current_user: Optional[AuthUser] = None,
    ) -> ChatResponse:
        """Process chat using the approach system - primary method"""
        logger.info("Using approach system for chat processing")

        try:
            from app.core.setup import get_chat_approach

            chat_approach = get_chat_approach()
            if not chat_approach:
                raise ValueError("No chat approach configured")

            # Convert messages to the format expected by approaches
            messages = self._convert_messages_for_approach(request.messages)

            # Extract overrides from structured context
            overrides = self._extract_overrides(request.context)

            # Extract auth claims from current user (separation of concerns)
            auth_claims = self._extract_auth_claims(current_user)

            # Run the approach
            approach_result = await chat_approach.run_without_streaming(
                messages=messages,
                overrides=overrides,
                auth_claims=auth_claims,
                session_state=request.session_state,
            )

            # Update session if needed
            await self._update_session_if_needed(
                request.session_state, len(request.messages) + 1, "chat_approach"
            )

            # Convert approach result to ChatResponse
            return self._create_chat_response_from_approach(
                approach_result, request, overrides, stream
            )

        except Exception as e:
            logger.error(f"Approach processing failed: {e}")
            raise

    async def _process_simple(
        self,
        request: ChatRequest,
        stream: bool,
        current_user: Optional[AuthUser] = None,
    ) -> ChatResponse:
        """Process chat using simple response generation - fallback only"""
        logger.warning(
            "Using simple response generation for chat processing (fallback)"
        )

        # Get the last user message for processing
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        last_user_message = user_messages[-1].content

        # Generate a simple response
        context_dict = self._extract_overrides(request.context)
        response_content = await self._generate_chat_response(
            last_user_message, context_dict
        )

        # Update session if needed
        await self._update_session_if_needed(
            request.session_state, len(request.messages) + 1, "chat_simple"
        )

        # Create simple response
        return self._create_simple_chat_response(response_content, request, stream)

    # === Helper Methods for Single Responsibility ===

    def _convert_messages_for_approach(
        self, messages: List[ChatMessage]
    ) -> List[Dict[str, str]]:
        """Convert ChatMessage objects to format expected by approaches"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def _extract_overrides(self, context: Optional[ChatContext]) -> Dict[str, Any]:
        """Extract overrides from chat context"""
        if context and context.overrides:
            return context.overrides.model_dump(exclude_none=True)
        return {}

    async def _update_session_if_needed(
        self, session_state: Optional[str], message_count: int, interaction_type: str
    ) -> None:
        """Update session if session_state is provided"""
        if session_state:
            await self.session_service.update_session(
                session_state, message_count, interaction_type
            )

    def _create_chat_response_from_approach(
        self,
        approach_result: Dict[str, Any],
        request: ChatRequest,
        overrides: Dict[str, Any],
        stream: bool,
    ) -> ChatResponse:
        """Create ChatResponse from approach result - follows SRP"""
        if not isinstance(approach_result, dict) or "choices" not in approach_result:
            raise ValueError("Invalid approach result format")

        choice = approach_result["choices"][0]
        message_content = choice["message"]["content"]
        message_context = choice["message"].get("context", {})

        # Create the choice object
        chat_choice = self._create_chat_choice_from_approach(
            message_content, message_context, choice, stream
        )

        # Build response context
        response_context = self._build_response_context(overrides)

        return ChatResponse(
            choices=[chat_choice],
            session_state=request.session_state,
            context=response_context,
        )

    def _create_chat_choice_from_approach(
        self,
        message_content: str,
        message_context: Dict[str, Any],
        choice: Dict[str, Any],
        stream: bool,
    ) -> ChatChoice:
        """Create ChatChoice object from approach data - follows SRP"""
        content_data = ChatContentData(
            data_points=message_context.get("data_points", []),
            thoughts=message_context.get("thoughts", ""),
        )

        if stream:
            # For streaming responses, use delta format
            return ChatChoice(
                delta=ChatDelta(role="assistant", content=message_content),
                content=content_data,
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

            return ChatChoice(
                message=response_message,
                content=content_data,
                function_call=None,
                tool_calls=None,
                finish_reason=choice.get("finish_reason"),
            )

    def _create_simple_chat_response(
        self, response_content: str, request: ChatRequest, stream: bool
    ) -> ChatResponse:
        """Create ChatResponse for simple processing - follows SRP"""
        # Create choice object
        chat_choice = self._create_simple_chat_choice(response_content, stream)

        # Build context - preserve the original structure if it exists
        response_context = request.context or ChatContext()

        return ChatResponse(
            choices=[chat_choice],
            session_state=request.session_state,
            context=response_context,
        )

    def _create_simple_chat_choice(
        self, response_content: str, stream: bool
    ) -> ChatChoice:
        """Create ChatChoice for simple responses - follows SRP"""
        if stream:
            return ChatChoice(
                delta=ChatDelta(role="assistant", content=response_content),
                function_call=None,
                tool_calls=None,
            )
        else:
            response_message = ChatMessage(
                role="assistant", content=response_content, timestamp=datetime.now()
            )
            return ChatChoice(
                message=response_message, function_call=None, tool_calls=None
            )

    def _build_response_context(self, overrides: Dict[str, Any]) -> ChatContext:
        """Build response context from overrides - follows SRP"""
        response_overrides = Overrides(**overrides) if overrides else None
        return ChatContext(overrides=response_overrides)

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
