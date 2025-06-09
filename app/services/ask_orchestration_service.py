"""
Ask Orchestration Service - Business Logic Layer.
This service orchestrates the ask workflow using domain services.
"""

from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from app.schemas.chat import AskRequest, AskResponse
from app.services.query_processing_service import QueryProcessingService
from app.services.response_generation_service import ResponseGenerationService
from app.repositories.search_repository import SearchQuery


class AskOrchestrationService:
    """
    Orchestrates the ask workflow:
    1. Process user query
    2. Search for relevant documents
    3. Generate contextual response
    4. Format final response
    """

    def __init__(
        self,
        query_processor: QueryProcessingService,
        response_generator: ResponseGenerationService,
    ):
        self.query_processor = query_processor
        self.response_generator = response_generator

    async def process_ask_request(
        self, request: AskRequest, stream: bool = False
    ) -> AskResponse:
        """
        Main orchestration method for ask requests.
        Follows the Retrieve-Then-Read pattern with proper error handling.
        """
        logger.info(f"Processing ask request: {request.user_query[:50]}...")

        try:
            # Step 1: Process and analyze the user query
            processed_query = await self.query_processor.process_user_query(
                request.user_query, context={"request_type": "ask"}
            )
            logger.debug(f"Processed query: {processed_query.query}")

            # Step 2: Search for relevant documents
            search_results = await self.query_processor.search_documents(
                processed_query
            )
            logger.info(f"Found {len(search_results)} relevant documents")

            # Step 3: Generate response using retrieved context
            response_content = (
                await self.response_generator.generate_contextual_response(
                    user_query=request.user_query,
                    search_results=search_results,
                    response_type="ask",
                    stream=stream,
                )
            )

            # Step 4: Format sources for response
            sources = self._format_sources(search_results)

            # Step 5: Build response context
            response_context = {
                "approach": "retrieve_then_read",
                "documents_found": len(search_results),
                "query_processed_at": datetime.now().isoformat(),
                "streaming": stream,
                "search_query": processed_query.query,
                "filters_applied": processed_query.filters,
            }

            return AskResponse(
                user_query=request.user_query,
                chatbot_response=response_content,
                context=response_context,
                sources=sources,
                count=request.count or 0,
            )

        except Exception as e:
            logger.error(f"Error processing ask request: {e}")
            # Return error response instead of raising
            return self._create_error_response(request, str(e))

    def _format_sources(self, search_results: List[Any]) -> List[Dict[str, Any]]:
        """Format search results into sources for the response"""
        sources = []

        for i, result in enumerate(search_results[:5]):  # Limit to top 5 sources
            sources.append(
                {
                    "title": getattr(result, "title", f"Document {i+1}"),
                    "url": self._generate_source_url(result),
                    "relevance_score": getattr(result, "relevance_score", 0.0),
                    "excerpt": self._create_excerpt(
                        getattr(result, "content", ""), max_length=150
                    ),
                    "source": getattr(result, "source", "unknown"),
                }
            )

        return sources

    def _generate_source_url(self, result: Any) -> str:
        """Generate a URL for the source document"""
        source = getattr(result, "source", "unknown")
        # This could be enhanced to generate proper URLs based on document storage
        return f"/documents/{source}" if source != "unknown" else "/documents/unknown"

    def _create_excerpt(self, content: str, max_length: int = 150) -> str:
        """Create a brief excerpt from document content"""
        if len(content) <= max_length:
            return content

        # Find a good breaking point near the max length
        excerpt = content[:max_length]
        last_space = excerpt.rfind(" ")

        if last_space > max_length * 0.8:  # If we find a space in the last 20%
            excerpt = excerpt[:last_space]

        return excerpt + "..."

    def _create_error_response(
        self, request: AskRequest, error_msg: str
    ) -> AskResponse:
        """Create an error response when processing fails"""
        error_context = {
            "error": True,
            "error_message": error_msg,
            "approach": "error_fallback",
            "processed_at": datetime.now().isoformat(),
        }

        error_response = (
            "I apologize, but I encountered an issue while processing your request. "
            "Please try rephrasing your question or contact support if the problem persists."
        )

        return AskResponse(
            user_query=request.user_query,
            chatbot_response=error_response,
            context=error_context,
            sources=[],
            count=request.count or 0,
        )
