"""
Query Processing Service
Handles query understanding, enhancement, and search execution
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.repositories.search_repository import (
    SearchRepository,
    SearchQuery,
    SearchResult,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessedQuery:
    """Processed query result"""

    original_query: str
    enhanced_query: str
    search_results: List[SearchResult]
    metadata: Dict[str, Any]


class QueryProcessingService:
    """Domain service for query processing and search execution"""

    def __init__(self, search_repository: SearchRepository):
        self.search_repository = search_repository
        logger.info("Initialized QueryProcessingService")

    async def process_query(
        self, query: str, context: Optional[Dict[str, Any]] = None, max_results: int = 5
    ) -> ProcessedQuery:
        """
        Process user query: enhance, search, and return structured results
        """
        logger.info(f"Processing query: {query[:50]}...")

        try:
            # Step 1: Enhance the query
            enhanced_query = await self._enhance_query(query, context)

            # Step 2: Execute search
            search_query = SearchQuery(
                text=enhanced_query, top_k=max_results, semantic_search=True
            )

            search_results = await self.search_repository.search(search_query)

            # Step 3: Post-process results
            processed_results = await self._post_process_results(search_results, query)

            return ProcessedQuery(
                original_query=query,
                enhanced_query=enhanced_query,
                search_results=processed_results,
                metadata={
                    "results_count": len(processed_results),
                    "enhancement_applied": enhanced_query != query,
                    "context_used": context is not None,
                },
            )

        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise

    async def _enhance_query(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Enhance user query with context and domain knowledge
        """
        enhanced = query.strip()

        # Add context-based enhancements
        if context:
            if "user_role" in context:
                enhanced = f"[{context['user_role']}] {enhanced}"

            if "domain" in context:
                enhanced = f"{enhanced} (domain: {context['domain']})"

        # Add domain-specific query expansion
        enhanced = await self._expand_technical_terms(enhanced)

        logger.debug(f"Enhanced query: {query} -> {enhanced}")
        return enhanced

    async def _expand_technical_terms(self, query: str) -> str:
        """
        Expand technical terms and acronyms for better search
        """
        expansions = {
            "api": "API application programming interface",
            "ml": "machine learning ML",
            "ai": "artificial intelligence AI",
            "db": "database DB",
            "auth": "authentication authorization",
            "crud": "create read update delete CRUD",
        }

        query_lower = query.lower()
        for term, expansion in expansions.items():
            if term in query_lower:
                query = query.replace(term, expansion)

        return query

    async def _post_process_results(
        self, results: List[SearchResult], original_query: str
    ) -> List[SearchResult]:
        """
        Post-process search results for relevance and formatting
        """
        if not results:
            return results

        # Filter by minimum relevance score
        filtered_results = [r for r in results if r.score >= 0.3]

        # Sort by score (highest first)
        sorted_results = sorted(filtered_results, key=lambda x: x.score, reverse=True)

        # Enhance metadata
        for result in sorted_results:
            result.metadata.update(
                {
                    "relevance_tier": self._get_relevance_tier(result.score),
                    "query_terms_matched": self._count_query_matches(
                        result.content, original_query
                    ),
                }
            )

        return sorted_results

    def _get_relevance_tier(self, score: float) -> str:
        """Categorize relevance score into tiers"""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        else:
            return "low"

    def _count_query_matches(self, content: str, query: str) -> int:
        """Count how many query terms appear in content"""
        query_terms = query.lower().split()
        content_lower = content.lower()
        return sum(1 for term in query_terms if term in content_lower)

    async def health_check(self) -> Dict[str, str]:
        """Check service health"""
        try:
            search_health = await self.search_repository.health_check()
            return {
                "service": "QueryProcessingService",
                "status": "healthy",
                "search_repository": search_health.get("status", "unknown"),
            }
        except Exception as e:
            return {
                "service": "QueryProcessingService",
                "status": "unhealthy",
                "error": str(e),
            }
