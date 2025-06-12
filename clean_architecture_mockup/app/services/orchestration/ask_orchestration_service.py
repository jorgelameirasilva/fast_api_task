"""
Ask Orchestration Service
Coordinates the complete ask workflow: query processing + response generation
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.domain.query_processing_service import QueryProcessingService
from app.services.domain.response_generation_service import ResponseGenerationService

logger = logging.getLogger(__name__)


class AskOrchestrationService:
    """Application service that orchestrates the complete ask workflow"""

    def __init__(
        self,
        query_processing_service: QueryProcessingService,
        response_generation_service: ResponseGenerationService,
    ):
        self.query_processing_service = query_processing_service
        self.response_generation_service = response_generation_service
        logger.info("Initialized AskOrchestrationService")

    async def process_ask(
        self, query: str, context: Optional[Dict[str, Any]] = None, max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Complete ask workflow orchestration

        Steps:
        1. Process and enhance the query
        2. Execute search with enhanced query
        3. Generate LLM response using search results
        4. Return structured response with metadata
        """
        start_time = datetime.now()
        logger.info(f"Processing ask request: {query[:50]}...")

        try:
            # Step 1: Process query and get search results
            processed_query = await self.query_processing_service.process_query(
                query=query, context=context, max_results=max_results
            )

            logger.info(f"Found {len(processed_query.search_results)} search results")

            # Step 2: Generate response using search results
            generated_response = (
                await self.response_generation_service.generate_response(
                    query=query,
                    search_results=processed_query.search_results,
                    context=context,
                )
            )

            # Step 3: Calculate total processing time
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Step 4: Build structured response
            response = {
                "answer": generated_response.content,
                "sources": self._format_sources(processed_query.search_results),
                "confidence": generated_response.confidence,
                "processing_time_ms": processing_time,
                "metadata": {
                    "original_query": processed_query.original_query,
                    "enhanced_query": processed_query.enhanced_query,
                    "search_metadata": processed_query.metadata,
                    "response_metadata": {
                        "model": generated_response.model_info.get("model"),
                        "tokens_used": generated_response.model_info.get("tokens_used"),
                        "sources_used": len(generated_response.sources_used),
                    },
                },
            }

            logger.info(f"Ask request completed in {processing_time}ms")
            return response

        except Exception as e:
            logger.error(f"Ask orchestration failed: {e}")
            # Return error response
            return {
                "answer": "I apologize, but I encountered an error while processing your request. Please try again.",
                "sources": [],
                "confidence": 0.0,
                "processing_time_ms": int(
                    (datetime.now() - start_time).total_seconds() * 1000
                ),
                "error": str(e),
            }

    def _format_sources(self, search_results) -> list:
        """Format search results for API response"""
        formatted_sources = []

        for i, result in enumerate(search_results, 1):
            formatted_sources.append(
                {
                    "id": i,
                    "content": result.content,
                    "score": result.score,
                    "source": result.source,
                    "metadata": result.metadata,
                    "relevance_tier": result.metadata.get("relevance_tier", "unknown"),
                }
            )

        return formatted_sources

    async def health_check(self) -> Dict[str, str]:
        """Check orchestration service health"""
        try:
            # Check all dependent services
            query_health = await self.query_processing_service.health_check()
            response_health = await self.response_generation_service.health_check()

            # Determine overall health
            overall_status = "healthy"
            if (
                query_health.get("status") != "healthy"
                or response_health.get("status") != "healthy"
            ):
                overall_status = "degraded"

            return {
                "service": "AskOrchestrationService",
                "status": overall_status,
                "dependencies": {
                    "query_processing": query_health.get("status", "unknown"),
                    "response_generation": response_health.get("status", "unknown"),
                },
            }

        except Exception as e:
            return {
                "service": "AskOrchestrationService",
                "status": "unhealthy",
                "error": str(e),
            }
