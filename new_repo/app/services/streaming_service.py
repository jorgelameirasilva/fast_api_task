"""
Streaming Response Service - Handles streaming response formatting and management
Follows Single Responsibility Principle
"""

import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from fastapi.responses import StreamingResponse

from app.models.chat import ChatDelta, ChatChoice, ChatMessage
from app.models.session import ChatSession
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


class StreamingService:
    """
    Handles streaming response logic
    Single responsibility: Format and manage streaming responses
    """

    def __init__(self):
        self.session_manager = session_manager

    def create_streaming_response(
        self, generator: AsyncGenerator, session: Optional[ChatSession] = None
    ) -> StreamingResponse:
        """
        Create FastAPI StreamingResponse from async generator

        Args:
            generator: Async generator producing chat chunks
            session: Optional session for tracking

        Returns:
            StreamingResponse for FastAPI
        """
        try:
            if session:
                # Use session-aware streaming
                stream_generator = self._format_streaming_with_session(
                    generator, session
                )
            else:
                # Use basic streaming
                stream_generator = self._format_streaming_basic(generator)

            return StreamingResponse(
                self._to_ndjson(stream_generator),
                media_type="application/json-lines",
                headers={"Cache-Control": "no-cache"},
            )

        except Exception as e:
            logger.error(f"Error creating streaming response: {str(e)}")
            raise

    async def _format_streaming_basic(
        self, result: AsyncGenerator
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Format basic streaming response without session tracking

        Args:
            result: Raw streaming result from AI service

        Yields:
            Formatted chunk dictionaries
        """
        try:
            async for chunk in result:
                if isinstance(chunk, dict) and "choices" in chunk:
                    for choice in chunk["choices"]:
                        if "delta" in choice:
                            delta_content = choice["delta"].get("content", "")
                            delta_role = choice["delta"].get("role", "assistant")

                            # Create ChatDelta
                            delta = ChatDelta(role=delta_role, content=delta_content)

                            # Create ChatChoice with delta
                            chat_choice = ChatChoice(
                                delta=delta, finish_reason=choice.get("finish_reason")
                            )

                            yield {
                                "choices": [chat_choice.model_dump()],
                                "object": "chat.completion.chunk",
                            }
                else:
                    # Fallback for other chunk formats
                    yield chunk

        except Exception as e:
            logger.error(f"Streaming response error: {str(e)}")
            yield {"error": f"Streaming error: {type(e).__name__}"}

    async def _format_streaming_with_session(
        self, result: AsyncGenerator, session: ChatSession
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Format streaming response with session tracking and message saving

        Args:
            result: Raw streaming result from AI service
            session: Session to save complete message to

        Yields:
            Formatted chunk dictionaries with session_id
        """
        try:
            complete_content = ""

            async for chunk in result:
                if isinstance(chunk, dict) and "choices" in chunk:
                    for choice in chunk["choices"]:
                        if "delta" in choice:
                            delta_content = choice["delta"].get("content", "")
                            delta_role = choice["delta"].get("role", "assistant")

                            # Accumulate complete content
                            if delta_content:
                                complete_content += delta_content

                            # Create ChatDelta
                            delta = ChatDelta(role=delta_role, content=delta_content)

                            # Create ChatChoice with delta
                            chat_choice = ChatChoice(
                                delta=delta, finish_reason=choice.get("finish_reason")
                            )

                            # Check if this is the final chunk
                            if choice.get("finish_reason") == "stop":
                                # Save complete message to session
                                await self._save_complete_message_to_session(
                                    complete_content, session
                                )

                            yield {
                                "choices": [chat_choice.model_dump()],
                                "object": "chat.completion.chunk",
                                "session_id": session.id,
                            }
                else:
                    # Fallback for other chunk formats
                    yield chunk

        except Exception as e:
            logger.error(f"Streaming with session error: {str(e)}")
            yield {
                "error": f"Streaming error: {type(e).__name__}",
                "session_id": session.id if session else None,
            }

    async def _save_complete_message_to_session(
        self, content: str, session: ChatSession
    ) -> None:
        """
        Save the complete assistant message to session

        Args:
            content: Complete message content
            session: Session to save to
        """
        try:
            if content.strip():
                assistant_message = ChatMessage(role="assistant", content=content)
                await self.session_manager.add_assistant_message_to_session(
                    session, assistant_message
                )
                logger.debug(
                    f"Saved complete streaming message to session {session.id}"
                )

        except Exception as e:
            logger.error(f"Error saving streaming message to session: {str(e)}")

    async def _to_ndjson(
        self, generator: AsyncGenerator[Dict[str, Any], None]
    ) -> AsyncGenerator[str, None]:
        """
        Convert chunk generator to NDJSON format

        Args:
            generator: Generator producing chunk dictionaries

        Yields:
            NDJSON formatted strings
        """
        try:
            async for chunk in generator:
                yield json.dumps(chunk, ensure_ascii=False) + "\n"

        except Exception as e:
            logger.error(f"NDJSON formatting error: {str(e)}")
            error_chunk = {"error": f"Response formatting error: {type(e).__name__}"}
            yield json.dumps(error_chunk, ensure_ascii=False) + "\n"

    def format_streaming_response(self, response_chunk) -> str:
        """
        Format a single response chunk to NDJSON string

        Args:
            response_chunk: Response chunk to format

        Returns:
            NDJSON formatted string
        """
        try:
            if hasattr(response_chunk, "model_dump"):
                # Pydantic model
                chunk_dict = response_chunk.model_dump()
            elif isinstance(response_chunk, dict):
                # Already a dictionary
                chunk_dict = response_chunk
            else:
                # Convert to dict representation
                chunk_dict = {"content": str(response_chunk)}

            return json.dumps(chunk_dict, ensure_ascii=False) + "\n"

        except Exception as e:
            logger.error(f"Error formatting response chunk: {str(e)}")
            error_chunk = {"error": f"Formatting error: {type(e).__name__}"}
            return json.dumps(error_chunk, ensure_ascii=False) + "\n"

    def create_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Create standardized error response

        Args:
            error_message: Error message to include

        Returns:
            Error response dictionary
        """
        return {
            "error": f"The app encountered an error processing your request. Error: {error_message}",
            "choices": [],
            "object": "chat.completion.chunk",
        }


# Global instance
streaming_service = StreamingService()
