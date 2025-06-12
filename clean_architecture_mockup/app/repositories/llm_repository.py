"""
LLM Repository
Abstracts Large Language Model functionality with multiple implementations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """LLM message data model"""

    role: str  # "system", "user", "assistant"
    content: str
    timestamp: Optional[datetime] = None


@dataclass
class LLMRequest:
    """LLM request data model"""

    messages: List[LLMMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    model: Optional[str] = None


@dataclass
class LLMResponse:
    """LLM response data model"""

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    processing_time_ms: int


class LLMRepository(ABC):
    """Abstract LLM repository interface"""

    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using LLM"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, str]:
        """Check repository health status"""
        pass


class OpenAIRepository(LLMRepository):
    """OpenAI GPT implementation"""

    def __init__(self):
        self.api_key = self._get_api_key()
        self.model = self._get_default_model()
        self.base_url = self._get_base_url()
        logger.info(f"Initialized OpenAI Repository with model: {self.model}")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API"""
        try:
            start_time = datetime.now()
            logger.info(f"Generating response with {len(request.messages)} messages")

            # Placeholder for OpenAI SDK integration
            # This would be replaced with actual OpenAI API calls
            # import openai
            # client = openai.AsyncOpenAI(api_key=self.api_key)
            # response = await client.chat.completions.create(
            #     model=request.model or self.model,
            #     messages=[{"role": msg.role, "content": msg.content} for msg in request.messages],
            #     temperature=request.temperature,
            #     max_tokens=request.max_tokens
            # )

            # Mock implementation for demonstration
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return LLMResponse(
                content=f"OpenAI response to: {request.messages[-1].content}",
                model=request.model or self.model,
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
                finish_reason="stop",
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    async def health_check(self) -> Dict[str, str]:
        """Check OpenAI API health"""
        try:
            # Placeholder for actual health check
            return {"status": "healthy", "service": "OpenAI API", "model": self.model}
        except Exception:
            return {"status": "unhealthy", "service": "OpenAI API"}

    def _get_api_key(self) -> str:
        # Get from environment or config
        return "your-openai-api-key"

    def _get_default_model(self) -> str:
        # Get from environment or config
        return "gpt-4"

    def _get_base_url(self) -> Optional[str]:
        # Get from environment or config for custom endpoints
        return None


class MockLLMRepository(LLMRepository):
    """Mock LLM implementation for testing/development"""

    def __init__(self):
        self.model = "mock-llm-v1"
        self.responses = self._load_mock_responses()
        logger.info("Initialized Mock LLM Repository")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate mock response with pattern matching"""
        start_time = datetime.now()
        logger.info(f"Generating mock response for {len(request.messages)} messages")

        last_message = request.messages[-1].content.lower()

        # Pattern-based response selection
        response_content = self._select_response(last_message)

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return LLMResponse(
            content=response_content,
            model=self.model,
            usage={"prompt_tokens": 80, "completion_tokens": 40, "total_tokens": 120},
            finish_reason="stop",
            processing_time_ms=processing_time,
        )

    async def health_check(self) -> Dict[str, str]:
        """Mock health check always returns healthy"""
        return {"status": "healthy", "service": "Mock LLM", "model": self.model}

    def _select_response(self, query: str) -> str:
        """Select appropriate mock response based on query patterns"""
        for pattern, response in self.responses.items():
            if pattern in query:
                return response

        # Default response
        return f"This is a mock response to your query about: {query}"

    def _load_mock_responses(self) -> Dict[str, str]:
        """Load predefined mock responses"""
        return {
            "fastapi": "FastAPI is a modern, fast web framework for building APIs with Python. It's built on standard Python type hints and provides automatic API documentation.",
            "clean architecture": "Clean Architecture is a software design philosophy that separates the elements of a design into ring levels. The main rule is that code dependencies can only point inwards.",
            "dependency injection": "Dependency Injection is a design pattern that implements Inversion of Control for resolving dependencies. It makes code more testable and maintainable.",
            "repository pattern": "The Repository pattern encapsulates the logic needed to access data sources. It separates the infrastructure or technology used to access databases from the domain model layer.",
            "testing": "Testing is crucial for maintaining code quality. With proper dependency injection, you can easily mock dependencies and create isolated unit tests.",
            "hello": "Hello! I'm a mock LLM assistant. How can I help you today?",
            "help": "I can help you understand various software engineering concepts including FastAPI, Clean Architecture, design patterns, and best practices.",
        }
