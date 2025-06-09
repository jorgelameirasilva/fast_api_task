"""
Search Repository Interface and Implementations.
This provides abstraction over different search providers (Azure, Elasticsearch, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class SearchResult:
    """Represents a search result document"""

    content: str
    source: str
    title: str
    relevance_score: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SearchQuery:
    """Represents a search query with parameters"""

    query: str
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None
    use_semantic_search: bool = True
    use_vector_search: bool = True

    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


class SearchRepository(ABC):
    """Abstract repository for search operations"""

    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform a search and return results"""
        pass

    @abstractmethod
    async def get_document_by_id(self, doc_id: str) -> Optional[SearchResult]:
        """Get a specific document by ID"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if search service is healthy"""
        pass


class AzureSearchRepository(SearchRepository):
    """Azure Cognitive Search implementation"""

    def __init__(
        self,
        service_name: str,
        api_key: str,
        index_name: str,
        content_field: str = "content",
        source_field: str = "sourcepage",
        title_field: str = "title",
    ):
        self.service_name = service_name
        self.api_key = api_key
        self.index_name = index_name
        self.content_field = content_field
        self.source_field = source_field
        self.title_field = title_field
        self._client = None

    async def _get_client(self):
        """Lazy initialization of Azure Search client"""
        if self._client is None:
            try:
                from azure.search.documents import SearchClient
                from azure.core.credentials import AzureKeyCredential

                self._client = SearchClient(
                    endpoint=f"https://{self.service_name}.search.windows.net",
                    index_name=self.index_name,
                    credential=AzureKeyCredential(self.api_key),
                )
                logger.info(f"Azure Search client initialized for {self.service_name}")
            except ImportError:
                logger.error("Azure Search SDK not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Azure Search client: {e}")
                raise
        return self._client

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform Azure Search query"""
        try:
            client = await self._get_client()

            # Build search parameters
            search_params = {
                "search_text": query.query,
                "top": query.top_k,
                "include_total_count": True,
            }

            # Add filters if provided
            if query.filters:
                filter_expressions = []
                for key, value in query.filters.items():
                    if isinstance(value, str):
                        filter_expressions.append(f"{key} eq '{value}'")
                    else:
                        filter_expressions.append(f"{key} eq {value}")

                if filter_expressions:
                    search_params["filter"] = " and ".join(filter_expressions)

            # Perform search
            results = client.search(**search_params)

            # Convert to SearchResult objects
            search_results = []
            for result in results:
                search_result = SearchResult(
                    content=result.get(self.content_field, ""),
                    source=result.get(self.source_field, "unknown"),
                    title=result.get(self.title_field, "Untitled"),
                    relevance_score=result.get("@search.score", 0.0),
                    metadata={
                        "search_score": result.get("@search.score", 0.0),
                        "index": self.index_name,
                        **{k: v for k, v in result.items() if not k.startswith("@")},
                    },
                )
                search_results.append(search_result)

            logger.info(
                f"Found {len(search_results)} results for query: {query.query[:50]}..."
            )
            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def get_document_by_id(self, doc_id: str) -> Optional[SearchResult]:
        """Get document by ID from Azure Search"""
        try:
            client = await self._get_client()
            result = client.get_document(key=doc_id)

            return SearchResult(
                content=result.get(self.content_field, ""),
                source=result.get(self.source_field, "unknown"),
                title=result.get(self.title_field, "Untitled"),
                relevance_score=1.0,  # Direct lookup
                metadata=result,
            )
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    async def health_check(self) -> bool:
        """Check Azure Search service health"""
        try:
            client = await self._get_client()
            # Try a simple search to verify connectivity
            list(client.search("test", top=1))
            return True
        except Exception as e:
            logger.error(f"Azure Search health check failed: {e}")
            return False


class MockSearchRepository(SearchRepository):
    """Mock implementation for testing and development"""

    def __init__(self):
        self.mock_documents = [
            SearchResult(
                content="Sample document content about healthcare benefits",
                source="healthcare_guide.pdf",
                title="Healthcare Benefits Guide",
                relevance_score=0.95,
                metadata={"page": 1},
            ),
            SearchResult(
                content="Employee handbook section on time off policies",
                source="employee_handbook.pdf",
                title="Time Off Policies",
                relevance_score=0.87,
                metadata={"page": 15},
            ),
            SearchResult(
                content="Information about 401k retirement plans",
                source="benefits_overview.pdf",
                title="401k Retirement Plans",
                relevance_score=0.82,
                metadata={"page": 3},
            ),
        ]

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Return mock search results"""
        logger.info(f"Mock search for: {query.query}")
        # Simple mock logic - return all documents with adjusted scores
        results = []
        for i, doc in enumerate(self.mock_documents[: query.top_k]):
            doc.relevance_score = max(0.1, doc.relevance_score - (i * 0.1))
            results.append(doc)
        return results

    async def get_document_by_id(self, doc_id: str) -> Optional[SearchResult]:
        """Return mock document"""
        return self.mock_documents[0] if self.mock_documents else None

    async def health_check(self) -> bool:
        """Mock health check always returns True"""
        return True
