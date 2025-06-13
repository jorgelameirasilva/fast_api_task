"""
LLM Repository - Handles all LLM provider interactions
"""

import asyncio
import aiohttp
import os
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass
from loguru import logger


@dataclass
class LLMMessage:
    """LLM message structure"""

    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class LLMResponse:
    """LLM response structure"""

    content: str
    usage: Optional[Dict] = None
    model: Optional[str] = None


class LLMRepository:
    """Repository for LLM provider interactions"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))

    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response from LLM"""
        try:
            if not self.api_key:
                logger.warning("No OpenAI API key found, using mock response")
                return self._mock_response(messages[-1].content)

            payload = {
                "model": self.model,
                "messages": [
                    {"role": msg.role, "content": msg.content} for msg in messages
                ],
                "temperature": temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return LLMResponse(
                            content=data["choices"][0]["message"]["content"],
                            usage=data.get("usage"),
                            model=data.get("model"),
                        )
                    else:
                        logger.error(f"LLM API error: {response.status}")
                        return self._mock_response(messages[-1].content)

        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            return self._mock_response(messages[-1].content)

    async def generate_streaming_response(
        self, messages: List[LLMMessage], temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from LLM"""
        try:
            if not self.api_key:
                logger.warning("No OpenAI API key found, using mock streaming response")
                async for chunk in self._mock_streaming_response(messages[-1].content):
                    yield chunk
                return

            payload = {
                "model": self.model,
                "messages": [
                    {"role": msg.role, "content": msg.content} for msg in messages
                ],
                "temperature": temperature,
                "stream": True,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    import json

                                    chunk_data = json.loads(data)
                                    if (
                                        "choices" in chunk_data
                                        and chunk_data["choices"]
                                    ):
                                        delta = chunk_data["choices"][0].get(
                                            "delta", {}
                                        )
                                        if "content" in delta:
                                            yield delta["content"]
                                except json.JSONDecodeError:
                                    continue
                    else:
                        async for chunk in self._mock_streaming_response(
                            messages[-1].content
                        ):
                            yield chunk

        except Exception as e:
            logger.error(f"Error in streaming LLM API: {e}")
            async for chunk in self._mock_streaming_response(messages[-1].content):
                yield chunk

    def _mock_response(self, user_input: str) -> LLMResponse:
        """Mock response for development/testing"""
        mock_content = f"This is a mock response to: '{user_input}'. In a real implementation, this would be generated by an LLM."
        return LLMResponse(
            content=mock_content,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            model="mock-model",
        )

    async def _mock_streaming_response(
        self, user_input: str
    ) -> AsyncGenerator[str, None]:
        """Mock streaming response for development/testing"""
        response_parts = [
            "This ",
            "is ",
            "a ",
            "mock ",
            "streaming ",
            "response ",
            "to: ",
            f"'{user_input}'. ",
            "In ",
            "a ",
            "real ",
            "implementation, ",
            "this ",
            "would ",
            "be ",
            "generated ",
            "by ",
            "an ",
            "LLM.",
        ]

        for part in response_parts:
            yield part
            await asyncio.sleep(0.1)  # Simulate streaming delay

    async def health_check(self) -> bool:
        """Check if LLM service is healthy"""
        try:
            if not self.api_key:
                return False  # Mock is always "unhealthy" but functional

            # Simple test request
            test_messages = [LLMMessage(role="user", content="Hello")]
            response = await self.generate_response(test_messages, max_tokens=5)
            return bool(response.content)

        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False
