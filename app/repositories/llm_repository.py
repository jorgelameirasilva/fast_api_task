"""
LLM Repository Interface and Implementations.
This provides abstraction over different LLM providers (OpenAI, Azure OpenAI, Anthropic, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from loguru import logger


@dataclass
class LLMMessage:
    """Represents a message in LLM conversation"""

    role: str  # "system", "user", "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMResponse:
    """Represents an LLM response"""

    content: str
    usage_tokens: Dict[str, int]  # {"prompt": int, "completion": int, "total": int}
    model: str
    finish_reason: str
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMRequest:
    """Represents an LLM request"""

    messages: List[LLMMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    additional_params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.additional_params is None:
            self.additional_params = {}


class LLMRepository(ABC):
    """Abstract repository for LLM operations"""

    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM"""
        pass

    @abstractmethod
    async def generate_embeddings(
        self, texts: List[str], model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for the given texts"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if LLM service is healthy"""
        pass


class OpenAIRepository(LLMRepository):
    """OpenAI API implementation"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        azure_endpoint: Optional[str] = None,
        is_azure: bool = False,
        embedding_model: str = "text-embedding-ada-002",
        organization: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.azure_endpoint = azure_endpoint
        self.is_azure = is_azure
        self.embedding_model = embedding_model
        self.organization = organization
        self._client = None

    async def _get_client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            try:
                if self.is_azure:
                    from openai import AsyncAzureOpenAI

                    self._client = AsyncAzureOpenAI(
                        api_key=self.api_key,
                        api_version="2023-12-01-preview",
                        azure_endpoint=self.azure_endpoint,
                    )
                    logger.info("Azure OpenAI client initialized")
                else:
                    from openai import AsyncOpenAI

                    self._client = AsyncOpenAI(
                        api_key=self.api_key, organization=self.organization
                    )
                    logger.info("OpenAI client initialized")
            except ImportError:
                logger.error("OpenAI SDK not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise
        return self._client

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API"""
        try:
            client = await self._get_client()

            # Convert messages to OpenAI format
            messages = [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ]

            # Build request parameters
            params = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "stream": False,
                **request.additional_params,
            }

            if request.max_tokens:
                params["max_tokens"] = request.max_tokens

            # Make API call
            response = await client.chat.completions.create(**params)

            # Extract response data
            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content,
                usage_tokens={
                    "prompt": usage.prompt_tokens,
                    "completion": usage.completion_tokens,
                    "total": usage.total_tokens,
                },
                model=response.model,
                finish_reason=choice.finish_reason,
                metadata={
                    "response_id": response.id,
                    "created": response.created,
                    "provider": "azure_openai" if self.is_azure else "openai",
                },
            )

        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            raise

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate streaming response using OpenAI API"""
        try:
            client = await self._get_client()

            # Convert messages to OpenAI format
            messages = [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ]

            # Build request parameters
            params = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "stream": True,
                **request.additional_params,
            }

            if request.max_tokens:
                params["max_tokens"] = request.max_tokens

            # Make streaming API call
            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Failed to generate streaming LLM response: {e}")
            raise

    async def generate_embeddings(
        self, texts: List[str], model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            client = await self._get_client()

            response = await client.embeddings.create(
                model=model or self.embedding_model, input=texts
            )

            embeddings = [data.embedding for data in response.data]
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    async def health_check(self) -> bool:
        """Check OpenAI service health"""
        try:
            client = await self._get_client()
            # Try a simple API call
            await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False


class MockLLMRepository(LLMRepository):
    """Mock implementation for testing and development"""

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or [
            "This is a mock response from the LLM repository.",
            "Another mock response for testing purposes.",
            "Yet another mock response with different content.",
        ]
        self.response_index = 0

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate mock response"""
        logger.info(f"Mock LLM request with {len(request.messages)} messages")

        # Get next response in rotation
        content = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        return LLMResponse(
            content=content,
            usage_tokens={"prompt": 50, "completion": 20, "total": 70},
            model="mock-model",
            finish_reason="stop",
            metadata={"mock": True, "request_index": self.response_index},
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate mock streaming response"""
        content = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        # Stream words one by one
        words = content.split()
        for word in words:
            yield word + " "

    async def generate_embeddings(
        self, texts: List[str], model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate mock embeddings"""
        logger.info(f"Mock embeddings for {len(texts)} texts")
        # Return mock 768-dimensional embeddings
        import random

        return [[random.random() for _ in range(768)] for _ in texts]

    async def health_check(self) -> bool:
        """Mock health check always returns True"""
        return True
