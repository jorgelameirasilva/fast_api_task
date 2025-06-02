from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from app.schemas.chat import AskRequest, AskResponse
from app.approaches import get_best_approach, get_approach


class AskService:
    """Service focused solely on ask operations"""

    async def process_ask(
        self, request: AskRequest, stream: bool = False
    ) -> AskResponse:
        """Process an ask request using the approaches system"""
        logger.info(f"Processing ask request: {request.user_query[:50]}...")

        # Create messages and get approach
        messages = self._create_messages(request)
        approach = self._get_best_approach(request, messages)

        # Prepare context and execute
        context = self._prepare_context(request)

        try:
            result = await self._execute_approach(approach, messages, stream, context)
            return self._build_response(result, request, approach, stream)
        except Exception as e:
            logger.error(f"Error executing approach {approach.name}: {e}")
            return self._build_fallback_response(request)

    async def process_ask_with_approach(
        self, request: AskRequest, approach_name: str, stream: bool = False
    ) -> AskResponse:
        """Process an ask request with a specific approach"""
        logger.info(f"Processing ask request with approach: {approach_name}")

        # Get specific approach and create messages
        approach = get_approach(approach_name)
        messages = self._create_messages(request)

        # Prepare context with explicit approach info
        context = self._prepare_context(request)
        context["request_metadata"]["explicit_approach"] = approach_name

        # Execute approach
        result = await self._execute_approach(approach, messages, stream, context)
        response = self._build_response(result, request, approach, stream)

        # Add explicit approach info to context
        response.context["explicit_approach_requested"] = approach_name

        return response

    def _create_messages(self, request: AskRequest) -> List[Dict[str, str]]:
        """Create messages array from request"""
        messages = [{"role": "user", "content": request.user_query}]

        if request.chatbot_response:
            messages.insert(
                0, {"role": "assistant", "content": request.chatbot_response}
            )

        return messages

    def _get_best_approach(self, request: AskRequest, messages: List[Dict[str, str]]):
        """Get the best approach for the request"""
        approach = get_best_approach(
            query=request.user_query,
            context={"request": request},
            message_count=len(messages),
        )
        logger.info(f"Selected approach: {approach.name}")
        return approach

    def _prepare_context(self, request: AskRequest) -> Dict[str, Any]:
        """Prepare context for approach execution"""
        return {
            "overrides": {},
            "auth_claims": None,
            "request_metadata": {
                "count": request.count,
                "upvote": request.upvote,
                "user_query_vector": request.user_query_vector,
            },
        }

    async def _execute_approach(self, approach, messages, stream, context):
        """Execute the approach and handle streaming"""
        result = await approach.run(
            messages=messages,
            stream=stream,
            session_state=None,
            context=context,
        )

        if stream and hasattr(result, "__aiter__"):
            final_result = {}
            async for chunk in result:
                final_result.update(chunk)
            return final_result

        return result

    def _build_response(
        self, result: Dict[str, Any], request: AskRequest, approach, stream: bool
    ) -> AskResponse:
        """Build the ask response from approach result"""
        response_content = result.get("content", "No response generated")
        sources = result.get("sources", [])
        response_context = result.get("context", {})

        response_context.update(
            {
                "approach_used": approach.name,
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

    def _build_fallback_response(self, request: AskRequest) -> AskResponse:
        """Build fallback response when approach execution fails"""
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


# Create singleton instance
ask_service = AskService()
