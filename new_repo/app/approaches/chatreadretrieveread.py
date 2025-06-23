import json
import logging
import re
from typing import Any, AsyncGenerator, Coroutine, Literal, Optional, Union, overload

from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType, RawVectorQuery, VectorQuery
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)

from app.approaches.approach import Approach
from app.core.authentication import AuthenticationHelper
from app.core.messagebuilder import MessageBuilder
from app.text import nonewlines


class ChatReadRetrieveReadApproach(Approach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    NO_RESPONSE = "0"

    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then sends the conversation history,
    original user question, and search results to OpenAI to generate a response.
    """

    system_message_chat_conversation = """You are an AI Assistant. You will be given a question and a source and a chat history. Use the sources to answer the question. If you don't have information from the sources like publicly available information, or if the user is thanking you or says "I'm unable to provide help", don't format your answer using the source format. Write in a natural conversational way.
Each source should have a name followed by colon and the actual information. Don't format any mathematical formula in LaTeX, if you want to format a formula use unicode characters instead.
Don't assume sources, list each source separately, for example [info1.txt][info2.pdf].
Include all questions and answers from the chat history in your response.

Follow up questions prompt:
"""

    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching for information.
You have access to Azure AI Search service with rich search capabilities that can retrieve, summarize, and create search queries from prompts.
Generate a search query based on the conversation and the user question.
If you cannot determine a search query from the conversation, return just the number 0.
Do not include any text inside [] or <> in the search query terms.
Do not include any special characters like "*".
If the question is not in English, translate the question to English before generating the search query.
If you cannot generate a search query, return just the number 0.
"""

    query_prompt_few_shots = [
        {"role": "user", "content": "What are my health plans?"},
        {"role": "assistant", "content": "health insurance plans"},
        {"role": "user", "content": "does my plan cover cardio?"},
        {"role": "assistant", "content": "cardio health plan coverage"},
        {"role": "user", "content": "thanks"},
        {"role": "assistant", "content": "0"},
    ]

    def __init__(
        self,
        *,
        search_client: SearchClient,
        openai_client: AsyncOpenAI,
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],
        embedding_deployment: Optional[str],
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
        chatgpt_token_limit: int = 4096,
        embedding_model: str = "",
    ):
        self.search_client = search_client
        self.openai_client = openai_client
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.chatgpt_token_limit = chatgpt_token_limit
        self.embedding_model = embedding_model

    @overload
    async def run_until_final_call(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: Literal[False],
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, ChatCompletion]]: ...

    @overload
    async def run_until_final_call(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: Literal[True],
    ) -> tuple[
        dict[str, Any], Coroutine[Any, Any, AsyncStream[ChatCompletionChunk]]
    ]: ...

    async def run_until_final_call(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool,
    ) -> tuple[
        dict[str, Any],
        Coroutine[Any, Any, Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]],
    ]:
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = (
            True if overrides.get("semantic_captions") and has_text else False
        )
        top = overrides.get("top", 3)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)

        # Handle empty messages case
        if not history:
            original_user_query = "Hello"  # Default query for empty messages
        else:
            original_user_query = history[-1]["content"]
        user_query_request = "Generate a search query for: " + original_user_query

        functions = [
            {
                "name": "search_sources",
                "description": "Retrieve sources from the Azure AI Search Index",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Query string to retrieve documents from store search eg: 'health care plan'",
                        }
                    },
                    "required": ["search_query"],
                },
            },
        ]

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        messages = self.get_messages_from_history(
            system_prompt=self.query_prompt_template,
            model_id=self.chatgpt_model,
            history=history,
            user_content=user_query_request,
            max_tokens=self.chatgpt_token_limit - len(user_query_request),
            few_shots=self.query_prompt_few_shots,
        )

        chat_completion: ChatCompletion = (
            await self.openai_client.chat.completions.create(
                messages=messages,
                model=(
                    self.chatgpt_deployment
                    if self.chatgpt_deployment
                    else self.chatgpt_model
                ),
                temperature=0.0,
                max_tokens=100,
                n=1,
                functions=functions,
                function_call="auto",
            )
        )

        query_text = self.get_search_query(chat_completion, original_user_query)

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
        vectors: list[VectorQuery] = []
        if has_vector:
            query_vector = await self.openai_client.embeddings.create(
                model=(
                    self.embedding_deployment
                    if self.embedding_deployment
                    else self.embedding_model
                ),
                input=query_text,
            )
            query_vector = query_vector.data[0].embedding
            vectors.append(
                RawVectorQuery(vector=query_vector, k=50, fields="embedding")
            )

        if not has_text:
            query_text = None

        filter = self.build_filter(overrides, auth_claims)

        if overrides.get("semantic_ranker") and has_text:
            r = await self.search_client.search(
                query_text,
                filter=filter,
                query_type=QueryType.SEMANTIC,
                query_language=self.query_language,
                query_speller=self.query_speller,
                semantic_configuration_name="default",
                top=top,
                query_caption=(
                    "extractive|highlight-false" if use_semantic_captions else None
                ),
            )
        else:
            r = await self.search_client.search(
                query_text, filter=filter, top=top, vector_queries=vectors
            )

        if use_semantic_captions:
            results = [
                doc[self.sourcepage_field]
                + ": "
                + nonewlines(" . ".join([c.text for c in doc["@search.captions"]]))
                async for doc in r
            ]
        else:
            results = [
                doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field])
                async for doc in r
            ]

        content = "\n".join(results)

        follow_up_questions_prompt = (
            self.system_message_chat_conversation
            if overrides.get("suggest_followup_questions")
            else ""
        )

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        prompt_override = overrides.get("prompt_template")
        if prompt_override is None:
            system_message = self.system_message_chat_conversation.format(
                injected_prompt="",
                follow_up_questions_prompt=follow_up_questions_prompt,
                original_user_query=original_user_query,
            )
        elif prompt_override.startswith(">>>"):
            system_message = self.system_message_chat_conversation.format(
                injected_prompt=prompt_override[3:] + "\n",
                follow_up_questions_prompt=follow_up_questions_prompt,
            )
        else:
            system_message = prompt_override.format(
                follow_up_questions_prompt=follow_up_questions_prompt
            )

        response_token_limit = 1024
        messages_token_limit = self.chatgpt_token_limit - response_token_limit
        messages = self.get_messages_from_history(
            system_prompt=system_message,
            model_id=self.chatgpt_model,
            history=history,
            user_content=original_user_query,
            max_tokens=messages_token_limit,
        )

        msg_to_display = "\n\n".join([str(message) for message in messages])

        extra_info = {
            "data_points": results,
            "thoughts": f"Searched for:<br>{query_text}<br><br>Conversations:<br>"
            + msg_to_display.replace("\n", "<br>"),
            "msg_to_display": msg_to_display.replace("\n", "<br>"),
        }

        chat_coroutine = self.openai_client.chat.completions.create(
            messages=messages,
            model=(
                self.chatgpt_deployment
                if self.chatgpt_deployment
                else self.chatgpt_model
            ),
            temperature=overrides.get("temperature", 0.3),
            max_tokens=response_token_limit,
            n=1,
            stream=should_stream,
        )
        return (extra_info, chat_coroutine)

    async def run_with_streaming(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
        context: dict[str, Any] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        extra_info, chat_coroutine = await self.run_until_final_call(
            history, overrides, auth_claims, should_stream=True
        )

        followup_questions_started = False
        followup_content = ""
        async for event_chunk in await chat_coroutine:
            event = event_chunk.model_dump()
            if event["object"] == "chat.completion.chunk":
                if (
                    event["choices"]
                    and event["choices"][0]
                    and event["choices"][0]["delta"]
                ):
                    content = event["choices"][0]["delta"].get("content")
                    content = content if content else ""
                    if content.startswith("<br>"):
                        content = content[4:]
                    if overrides.get("suggest_followup_questions") and "<<" in content:
                        followup_questions_started = True
                        earlier_content = content[: content.index("<<")]
                        if earlier_content:
                            event["choices"][0]["delta"]["content"] = earlier_content
                            yield event
                    elif followup_questions_started:
                        followup_content += content
                    else:
                        yield event
            if followup_content:
                _, followup_questions = self.extract_followup_questions(
                    followup_content
                )
                yield {
                    "choices": [
                        {
                            "delta": {"role": self.ASSISTANT},
                            "context": {"followup_questions": followup_questions},
                            "session_state": None,
                            "finish_reason": None,
                        }
                    ],
                    "object": "chat.completion.chunk",
                }

    async def run_without_streaming(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> dict[str, Any]:
        extra_info, chat_coroutine = await self.run_until_final_call(
            history, overrides, auth_claims, should_stream=False
        )
        chat_completion = await chat_coroutine
        content = chat_completion.choices[0].message.content

        if overrides.get("suggest_followup_questions"):
            content, followup_questions = self.extract_followup_questions(content)
            extra_info["followup_questions"] = followup_questions

        chat_completion.choices[0].message.content = content
        return {"message": chat_completion.choices[0].message, **extra_info}

    async def run(
        self,
        messages: list[dict],
        stream: bool = False,
        session_state: Any = None,
        context: dict[str, Any] = None,
    ) -> Union[dict[str, Any], AsyncGenerator[dict[str, Any], None]]:
        overrides = context.get("overrides", {}) if context else {}
        auth_claims = context.get("auth_claims", {}) if context else {}
        if stream is False:
            return await self.run_without_streaming(
                messages, overrides, auth_claims, session_state
            )
        else:
            return self.run_with_streaming(
                messages, overrides, auth_claims, session_state, context
            )

    def get_messages_from_history(
        self,
        system_prompt: str,
        model_id: str,
        history: list[dict[str, str]],
        user_content: str,
        max_tokens: int,
        few_shots: list[dict[str, str]] = [],
    ) -> list[ChatCompletionMessageParam]:
        message_builder = MessageBuilder(system_prompt, model_id)

        for shot in reversed(few_shots):
            message_builder.insert_message(shot["role"], shot["content"])

        append_index = len(few_shots) + 1

        message_builder.insert_message(self.USER, user_content, index=append_index)
        total_token_count = message_builder.count_tokens_for_message(
            {"role": self.USER, "content": user_content}
        )
        newest_to_oldest = list(reversed(history[:-1]))

        for message in newest_to_oldest:
            potential_message_count = message_builder.count_tokens_for_message(message)
            if (total_token_count + potential_message_count) > max_tokens:
                logging.debug(
                    "Reached max tokens of %d, history will be truncated", max_tokens
                )
                break
            message_builder.insert_message(
                message["role"], message["content"], index=append_index
            )
            total_token_count += potential_message_count
        return message_builder.messages

    def get_search_query(self, chat_completion: ChatCompletion, user_query: str) -> str:
        response_message = chat_completion.choices[0].message
        if response_message.function_call:
            function_call = response_message.function_call
            if function_call.name == "search_sources":
                arg = json.loads(function_call.arguments)
                search_query = arg.get("search_query", self.NO_RESPONSE)
                return search_query if search_query != self.NO_RESPONSE else user_query
        elif response_message.content:
            query_text = response_message.content.strip()
            if query_text != self.NO_RESPONSE:
                return query_text
        return user_query

    def extract_followup_questions(self, content: str):
        return content.split("<<")[0], re.findall(r"<<(.*?)>>", content)
