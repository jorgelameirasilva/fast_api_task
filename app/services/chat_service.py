from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    AskRequest,
    AskResponse,
    VoteRequest,
    VoteResponse,
    AuthSetupResponse,
)
from app.core.config import settings
from app.approaches import get_best_approach, get_approach, list_available_approaches


class ChatService:
    """Service for handling chat operations"""

    def __init__(self):
        self.session_storage: Dict[str, Any] = {}
        self.vote_storage: List[Dict[str, Any]] = []

    async def process_chat(
        self, request: ChatRequest, approach_name: str = None, stream: bool = False
    ) -> ChatResponse:
        """
        Process a chat request using the approaches system
        """
        logger.info(f"Processing chat with {len(request.messages)} messages")

        # Validate we have user messages
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise ValueError("No user message found in chat request")

        # Convert ChatMessage objects to dict format for approaches
        messages = []
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        # Get the last user message for approach selection
        last_user_message = user_messages[-1]

        # Determine the best approach or use specified one
        if approach_name:
            logger.info(f"Using explicit approach for chat: {approach_name}")
            approach = get_approach(approach_name)
        else:
            approach = get_best_approach(
                query=last_user_message.content,
                context={"request": request},
                message_count=len(messages),
            )
            logger.info(f"Selected approach for chat: {approach.name}")

        # Prepare context for the approach
        approach_context = {
            "overrides": request.context or {},
            "auth_claims": None,  # Can be populated from authentication
            "request_metadata": {
                "session_state": request.session_state,
                "message_count": len(messages),
                "chat_context": True,
            },
        }

        # Execute the approach
        try:
            result = await approach.run(
                messages=messages,
                stream=stream,
                session_state=request.session_state,
                context=approach_context,
            )

            # Handle streaming vs non-streaming responses
            if stream and hasattr(result, "__aiter__"):
                # For streaming, collect final result
                final_result = {}
                async for chunk in result:
                    final_result.update(chunk)
                result = final_result

            # Extract response components
            response_content = result.get("content", "No response generated")
            sources = result.get("sources", [])
            response_context = result.get("context", {})

            # Create response message
            response_message = ChatMessage(
                role="assistant", content=response_content, timestamp=datetime.now()
            )

            # Update session state if provided
            session_state = request.session_state
            if session_state:
                self.session_storage[session_state] = {
                    "last_interaction": datetime.now(),
                    "message_count": len(request.messages) + 1,
                    "approach_used": approach.name,
                }

            # Enhance context with chat-specific information
            enhanced_context = {
                **(request.context or {}),
                **response_context,
                "approach_used": approach.name,
                "streaming": stream,
                "sources_count": len(sources),
                "session_updated": session_state is not None,
                "chat_processed_at": datetime.now().isoformat(),
            }

            return ChatResponse(
                message=response_message,
                session_state=session_state,
                context=enhanced_context,
            )

        except Exception as e:
            logger.error(f"Error executing approach {approach.name} for chat: {e}")
            # Fallback to simple response
            return await self._fallback_chat_response(request)

    async def _fallback_chat_response(self, request: ChatRequest) -> ChatResponse:
        """
        Fallback response when approach execution fails for chat
        """
        logger.warning("Using fallback response for chat request")

        # Get the last user message for context
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        last_user_message = user_messages[-1] if user_messages else None
        user_content = (
            last_user_message.content if last_user_message else "your message"
        )

        fallback_content = (
            f"I apologize, but I encountered an issue while processing your message. "
            f"Please try rephrasing your question or contact support for assistance."
        )

        response_message = ChatMessage(
            role="assistant", content=fallback_content, timestamp=datetime.now()
        )

        return ChatResponse(
            message=response_message,
            session_state=request.session_state,
            context={
                "error": "chat_approach_execution_failed",
                "fallback_used": True,
                "chat_processed_at": datetime.now().isoformat(),
            },
        )

    async def process_ask(
        self, request: AskRequest, stream: bool = False
    ) -> AskResponse:
        """
        Process an ask request using the approaches system
        """
        logger.info(f"Processing ask request: {request.user_query[:50]}...")

        # Create messages array from the request
        messages = [{"role": "user", "content": request.user_query}]

        # Add previous chatbot response if available for context
        if request.chatbot_response:
            messages.insert(
                0, {"role": "assistant", "content": request.chatbot_response}
            )

        # Determine the best approach for this request
        approach = get_best_approach(
            query=request.user_query,
            context={"request": request},
            message_count=len(messages),
        )

        logger.info(f"Selected approach: {approach.name}")

        # Prepare context for the approach
        approach_context = {
            "overrides": {},  # Can be extended with request parameters
            "auth_claims": None,  # Can be populated from authentication
            "request_metadata": {
                "count": request.count,
                "upvote": request.upvote,
                "user_query_vector": request.user_query_vector,
            },
        }

        # Execute the approach
        try:
            result = await approach.run(
                messages=messages,
                stream=stream,  # Now uses the streaming parameter
                session_state=None,  # Can be populated from request
                context=approach_context,
            )

            # Handle streaming vs non-streaming responses
            if stream and hasattr(result, "__aiter__"):
                # For streaming, collect final result
                final_result = {}
                async for chunk in result:
                    final_result.update(chunk)
                result = final_result

            # Extract response components
            response_content = result.get("content", "No response generated")
            sources = result.get("sources", [])
            response_context = result.get("context", {})

            # Add approach information to context
            response_context.update(
                {
                    "approach_used": approach.name,
                    "streaming": stream,  # Add streaming info to context
                    "query_processed_at": datetime.now().isoformat(),
                }
            )

            return AskResponse(
                user_query=request.user_query,
                chatbot_response=response_content,
                context=response_context,
                sources=sources,
                count=request.count or 0,
            )

        except Exception as e:
            logger.error(f"Error executing approach {approach.name}: {e}")
            # Fallback to simple response
            return await self._fallback_ask_response(request)

    async def _fallback_ask_response(self, request: AskRequest) -> AskResponse:
        """
        Fallback response when approach execution fails
        """
        logger.warning("Using fallback response for ask request")

        fallback_response = (
            f"I apologize, but I encountered an issue while processing your query: "
            f"'{request.user_query}'. Please try rephrasing your question or contact support."
        )

        return AskResponse(
            user_query=request.user_query,
            chatbot_response=fallback_response,
            context={
                "error": "approach_execution_failed",
                "fallback_used": True,
                "query_processed_at": datetime.now().isoformat(),
            },
            sources=[],
            count=request.count or 0,
        )

    async def process_ask_with_approach(
        self, request: AskRequest, approach_name: str, stream: bool = False
    ) -> AskResponse:
        """
        Process an ask request with a specific approach

        Args:
            request: The ask request
            approach_name: Name of the approach to use
            stream: Whether to stream the response

        Returns:
            AskResponse with the generated response
        """
        logger.info(f"Processing ask request with approach: {approach_name}")

        # Get the specified approach
        approach = get_approach(approach_name)

        # Create messages array
        messages = [{"role": "user", "content": request.user_query}]
        if request.chatbot_response:
            messages.insert(
                0, {"role": "assistant", "content": request.chatbot_response}
            )

        # Prepare context
        approach_context = {
            "overrides": {},
            "auth_claims": None,
            "request_metadata": {
                "count": request.count,
                "upvote": request.upvote,
                "user_query_vector": request.user_query_vector,
                "explicit_approach": approach_name,
            },
        }

        # Execute approach
        result = await approach.run(
            messages=messages,
            stream=stream,
            session_state=None,
            context=approach_context,
        )

        # Handle streaming vs non-streaming responses
        if stream and hasattr(result, "__aiter__"):
            # For streaming, collect final result
            final_result = {}
            async for chunk in result:
                final_result.update(chunk)
            result = final_result

        # Extract response components
        response_content = result.get("content", "No response generated")
        sources = result.get("sources", [])
        response_context = result.get("context", {})

        response_context.update(
            {
                "approach_used": approach.name,
                "explicit_approach_requested": approach_name,
                "streaming": stream,
                "query_processed_at": datetime.now().isoformat(),
            }
        )

        return AskResponse(
            user_query=request.user_query,
            chatbot_response=response_content,
            context=response_context,
            sources=sources,
            count=request.count or 0,
        )

    async def process_vote(self, request: VoteRequest) -> VoteResponse:
        """
        Process a vote/feedback request with enhanced validation
        """
        logger.info(f"Processing vote: upvote={request.upvote}, count={request.count}")

        # Validate vote consistency
        if request.downvote is not None and request.upvote == request.downvote:
            raise ValueError("Vote cannot be both upvote and downvote")

        # Store the vote with all available fields
        vote_record = {
            "user_query": request.user_query,
            "chatbot_response": request.chatbot_response,
            "upvote": request.upvote,
            "downvote": request.downvote,
            "count": request.count,
            "reason_multiple_choice": request.reason_multiple_choice,
            "additional_comments": request.additional_comments,
            "date": request.date,
            "time": request.time,
            "email_address": request.email_address,
            "timestamp": datetime.now().isoformat(),
        }

        self.vote_storage.append(vote_record)

        # Determine if this is primarily an upvote or downvote
        is_upvote = request.upvote if request.downvote is None else not request.downvote

        return VoteResponse(
            status="success",
            message="Vote recorded successfully",
            upvote=is_upvote,
            count=request.count,
        )

    async def get_auth_setup(self) -> AuthSetupResponse:
        """
        Get authentication setup configuration
        """
        logger.info("Getting auth setup configuration")

        return AuthSetupResponse(
            auth_enabled=settings.AUTH_ENABLED,
            auth_type="none" if not settings.AUTH_ENABLED else "azure_ad",
            login_url="/login" if settings.AUTH_ENABLED else None,
            logout_url="/logout" if settings.AUTH_ENABLED else None,
        )

    async def _generate_chat_response(
        self, user_message: str, context: Dict[str, Any]
    ) -> str:
        """
        Generate a chat response (placeholder implementation)
        """
        # This is where you would integrate with Azure OpenAI or other LLM services
        logger.debug(f"Generating response for: {user_message[:30]}...")

        # Placeholder response
        return f"Thank you for your message: '{user_message}'. This is a placeholder response from the chat service."

    async def _generate_ask_response(self, query: str) -> str:
        """
        Generate an ask response (placeholder implementation)
        """
        # This is where you would integrate with Azure OpenAI and search services
        logger.debug(f"Generating ask response for: {query[:30]}...")

        # Placeholder response
        return f"Based on your query '{query}', here is a comprehensive response. This is a placeholder implementation."

    async def _get_relevant_sources(self, query: str) -> List[Dict[str, Any]]:
        """
        Get relevant sources for a query (placeholder implementation)
        """
        # This is where you would integrate with Azure Search or other search services
        logger.debug(f"Getting sources for: {query[:30]}...")

        # Placeholder sources
        return [
            {
                "title": "Sample Document 1",
                "url": "/content/sample1.pdf",
                "relevance_score": 0.95,
                "excerpt": "This is a sample excerpt from document 1...",
            },
            {
                "title": "Sample Document 2",
                "url": "/content/sample2.pdf",
                "relevance_score": 0.87,
                "excerpt": "This is a sample excerpt from document 2...",
            },
        ]


# Create a singleton instance
chat_service = ChatService()
