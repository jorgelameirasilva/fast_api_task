from typing import Any, Dict, List, Union, AsyncGenerator, Optional
from loguru import logger

from app.approaches.base import Approach


class ChatReadRetrieveReadApproach(Approach):
    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then
    sends the conversation history, original user question, and search results to OpenAI to generate a response.
    """

    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    NO_RESPONSE = "0"

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

        self.system_message_chat_conversation = (
            "You are an intelligent assistant helping Contoso Inc employees with their healthcare plan questions and employee handbook questions. "
            "Use 'you' to refer to the individual asking the questions even if they ask with 'we'. "
            "Answer the following question using only the data provided in the sources below. "
            "For tabular information return it as an html table. Do not return markdown format. "
            "Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. "
            "If you cannot answer using the sources below, say you don't know. Use below example to answer"
        )

        self.follow_up_questions_prompt_content = """Generate 3 very brief follow-up questions that the user would likely ask next.
        Use double angle brackets to enclose the follow-up questions, e.g. <<Are there exclusions for prescriptions?>>
        Try not to repeat questions that have already been asked.
        Only generate questions related to the employee handbook and health plan.
        Make sure the last question ends with ">>"."""

        self.query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about employee handbook and their health plan.
        You have access to Azure AI Search index with 100's of documents.
        Generate a search query based on the conversation and the new question.
        Do not include cited source filenames and document names e.g info1.txt or doc.pdf in the search query terms.
        Do not include any text inside [] or <<>> in the search query terms.
        Do not include any special characters like '+'.
        If the question is not in English, translate the question to English before generating the search query.
        If you cannot generate a search query, return just the number 0.
        """

    async def run(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        session_state: Any = None,
        context: Dict[str, Any] = {},
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Run the chat-read-retrieve-read approach
        """
        logger.info("Running ChatReadRetrieveReadApproach")

        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})

        if stream:
            return self.run_with_streaming(
                messages, overrides, auth_claims, session_state
            )
        else:
            return await self.run_without_streaming(
                messages, overrides, auth_claims, session_state
            )

    async def get_messages_from_history(
        self,
        system_prompt: str,
        model_id: str,
        history: List[Dict[str, str]],
        user_content: str,
        max_tokens: int,
        few_shots: List = [],
    ) -> List[Dict[str, str]]:
        """
        Build message list from conversation history - placeholder implementation
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Add few shot examples if provided
        for shot in few_shots:
            messages.append({"role": shot.get("role"), "content": shot.get("content")})

        # Add conversation history (simplified)
        for message in history[-5:]:  # Keep last 5 messages
            messages.append({"role": message["role"], "content": message["content"]})

        # Add current user message
        messages.append({"role": "user", "content": user_content})

        return messages

    async def get_search_query(self, chat_completion, user_query: str) -> str:
        """
        Extract search query from chat completion - placeholder implementation
        """
        logger.debug("Extracting search query from chat completion")

        # Placeholder: just return the user query
        return user_query

    async def run_until_final_call(
        self,
        messages: List[Dict[str, str]],
        overrides: Dict[str, Any] = {},
        auth_claims: Dict[str, Any] = {},
        should_stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate final response using chat conversation context
        """
        logger.info("ChatReadRetrieveRead: Generating final response")

        user_query = messages[-1]["content"] if messages else "No query"

        response_content = (
            f"Based on the conversation context and retrieved documents, here's the answer to '{user_query}': "
            f"This is a comprehensive response generated using the Chat-Read-Retrieve-Read approach. "
            f"The system analyzed the conversation history, retrieved relevant documents, and generated this contextual answer."
        )

        return {
            "choices": [
                {
                    "message": {
                        "content": response_content,
                        "context": {
                            "data_points": [
                                f"Conversation context for: {user_query}",
                                f"Retrieved documents about: {user_query}",
                            ],
                            "thoughts": f"Conversation: {user_query}\nAnswer: {response_content}",
                            "followup_questions": [
                                f"<<Can you tell me more about {user_query[:20]}?>>",
                                f"<<What are the details of {user_query[:20]}?>>",
                                f"<<Are there any exceptions for {user_query[:20]}?>>",
                            ],
                        },
                    }
                }
            ]
        }
