"""Mock clients for development and testing"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator
import json
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage
from openai.types import CreateEmbeddingResponse, Embedding
from openai.types.create_embedding_response import Usage


class MockSearchClient:
    """Mock Azure Search client for development"""

    def __init__(
        self, endpoint: str = None, index_name: str = None, credential: Any = None
    ):
        self.endpoint = endpoint
        self.index_name = index_name
        self.credential = credential

    async def search(self, search_text: str = "", **kwargs):
        """Mock search that returns sample documents as async generator"""
        await asyncio.sleep(0.1)  # Simulate network delay

        # Mock search results
        results = [
            {
                "id": "doc1",
                "content": "This is a sample HR document about reporting illness. Please follow the company guidelines for sick leave.",
                "sourcepage": "hr-handbook-illness.pdf",
                "score": 0.95,
            },
            {
                "id": "doc2",
                "content": "For reporting any workplace illness or injury, contact your supervisor immediately and fill out the incident report form.",
                "sourcepage": "safety-guidelines.pdf",
                "score": 0.87,
            },
            {
                "id": "doc3",
                "content": "Employee health and safety is our top priority. Report any health concerns to HR within 24 hours.",
                "sourcepage": "employee-handbook.pdf",
                "score": 0.76,
            },
        ]

        # Return as async generator
        async def async_result_generator():
            for result in results:
                yield result

        return async_result_generator()

    def close(self):
        """Close the client"""
        pass


class MockBlobContainerClient:
    """Mock Azure Blob Storage client for development"""

    def __init__(self, container_name: str = None):
        self.container_name = container_name

    def get_blob_client(self, blob_name: str):
        """Return a mock blob client"""
        return MockBlobClient(blob_name)

    async def list_blobs(self, **kwargs):
        """Mock list blobs"""
        await asyncio.sleep(0.05)
        return []

    def close(self):
        """Close the client"""
        pass


class MockBlobClient:
    """Mock blob client for individual blob operations"""

    def __init__(self, blob_name: str):
        self.blob_name = blob_name

    def download_blob(self):
        """Mock blob download"""
        return MockBlobDownload()


class MockBlobDownload:
    """Mock blob download object"""

    def __init__(self):
        self.properties = {"content_settings": {"content_type": "application/pdf"}}

    def readinto(self, buffer):
        """Mock read into buffer"""
        mock_content = b"Mock PDF content for testing"
        buffer.write(mock_content)
        return len(mock_content)


class MockOpenAIClient:
    """Mock OpenAI client that returns realistic responses"""

    class Chat:
        class Completions:
            async def create(
                self, messages=None, model="gpt-4o", stream=False, **kwargs
            ):
                """Mock chat completion"""
                await asyncio.sleep(0.2)  # Simulate API delay

                if stream:
                    return self._create_stream_response(messages, model, **kwargs)
                else:
                    return self._create_response(messages, model, **kwargs)

            def _create_response(self, messages, model, **kwargs):
                """Create a standard chat completion response"""
                # Extract the last user message for context
                user_message = ""
                if messages:
                    for msg in reversed(messages):
                        if msg.get("role") == "user":
                            user_message = msg.get("content", "")
                            break

                # Generate contextual response
                if "illness" in user_message.lower() or "sick" in user_message.lower():
                    content = """Based on the HR documents I found, here's how to report an illness:

1. **Immediate Action**: Contact your supervisor as soon as possible
2. **Documentation**: Fill out the incident report form 
3. **Timeline**: Report to HR within 24 hours
4. **Follow-up**: Follow company guidelines for sick leave procedures

The company prioritizes employee health and safety. Make sure to follow the established protocols for reporting workplace illness or injury."""

                elif "chat" in user_message.lower() or "help" in user_message.lower():
                    content = """I'm here to help you with HR-related questions. I can assist with:

- Reporting illness or workplace injuries
- Understanding company policies
- Sick leave procedures
- Employee handbook questions
- Safety guidelines

What specific HR topic would you like help with?"""

                else:
                    content = f"""I understand you're asking about: "{user_message[:100]}..."

Based on the available HR documents and company policies, I can provide guidance on various workplace topics. Could you please be more specific about what you need help with? I'm here to help with HR-related questions, company policies, and procedures."""

                # Create the response message with context
                message = ChatCompletionMessage(content=content, role="assistant")

                # Add context information (similar to original approaches)
                message.context = {
                    "data_points": [
                        "hr-handbook-illness.pdf: HR guidelines for illness reporting",
                        "safety-guidelines.pdf: Workplace safety and incident reporting",
                        "employee-handbook.pdf: General employee policies and procedures",
                    ],
                    "thoughts": f"The user asked about '{user_message[:50]}...'. I searched through HR documents and found relevant information about company policies and procedures. I provided a structured response with actionable steps.",
                    "followup_questions": [
                        "<<Do you need information about specific sick leave policies?>>",
                        "<<Would you like details about the incident report form?>>",
                        "<<Do you have questions about contacting your supervisor?>>",
                    ],
                }

                return ChatCompletion(
                    id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    choices=[Choice(finish_reason="stop", index=0, message=message)],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion",
                    usage=CompletionUsage(
                        completion_tokens=len(content.split()),
                        prompt_tokens=len(str(messages).split()) if messages else 10,
                        total_tokens=len(content.split())
                        + (len(str(messages).split()) if messages else 10),
                    ),
                )

            async def _create_stream_response(self, messages, model, **kwargs):
                """Create a streaming chat completion response"""
                # Import at the top to avoid naming conflicts
                from openai.types.chat import ChatCompletionChunk
                from openai.types.chat.chat_completion_chunk import (
                    Choice as ChunkChoice,
                    ChoiceDelta,
                )

                response = self._create_response(messages, model, **kwargs)

                # Convert to streaming format - return the generator directly
                content = response.choices[0].message.content
                words = content.split()

                for i, word in enumerate(words):
                    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"

                    chunk_choice = ChunkChoice(
                        delta=ChoiceDelta(
                            content=word + " " if i < len(words) - 1 else word
                        ),
                        finish_reason=None,
                        index=0,
                    )

                    streaming_chunk = ChatCompletionChunk(
                        id=chunk_id,
                        choices=[chunk_choice],
                        created=int(time.time()),
                        model=model,
                        object="chat.completion.chunk",
                    )

                    yield streaming_chunk
                    await asyncio.sleep(0.05)  # Simulate streaming delay

                # Final chunk with context
                final_choice = ChunkChoice(
                    delta=ChoiceDelta(), finish_reason="stop", index=0
                )

                final_streaming_chunk = ChatCompletionChunk(
                    id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    choices=[final_choice],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                )

                yield final_streaming_chunk

    class Embeddings:
        async def create(self, input=None, model="text-embedding-ada-002", **kwargs):
            """Mock embeddings creation"""
            await asyncio.sleep(0.1)  # Simulate API delay

            # Generate mock embeddings based on input
            if isinstance(input, list):
                input_texts = input
            else:
                input_texts = [input] if input else [""]

            embeddings = []
            for i, text in enumerate(input_texts):
                # Create deterministic but realistic-looking embeddings
                embedding = [0.1 * hash(text + str(j)) % 100 / 100 for j in range(1536)]
                embeddings.append(
                    Embedding(object="embedding", index=i, embedding=embedding)
                )

            return CreateEmbeddingResponse(
                object="list",
                data=embeddings,
                model=model,
                usage=Usage(
                    prompt_tokens=sum(len(text.split()) for text in input_texts),
                    total_tokens=sum(len(text.split()) for text in input_texts),
                ),
            )

    def __init__(self):
        self.chat = self.Chat()
        self.chat.completions = self.Chat.Completions()
        self.embeddings = self.Embeddings()

    async def close(self):
        """Close the client"""
        pass


class MockAzureOpenAIClient(MockOpenAIClient):
    """Mock Azure OpenAI client that extends the base OpenAI mock"""

    def __init__(
        self,
        base_url: str = None,
        azure_ad_token_provider=None,
        api_version: str = None,
        **kwargs,
    ):
        super().__init__()
        self.base_url = base_url
        self.azure_ad_token_provider = azure_ad_token_provider
        self.api_version = api_version

    async def close(self):
        """Close the Azure OpenAI client"""
        pass


class MockTableServiceClient:
    """Mock Azure Storage Table Service client for development"""

    def __init__(self, endpoint: str = None, credential: Any = None):
        self.endpoint = endpoint
        self.credential = credential
        self._tables = {}  # Store table clients

    def get_table_client(self, table_name: str):
        """Get a mock table client for the specified table"""
        if table_name not in self._tables:
            self._tables[table_name] = MockTableClient(table_name)
        return self._tables[table_name]

    async def create_table_if_not_exists(self, table_name: str):
        """Mock create table if not exists"""
        await asyncio.sleep(0.05)  # Simulate network delay
        if table_name not in self._tables:
            self._tables[table_name] = MockTableClient(table_name)
        return True

    async def list_tables(self):
        """Mock list tables"""
        await asyncio.sleep(0.05)
        return list(self._tables.keys())

    async def close(self):
        """Close the service client"""
        pass


class MockTableClient:
    """Mock Azure Storage Table client for individual table operations"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self._entities = {}  # Store entities in memory

    async def create_entity(self, entity: dict):
        """Mock create entity operation"""
        await asyncio.sleep(0.1)  # Simulate network delay

        # Simulate Azure Table Storage entity creation
        entity_key = f"{entity.get('PartitionKey', '')}#{entity.get('RowKey', '')}"

        # Add Azure Storage metadata
        stored_entity = entity.copy()
        stored_entity["etag"] = f"W/\"datetime'{uuid.uuid4()}'\""
        stored_entity["timestamp"] = time.time()

        self._entities[entity_key] = stored_entity

        print(f"[MOCK TABLE] Created entity in {self.table_name}: {entity}")
        return stored_entity

    async def get_entity(self, partition_key: str, row_key: str):
        """Mock get entity operation"""
        await asyncio.sleep(0.05)
        entity_key = f"{partition_key}#{row_key}"

        if entity_key in self._entities:
            return self._entities[entity_key]
        else:
            # Simulate ResourceNotFoundError
            raise Exception(f"Entity not found: {entity_key}")

    async def update_entity(self, entity: dict, mode="merge"):
        """Mock update entity operation"""
        await asyncio.sleep(0.1)
        entity_key = f"{entity.get('PartitionKey', '')}#{entity.get('RowKey', '')}"

        if entity_key in self._entities:
            if mode == "merge":
                self._entities[entity_key].update(entity)
            else:
                self._entities[entity_key] = entity

            # Update metadata
            self._entities[entity_key]["etag"] = f"W/\"datetime'{uuid.uuid4()}'\""
            self._entities[entity_key]["timestamp"] = time.time()

            print(f"[MOCK TABLE] Updated entity in {self.table_name}: {entity}")
            return self._entities[entity_key]
        else:
            raise Exception(f"Entity not found for update: {entity_key}")

    async def delete_entity(self, partition_key: str, row_key: str):
        """Mock delete entity operation"""
        await asyncio.sleep(0.05)
        entity_key = f"{partition_key}#{row_key}"

        if entity_key in self._entities:
            del self._entities[entity_key]
            print(f"[MOCK TABLE] Deleted entity from {self.table_name}: {entity_key}")
        else:
            raise Exception(f"Entity not found for deletion: {entity_key}")

    async def query_entities(self, query_filter: str = None, select: List[str] = None):
        """Mock query entities operation"""
        await asyncio.sleep(0.1)

        # Return all entities as a simple list (real implementation would apply filters)
        entities = list(self._entities.values())
        print(f"[MOCK TABLE] Queried {len(entities)} entities from {self.table_name}")

        # Return as async generator
        async def async_result_generator():
            for entity in entities:
                yield entity

        return async_result_generator()

    async def close(self):
        """Close the table client"""
        pass


# Global client instances
_search_client: Optional[MockSearchClient] = None
_openai_client: Optional[MockOpenAIClient] = None
_embeddings_client: Optional[MockOpenAIClient] = None
_blob_container_client: Optional[MockBlobContainerClient] = None
_mock_blob_container_client: Optional[MockBlobContainerClient] = None
_mock_table_service_client: Optional[MockTableServiceClient] = None


def get_mock_search_client() -> MockSearchClient:
    """Get or create mock search client"""
    global _search_client
    if _search_client is None:
        _search_client = MockSearchClient()
    return _search_client


def get_mock_openai_client() -> MockOpenAIClient:
    """Get or create mock OpenAI client"""
    global _openai_client
    if _openai_client is None:
        _openai_client = MockAzureOpenAIClient()
    return _openai_client


def get_mock_embeddings_client() -> MockOpenAIClient:
    """Get or create mock embeddings client"""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = MockAzureOpenAIClient()
    return _embeddings_client


def get_mock_blob_container_client() -> MockBlobContainerClient:
    """Get a mock blob container client for development"""
    global _mock_blob_container_client
    if _mock_blob_container_client is None:
        _mock_blob_container_client = MockBlobContainerClient("mock-container")
    return _mock_blob_container_client


def get_mock_table_service_client() -> MockTableServiceClient:
    """Get a mock Azure Storage Table service client for development"""
    global _mock_table_service_client
    if _mock_table_service_client is None:
        _mock_table_service_client = MockTableServiceClient(
            endpoint="https://mock-storage.table.core.windows.net"
        )
    return _mock_table_service_client


async def cleanup_mock_clients():
    """Cleanup mock clients during shutdown"""
    global _search_client, _openai_client, _embeddings_client, _blob_container_client, _mock_blob_container_client, _mock_table_service_client

    try:
        if _search_client:
            _search_client.close()
            _search_client = None

        if _openai_client:
            await _openai_client.close()
            _openai_client = None

        if _embeddings_client:
            await _embeddings_client.close()
            _embeddings_client = None

        if _blob_container_client:
            _blob_container_client.close()
            _blob_container_client = None

        if _mock_blob_container_client:
            _mock_blob_container_client.close()
            _mock_blob_container_client = None

        if _mock_table_service_client:
            await _mock_table_service_client.close()
            _mock_table_service_client = None

    except Exception as e:
        print(f"Error during mock client cleanup: {e}")
