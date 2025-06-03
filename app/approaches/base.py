from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union, AsyncGenerator, Optional
from loguru import logger


class Approach(ABC):
    """
    Base class for all approaches.
    """

    def __init__(
        self,
        search_client=None,
        openai_client=None,
        chatgpt_model: str = "gpt-3.5-turbo",
        chatgpt_deployment: Optional[str] = None,
        embedding_model: str = "text-embedding-ada-002",
        embedding_deployment: Optional[str] = None,
        sourcepage_field: str = "sourcepage",
        content_field: str = "content",
        query_language: str = "en-us",
        query_speller: str = "lexicon",
    ):
        self.search_client = search_client
        self.openai_client = openai_client
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_model = embedding_model
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller

    def build_filter(self, overrides: Dict[str, Any]) -> Optional[str]:
        """Build filter for search queries based on overrides"""
        exclude_category = overrides.get("exclude_category")
        filters = []

        if exclude_category:
            filters.append(f"category ne '{exclude_category}'")

        return " and ".join(filters) if filters else None

    @abstractmethod
    async def run(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        session_state: Any = None,
        context: Dict[str, Any] = {},
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Run the approach and return response
        """
        pass

    async def run_until_final_call(
        self,
        messages: List[Dict[str, str]],
        overrides: Dict[str, Any] = {},
        auth_claims: Dict[str, Any] = {},
        should_stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Run approach until final call - placeholder implementation
        """
        logger.info("Running approach until final call")
        return {
            "choices": [
                {
                    "message": {
                        "content": "This is a placeholder response from the approach system"
                    }
                }
            ]
        }

    async def run_without_streaming(
        self,
        messages: List[Dict[str, str]],
        overrides: Dict[str, Any] = {},
        auth_claims: Dict[str, Any] = {},
        session_state: Any = None,
    ) -> Dict[str, Any]:
        """
        Run approach without streaming - placeholder implementation
        """
        logger.info("Running approach without streaming")
        return await self.run_until_final_call(messages, overrides, auth_claims, False)

    async def run_with_streaming(
        self,
        messages: List[Dict[str, str]],
        overrides: Dict[str, Any] = {},
        auth_claims: Dict[str, Any] = {},
        session_state: Any = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run approach with streaming - placeholder implementation
        """
        logger.info("Running approach with streaming")

        # Placeholder streaming response
        yield {
            "choices": [
                {
                    "delta": {"content": "This is a streaming "},
                    "context": {},
                    "session_state": session_state,
                    "finish_reason": None,
                    "index": 0,
                }
            ]
        }

        yield {
            "choices": [
                {
                    "delta": {"content": "response from the approach system"},
                    "context": {},
                    "session_state": session_state,
                    "finish_reason": "stop",
                    "index": 0,
                }
            ]
        }
