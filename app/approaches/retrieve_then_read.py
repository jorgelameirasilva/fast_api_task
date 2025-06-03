from typing import Any, Dict, List, Union, AsyncGenerator, Optional
from loguru import logger

from app.approaches.base import Approach


class RetrieveThenReadApproach(Approach):
    """
    Simple retrieve-then-read implementation.
    Retrieve top documents from search, then constructs a prompt
    to generate an answer with that prompt.
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
        super().__init__(
            search_client=search_client,
            openai_client=openai_client,
            chatgpt_model=chatgpt_model,
            chatgpt_deployment=chatgpt_deployment,
            embedding_model=embedding_model,
            embedding_deployment=embedding_deployment,
            sourcepage_field=sourcepage_field,
            content_field=content_field,
            query_language=query_language,
            query_speller=query_speller,
        )

    async def run(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        session_state: Any = None,
        context: Dict[str, Any] = {},
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Run the retrieve-then-read approach
        """
        logger.info("Running RetrieveThenReadApproach")

        # Extract the user query from messages
        q = messages[-1]["content"]
        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})

        # Determine retrieval mode
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top", 3)
        filter = self.build_filter(overrides)

        # Placeholder for search logic
        results = await self._search_documents(q, filter, has_text, has_vector, top)
        content = "\n".join(results)

        # Placeholder for response generation
        if stream:
            return self.run_with_streaming(
                messages, overrides, auth_claims, session_state
            )
        else:
            return await self.run_without_streaming(
                messages, overrides, auth_claims, session_state
            )

    async def _search_documents(
        self,
        query: str,
        filter: Optional[str],
        has_text: bool,
        has_vector: bool,
        top: int,
    ) -> List[str]:
        """
        Placeholder search implementation
        """
        logger.debug(f"Searching for: {query[:30]}...")

        # Return placeholder results
        return [
            f"Document 1: Information about {query}",
            f"Document 2: Additional context for {query}",
            f"Document 3: Related details about {query}",
        ]

    async def run_until_final_call(
        self,
        messages: List[Dict[str, str]],
        overrides: Dict[str, Any] = {},
        auth_claims: Dict[str, Any] = {},
        should_stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate final response using retrieved documents
        """
        logger.info("RetrieveThenRead: Generating final response")

        user_query = messages[-1]["content"] if messages else "No query"

        response_content = (
            f"Based on the retrieved documents, here's the answer to '{user_query}': "
            f"This is a comprehensive response generated using the Retrieve-Then-Read approach. "
            f"The system retrieved relevant documents and used them to generate this contextual answer."
        )

        return {
            "choices": [
                {
                    "message": {
                        "content": response_content,
                        "context": {
                            "data_points": [
                                f"Document 1: Information about {user_query}",
                                f"Document 2: Additional context for {user_query}",
                            ],
                            "thoughts": f"Question: {user_query}\nAnswer: {response_content}",
                        },
                    }
                }
            ]
        }
