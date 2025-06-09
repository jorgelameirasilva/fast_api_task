"""
Chat Orchestration Service - Business Logic Layer.
This service orchestrates the chat workflow using domain services.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger

from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage
from app.services.query_processing_service import QueryProcessingService
from app.services.response_generation_service import ResponseGenerationService


class ChatOrchestrationService:
    """
    Orchestrates the chat workflow:
    1. Process conversation context
    2. Extract current user query
    3. Search for relevant documents
    4. Generate contextual response with conversation history
    5. Format final response
    """

    def __init__(
        self,
        query_processor: QueryProcessingService,
        response_generator: ResponseGenerationService,
    ):
        self.query_processor = query_processor
        self.response_generator = response_generator

    async def process_chat_request(
        self, request: ChatRequest, stream: bool = False
    ) -> ChatResponse:
        """
        Main orchestration method for chat requests.
        Follows the Chat-Read-Retrieve-Read pattern with conversation context.
        """
        logger.info(f"Processing chat request with {len(request.messages)} messages")

        try:
            # Step 1: Extract the latest user message
            user_messages = [msg for msg in request.messages if msg.role == "user"]
            if not user_messages:
                raise ValueError("No user message found in chat request")

            latest_user_message = user_messages[-1].content
            logger.debug(f"Latest user message: {latest_user_message[:50]}...")

            # Step 2: Process and analyze the user query with conversation context
            conversation_context = self._build_conversation_context(request.messages)
            processed_query = await self.query_processor.process_user_query(
                latest_user_message,
                context={
                    "request_type": "chat",
                    "conversation_context": conversation_context,
                },
            )
            logger.debug(f"Processed query: {processed_query.query}")

            # Step 3: Search for relevant documents
            search_results = await self.query_processor.search_documents(
                processed_query
            )
            logger.info(f"Found {len(search_results)} relevant documents")

            # Step 4: Generate response using retrieved context and conversation history
            conversation_history = self._format_conversation_history(request.messages)
            response_content = (
                await self.response_generator.generate_contextual_response(
                    user_query=latest_user_message,
                    search_results=search_results,
                    response_type="chat",
                    stream=stream,
                    conversation_history=conversation_history,
                )
            )

            # Step 5: Create response message
            response_message = ChatMessage(
                role="assistant", content=response_content, timestamp=datetime.now()
            )

            # Step 6: Build response context
            response_context = {
                **(request.context or {}),
                "approach": "chat_read_retrieve_read",
                "documents_found": len(search_results),
                "conversation_length": len(request.messages),
                "query_processed_at": datetime.now().isoformat(),
                "streaming": stream,
                "search_query": processed_query.query,
                "filters_applied": processed_query.filters,
            }

            return ChatResponse(
                message=response_message,
                session_state=request.session_state,
                context=response_context,
            )

        except Exception as e:
            logger.error(f"Error processing chat request: {e}")
            # Return error response instead of raising
            return self._create_error_response(request, str(e))

    def _build_conversation_context(self, messages: List[ChatMessage]) -> str:
        """
        Build a context summary from the conversation history.
        This helps with query enhancement and understanding user intent.
        """
        if len(messages) <= 1:
            return "No previous conversation context."

        # Take the last few messages for context (excluding the current one)
        context_messages = messages[-6:-1]  # Last 5 messages before current

        context_parts = []
        for msg in context_messages:
            context_parts.append(f"{msg.role.title()}: {msg.content[:100]}")

        return "\n".join(context_parts)

    def _format_conversation_history(
        self, messages: List[ChatMessage]
    ) -> List[Dict[str, str]]:
        """
        Format conversation history for the response generator.
        """
        history = []
        for msg in messages[:-1]:  # Exclude the current message
            history.append({"role": msg.role, "content": msg.content})
        return history

    def _create_error_response(
        self, request: ChatRequest, error_msg: str
    ) -> ChatResponse:
        """Create an error response when processing fails"""
        error_context = {
            **(request.context or {}),
            "error": True,
            "error_message": error_msg,
            "approach": "error_fallback",
            "processed_at": datetime.now().isoformat(),
        }

        error_response = (
            "I apologize, but I encountered an issue while processing your message. "
            "Could you please rephrase your question or try again? If the problem "
            "persists, please contact support."
        )

        error_message = ChatMessage(
            role="assistant", content=error_response, timestamp=datetime.now()
        )

        return ChatResponse(
            message=error_message,
            session_state=request.session_state,
            context=error_context,
        )
