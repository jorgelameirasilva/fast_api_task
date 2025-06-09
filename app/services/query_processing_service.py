"""
Query Processing Service - Domain Service Layer.
Handles query analysis, enhancement, and document retrieval.
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from app.repositories.search_repository import (
    SearchRepository,
    SearchQuery,
    SearchResult,
)
from app.repositories.llm_repository import LLMRepository, LLMMessage, LLMRequest


class QueryProcessingService:
    """
    Service responsible for processing user queries and retrieving relevant documents.
    This includes query enhancement, search execution, and result filtering.
    """

    def __init__(
        self, search_repository: SearchRepository, llm_repository: LLMRepository
    ):
        self.search_repository = search_repository
        self.llm_repository = llm_repository

    async def process_user_query(
        self, user_query: str, context: Optional[Dict[str, Any]] = None
    ) -> SearchQuery:
        """
        Process and enhance user query for better search results.

        Args:
            user_query: Raw user input
            context: Additional context about the request

        Returns:
            SearchQuery object ready for search execution
        """
        logger.info(f"Processing query: {user_query[:50]}...")

        context = context or {}
        request_type = context.get("request_type", "ask")

        try:
            # Enhance query using LLM if needed
            enhanced_query = await self._enhance_query(user_query, context)

            # Extract search parameters
            search_params = self._extract_search_parameters(user_query, context)

            # Build search query
            search_query = SearchQuery(
                query=enhanced_query,
                top_k=search_params.get("top_k", 5),
                filters=search_params.get("filters", {}),
                use_semantic_search=search_params.get("use_semantic_search", True),
                use_vector_search=search_params.get("use_vector_search", True),
            )

            logger.debug(f"Created search query: {search_query.query}")
            return search_query

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            # Return basic query as fallback
            return SearchQuery(query=user_query, top_k=5)

    async def search_documents(self, search_query: SearchQuery) -> List[SearchResult]:
        """
        Execute document search using the search repository.

        Args:
            search_query: Processed search query

        Returns:
            List of relevant search results
        """
        logger.info(f"Searching documents for: {search_query.query[:50]}...")

        try:
            # Execute search
            results = await self.search_repository.search(search_query)

            # Post-process results if needed
            filtered_results = self._filter_results(results, search_query)

            logger.info(f"Retrieved {len(filtered_results)} documents")
            return filtered_results

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []

    async def _enhance_query(self, user_query: str, context: Dict[str, Any]) -> str:
        """
        Use LLM to enhance user query for better search results.

        This is particularly useful for:
        - Expanding abbreviations
        - Adding context from conversation history
        - Reformulating questions for better search
        """
        try:
            # Simple enhancement for now - could be made more sophisticated
            if len(user_query.split()) < 3:
                # Short queries might benefit from expansion
                enhancement_prompt = (
                    "Enhance this query to make it more specific for searching employee handbook "
                    "and healthcare benefits documentation. Keep it concise but add relevant keywords.\n\n"
                    f"Original query: {user_query}\n"
                    "Enhanced query:"
                )

                messages = [LLMMessage(role="user", content=enhancement_prompt)]
                request = LLMRequest(messages=messages, temperature=0.3, max_tokens=50)

                response = await self.llm_repository.generate_response(request)
                enhanced = response.content.strip()

                # Use enhanced query if it seems reasonable
                if enhanced and len(enhanced) > len(user_query) and len(enhanced) < 200:
                    logger.debug(f"Enhanced query: {user_query} -> {enhanced}")
                    return enhanced

            return user_query

        except Exception as e:
            logger.warning(f"Query enhancement failed, using original: {e}")
            return user_query

    def _extract_search_parameters(
        self, user_query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract search parameters from query and context.

        This could analyze the query to determine:
        - How many results to return
        - What filters to apply
        - Search modes to use
        """
        params = {
            "top_k": 5,  # Default
            "filters": {},
            "use_semantic_search": True,
            "use_vector_search": True,
        }

        # Adjust based on query characteristics
        query_lower = user_query.lower()

        # If query asks for specific information, might need more results
        if any(word in query_lower for word in ["all", "every", "list", "everything"]):
            params["top_k"] = 10

        # If query is very specific, fewer results might be better
        if len(user_query.split()) > 10:
            params["top_k"] = 3

        # Add filters based on context
        request_type = context.get("request_type")
        if request_type:
            params["filters"]["request_type"] = request_type

        return params

    def _filter_results(
        self, results: List[SearchResult], search_query: SearchQuery
    ) -> List[SearchResult]:
        """
        Post-process search results to improve quality.

        This could include:
        - Removing duplicates
        - Filtering by relevance threshold
        - Reranking based on additional criteria
        """
        if not results:
            return results

        # Filter by minimum relevance score
        min_score = 0.1  # Adjust based on your needs
        filtered = [r for r in results if r.relevance_score >= min_score]

        # Remove near-duplicates based on content similarity
        unique_results = self._remove_similar_documents(filtered)

        # Sort by relevance score
        unique_results.sort(key=lambda x: x.relevance_score, reverse=True)

        return unique_results

    def _remove_similar_documents(
        self, results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Remove documents that are too similar to each other.
        This is a simple implementation - could be enhanced with proper similarity metrics.
        """
        if len(results) <= 1:
            return results

        unique_results = []
        seen_content = set()

        for result in results:
            # Create a signature of the content for comparison
            content_words = set(result.content.lower().split()[:20])  # First 20 words

            # Check if this content is too similar to what we've seen
            is_similar = False
            for seen_words in seen_content:
                overlap = len(content_words.intersection(seen_words))
                if overlap > len(content_words) * 0.7:  # 70% overlap threshold
                    is_similar = True
                    break

            if not is_similar:
                unique_results.append(result)
                seen_content.add(frozenset(content_words))

        return unique_results
