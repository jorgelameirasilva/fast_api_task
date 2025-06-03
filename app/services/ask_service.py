from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from app.schemas.chat import AskRequest, AskResponse
from app.services.response_generator import ResponseGenerator


class AskService:
    """Service focused solely on ask operations"""

    def __init__(self, response_generator: ResponseGenerator = None):
        self.response_generator = response_generator or ResponseGenerator()

    async def process_ask(
        self, request: AskRequest, stream: bool = False
    ) -> AskResponse:
        """Process an ask request using approaches as primary method"""
        logger.info(f"Processing ask request: {request.user_query[:50]}...")

        try:
            # Primary: Use approaches (matching old code structure)
            return await self._process_with_approaches(request, stream)

        except Exception as e:
            logger.error(f"Approach processing failed: {e}")
            # Only fallback to simple processing if approaches completely fail
            logger.warning("Falling back to simple processing due to approach failure")
            return await self._process_simple(request, stream)

    async def _process_with_approaches(
        self, request: AskRequest, stream: bool
    ) -> AskResponse:
        """Process ask using the approach system - primary method"""
        logger.info("Using approach system for ask processing")

        try:
            from app.core.setup import get_ask_approach

            ask_approach = get_ask_approach()
            if not ask_approach:
                raise ValueError("No ask approach configured")

            # Convert request to messages format expected by approaches
            messages = [{"role": "user", "content": request.user_query}]

            # Prepare context for approach - match old code structure
            overrides = {}
            auth_claims = {}

            # Run the approach based on streaming preference
            if stream:
                # For now, treat streaming the same as non-streaming for response structure
                # The streaming functionality can be enhanced later for actual streaming responses
                approach_result = await ask_approach.run_without_streaming(
                    messages=messages,
                    overrides=overrides,
                    auth_claims=auth_claims,
                    session_state=None,
                )
            else:
                approach_result = await ask_approach.run_without_streaming(
                    messages=messages,
                    overrides=overrides,
                    auth_claims=auth_claims,
                    session_state=None,
                )

            # Convert approach result to AskResponse
            if isinstance(approach_result, dict) and "choices" in approach_result:
                choice = approach_result["choices"][0]
                message_content = choice["message"]["content"]
                message_context = choice["message"].get("context", {})

                # Extract sources from context
                sources = []
                if "data_points" in message_context:
                    for i, data_point in enumerate(message_context["data_points"]):
                        sources.append(
                            {
                                "title": f"Retrieved Document {i+1}",
                                "url": f"/content/doc{i+1}.pdf",
                                "relevance_score": 0.9 - (i * 0.1),
                                "excerpt": (
                                    data_point[:100] + "..."
                                    if len(data_point) > 100
                                    else data_point
                                ),
                            }
                        )

                # Build response context - include approach details
                response_context = {
                    "approach_used": "retrieve_then_read",
                    "approach_type": ask_approach.__class__.__name__,
                    "streaming": stream,
                    "query_processed_at": datetime.now().isoformat(),
                    **message_context,
                }

                return AskResponse(
                    user_query=request.user_query,
                    chatbot_response=message_content,
                    context=response_context,
                    sources=sources,
                    count=request.count or 0,
                )

            else:
                raise ValueError("Invalid approach result format")

        except Exception as e:
            logger.error(f"Approach processing failed: {e}")
            raise

    async def _process_simple(self, request: AskRequest, stream: bool) -> AskResponse:
        """Process ask using simple response generation - fallback only"""
        logger.warning("Using simple response generation for ask processing (fallback)")

        # Generate response using the response generator
        response_content = await self.response_generator.generate_ask_response(
            request.user_query
        )

        # Get relevant sources
        sources = await self.response_generator.get_relevant_sources(request.user_query)

        # Build response context
        response_context = {
            "approach_used": "simple_fallback",
            "streaming": stream,
            "query_processed_at": datetime.now().isoformat(),
            "fallback_reason": "approach_processing_failed",
        }

        return AskResponse(
            user_query=request.user_query,
            chatbot_response=response_content,
            context=response_context,
            sources=sources,
            count=request.count or 0,
        )


# Create service instance
ask_service = AskService()
