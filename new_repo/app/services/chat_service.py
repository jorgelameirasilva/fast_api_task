"""Chat service for handling chat business logic"""

import logging
import json
from typing import Dict, Any, List, AsyncGenerator, Union, Optional
from fastapi import HTTPException

from app.core.config import settings
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatChoice,
    ChatMessage,
    ChatDelta,
    ChatContentData,
    ChatContext,
)
from app.services.cosmos_service import cosmos_session_service
from app.utils.mock_clients import (
    get_mock_search_client,
    get_mock_openai_client,
    get_mock_blob_container_client,
)

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat interactions"""

    def __init__(self):
        self.approach = None
        self._setup_approach()

    def _setup_approach(self):
        """Setup the chat approach with clients"""
        try:
            # Use mock clients for development/testing
            if settings.use_mock_clients or settings.debug:
                search_client = get_mock_search_client()
                openai_client = get_mock_openai_client()
                blob_container_client = get_mock_blob_container_client()
            else:
                # In production, you would initialize real clients here
                # This would be similar to the original app.py setup
                raise NotImplementedError(
                    "Production clients not implemented yet - use mock clients"
                )

            # Import and setup the exact same approach as original
            from app.approaches.chatreadretrieveread import ChatReadRetrieveReadApproach

            self.approach = ChatReadRetrieveReadApproach(
                search_client=search_client,
                openai_client=openai_client,
                chatgpt_model=settings.secure_gpt_deployment_id
                or settings.azure_openai_chatgpt_model
                or "gpt-4o",  # Fallback for testing
                chatgpt_deployment=settings.azure_openai_chatgpt_deployment,
                embedding_model=settings.secure_gpt_emb_deployment_id
                or settings.azure_openai_emb_model_name
                or "text-embedding-ada-002",  # Fallback for testing
                embedding_deployment=settings.azure_openai_emb_deployment,
                sourcepage_field=settings.kb_fields_sourcepage,
                content_field=settings.kb_fields_content,
                query_language=settings.azure_search_query_language,
                query_speller=settings.azure_search_query_speller,
            )

            logger.info("Chat approach initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup chat approach: {str(e)}")
            raise

    async def process_chat(
        self, request: ChatRequest, auth_claims: Dict[str, Any]
    ) -> Union[ChatResponse, AsyncGenerator[Dict[str, Any], None]]:
        """
        Process chat request and return response with session management

        This replicates the exact behavior of the original /chat endpoint
        """
        try:
            if not self.approach:
                raise HTTPException(
                    status_code=500, detail="Chat approach not initialized"
                )

            # Add auth claims to context (exactly like original)
            context = request.context.copy()
            context["auth_claims"] = auth_claims

            # Convert messages to the format expected by approaches
            messages = [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ]

            # Run the approach (exactly like original)
            result = await self.approach.run(
                messages,
                stream=request.stream,
                context=context,
                session_state=request.session_state,
            )

            # Handle response based on type (exactly like original)
            if isinstance(result, dict):
                # Non-streaming response
                return self._create_chat_response(result, request.session_state)
            else:
                # Streaming response - return the async generator
                return self._format_streaming_response(result)

        except Exception as e:
            logger.error(f"Chat processing failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"The app encountered an error processing your request. Error type: {type(e).__name__}",
            )

    async def process_chat_with_session(
        self,
        request: ChatRequest,
        auth_claims: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Union[ChatResponse, AsyncGenerator[Dict[str, Any], None]]:
        """
        Process chat request with session management

        This version loads conversation history from session and saves the new messages
        """
        try:
            user_id = auth_claims.get("preferred_username") or auth_claims.get(
                "sub", "anonymous"
            )

            # Load or create session
            session = None
            if session_id:
                session = await cosmos_session_service.get_session(session_id, user_id)
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")

            # If no session provided or found, create a new one
            if not session:
                session = await cosmos_session_service.create_session(
                    user_id=user_id, context=request.context
                )
                logger.info(f"Created new session {session.id} for user {user_id}")

            # Add new user messages to session
            for message in request.messages:
                if message.role == "user":
                    await cosmos_session_service.add_message_to_session(
                        session_id=session.id,
                        user_id=user_id,
                        message=message,
                        update_context=request.context,
                    )

            # Get updated session with full conversation history
            updated_session = await cosmos_session_service.get_session(
                session.id, user_id
            )

            # Use session messages for chat processing
            session_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in updated_session.messages
            ]

            # Add auth claims to context
            context = updated_session.context.copy()
            context.update(request.context)
            context["auth_claims"] = auth_claims

            # Run the approach with session history
            result = await self.approach.run(
                session_messages,
                stream=request.stream,
                context=context,
                session_state=session.id,
            )

            # Handle response and save assistant message
            if isinstance(result, dict):
                # Non-streaming response
                response = self._create_chat_response(result, session.id)

                # Save assistant response to session
                if response.choices and response.choices[0].message:
                    await cosmos_session_service.add_message_to_session(
                        session_id=session.id,
                        user_id=user_id,
                        message=response.choices[0].message,
                    )

                return response
            else:
                # Streaming response
                return self._format_streaming_response_with_session(
                    result, session.id, user_id
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Chat processing with session failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"The app encountered an error processing your request. Error type: {type(e).__name__}",
            )

    def _create_chat_response(
        self, result: Dict[str, Any], session_state: Any
    ) -> ChatResponse:
        """Create a ChatResponse from approach result using new model structure"""
        try:
            # Extract message content
            message_obj = result.get("message")
            if hasattr(message_obj, "content"):
                # It's a ChatCompletionMessage object
                message_content = message_obj.content
            else:
                # It's a string or other format
                message_content = str(message_obj) if message_obj else ""

            # Create the message
            message = ChatMessage(role="assistant", content=message_content)

            # Create content data
            content_data = ChatContentData(
                data_points=result.get("data_points", []),
                thoughts=result.get("thoughts", ""),
            )

            # Create choice
            choice = ChatChoice(
                message=message, content=content_data, finish_reason="stop"
            )

            # Create context
            context = ChatContext(
                overrides=result.get("context", {}),
                session_state=str(session_state) if session_state else None,
            )

            return ChatResponse(
                choices=[choice],
                session_state=str(session_state) if session_state else None,
                context=context,
            )

        except Exception as e:
            logger.error(f"Failed to create chat response: {str(e)}")
            raise

    async def _format_streaming_response(
        self, result: AsyncGenerator
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Format streaming response to match original format"""
        try:
            async for chunk in result:
                # Convert chunk to new format with ChatDelta
                if isinstance(chunk, dict) and "choices" in chunk:
                    # Process each choice in the chunk
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
            # Yield error in same format as original
            yield {
                "error": f"The app encountered an error processing your request. Error type: {type(e).__name__}"
            }

    async def _format_streaming_response_with_session(
        self, result: AsyncGenerator, session_id: str, user_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Format streaming response and save complete message to session"""
        try:
            complete_content = ""
            async for chunk in result:
                # Convert chunk to new format with ChatDelta
                if isinstance(chunk, dict) and "choices" in chunk:
                    # Process each choice in the chunk
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
                                if complete_content:
                                    assistant_message = ChatMessage(
                                        role="assistant", content=complete_content
                                    )
                                    await cosmos_session_service.add_message_to_session(
                                        session_id=session_id,
                                        user_id=user_id,
                                        message=assistant_message,
                                    )

                            yield {
                                "choices": [chat_choice.model_dump()],
                                "object": "chat.completion.chunk",
                                "session_id": session_id,
                            }
                else:
                    # Fallback for other chunk formats
                    yield chunk

        except Exception as e:
            logger.error(f"Streaming response with session error: {str(e)}")
            # Yield error in same format as original
            yield {
                "error": f"The app encountered an error processing your request. Error type: {type(e).__name__}"
            }
