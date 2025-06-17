"""
Chat Orchestrator

Orchestrates the complete chat workflow following SOLID principles.
Coordinates session management, chat processing, and streaming responses.
"""

import json
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.session_manager import SessionManager
from app.services.streaming_service import StreamingService

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    Orchestrates the complete chat workflow.

    Responsibilities:
    - Coordinate chat processing services
    - Handle session management
    - Manage streaming responses
    - Provide clean interface for chat operations
    """

    def __init__(
        self,
        chat_service: ChatService,
        session_manager: SessionManager,
        streaming_service: StreamingService,
    ):
        """
        Initialize orchestrator with required services.

        Args:
            chat_service: Service for chat processing
            session_manager: Service for session management
            streaming_service: Service for streaming responses
        """
        self.chat_service = chat_service
        self.session_manager = session_manager
        self.streaming_service = streaming_service
        self.logger = logging.getLogger(__name__)

    async def process_chat_request(
        self, request: ChatRequest, auth_claims: Dict[str, Any]
    ) -> StreamingResponse:
        """
        Process a complete chat request workflow with unified response handling.

        Args:
            request: The chat request
            auth_claims: Authentication claims from JWT

        Returns:
            StreamingResponse: Always returns streaming response (even for non-streaming)
        """
        user_id = auth_claims.get("oid", "unknown")

        try:
            self.logger.info(f"Processing chat request for user: {user_id}")

            # Handle session management
            session = await self.session_manager.get_or_create_session(
                session_id=request.session_state,
                user_id=user_id,
                request_context=request.context,
            )

            if not session:
                # Fallback to basic context when session is unavailable
                self.logger.warning("Session unavailable, using basic context")
                conversation_context = request.context.copy()
                conversation_context["auth_claims"] = auth_claims
                session_id = None
            else:
                # Add user messages to session
                session = await self.session_manager.add_user_messages_to_session(
                    session=session,
                    messages=request.messages,
                    context_update=request.context,
                )

                # Prepare conversation context
                conversation_context = (
                    self.session_manager.prepare_conversation_context(
                        session=session, request=request, auth_claims=auth_claims
                    )
                )
                session_id = session.id

            # Create the appropriate generator based on stream preference
            if request.stream:
                # Streaming response
                generator = self._process_streaming_chat(
                    request, conversation_context, session_id, auth_claims
                )
            else:
                # Non-streaming response (but still returned as stream for consistency)
                generator = self._process_non_streaming_chat(
                    request, conversation_context, session_id, auth_claims
                )

            # Use streaming service to create unified StreamingResponse
            return self.streaming_service.create_streaming_response(generator, session)

        except Exception as e:
            self.logger.error(f"Chat processing failed for user {user_id}: {str(e)}")

            # Return error as streaming response
            error_generator = self._create_error_generator(
                str(e), session_id if "session_id" in locals() else None
            )
            return StreamingResponse(
                error_generator,
                media_type="application/x-ndjson",
                headers={"Cache-Control": "no-cache"},
            )

    async def _process_streaming_chat(
        self,
        request: ChatRequest,
        context: Dict[str, Any],
        session_id: Optional[str],
        auth_claims: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """Process streaming chat request and yield formatted chunks"""
        try:
            # Process chat with session context
            async for response_chunk in self.chat_service.process_chat_with_session(
                request, context, session_id
            ):
                # Response chunk already has session info from service

                # Format for streaming
                formatted_chunk = self.streaming_service.format_streaming_response(
                    response_chunk
                )
                yield formatted_chunk

            # Add final message to session (only if session exists)
            if (
                session_id
                and hasattr(response_chunk, "choices")
                and response_chunk.choices
            ):
                last_message = response_chunk.choices[0].message
                if last_message and last_message.content:
                    # Note: We'd need session object here, but for now skip session saving in fallback mode
                    self.logger.debug(
                        f"Session {session_id} message saving skipped in fallback mode"
                    )

        except Exception as e:
            self.logger.error(f"Streaming chat processing failed: {str(e)}")
            error_response = self.streaming_service.create_error_response(str(e))
            yield self.streaming_service.format_streaming_response(error_response)

    async def _process_non_streaming_chat(
        self,
        request: ChatRequest,
        context: Dict[str, Any],
        session_id: Optional[str],
        auth_claims: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """Process non-streaming chat request but return as streaming for consistency"""
        try:
            # Process chat without streaming
            response = await self.chat_service.process_chat_simple(request, context)

            # Response already has session_state from service

            # Add final message to session (only if session exists)
            if session_id and response.choices and response.choices[0].message:
                # Note: We'd need session object here, but for now skip session saving in fallback mode
                self.logger.debug(
                    f"Session {session_id} message saving skipped in fallback mode"
                )

            # Convert ChatResponse to streaming format
            formatted_response = self.streaming_service.format_streaming_response(
                response
            )
            yield formatted_response

        except Exception as e:
            self.logger.error(f"Non-streaming chat processing failed: {str(e)}")
            error_response = self.streaming_service.create_error_response(str(e))
            yield self.streaming_service.format_streaming_response(error_response)

    async def _create_error_generator(
        self, error_message: str, session_state: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Create error response generator"""
        error_response = {
            "error": f"The app encountered an error processing your request. Error: {error_message}",
            "session_state": session_state,
        }
        yield f"data: {json.dumps(error_response)}\n\n"


# Global instance - for backward compatibility with existing routes
from app.services.session_manager import session_manager
from app.services.streaming_service import streaming_service

chat_orchestrator = ChatOrchestrator(
    chat_service=ChatService(),
    session_manager=session_manager,
    streaming_service=streaming_service,
)
