"""Title generation service with repository pattern"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class TitleGenerationService(ABC):
    """Abstract base class for title generation services"""

    @abstractmethod
    async def generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a session title from the first user message"""
        pass


class SimpleTitleGenerationService(TitleGenerationService):
    """Simple title generation using string truncation"""

    async def generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a session title by truncating the first message"""
        title = first_message.strip()
        if len(title) > max_length:
            title = title[: max_length - 3] + "..."

        logger.debug(f"Generated simple title: '{title}'")
        return title


class LLMTitleGenerationService(TitleGenerationService):
    """LLM-based title generation with fallback to simple generation"""

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        model: str = "gpt-35-turbo",
        fallback_service: Optional[TitleGenerationService] = None,
    ):
        self.openai_client = openai_client
        self.model = model
        self.fallback_service = fallback_service or SimpleTitleGenerationService()

    async def generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a session title using LLM with fallback to simple generation"""
        try:
            # Use a focused prompt to generate a concise title
            prompt = f"""Generate a concise, descriptive title (max {max_length} characters) for a chat session that starts with this user message:

"{first_message}"

Requirements:
- Maximum {max_length} characters
- No quotes or special formatting
- Should be a clear, descriptive summary
- Professional and informative

Title:"""

            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20,  # Keep it short for titles
                n=1,
            )

            generated_title = response.choices[0].message.content.strip()

            # Clean up the response (remove quotes, extra spaces, etc.)
            generated_title = generated_title.strip("\"'")

            # Ensure it's not too long
            if len(generated_title) > max_length:
                generated_title = generated_title[: max_length - 3] + "..."

            # Fallback to simple method if LLM returned empty/invalid response
            if not generated_title or len(generated_title) < 3:
                logger.warning("LLM returned invalid title, using fallback service")
                return await self.fallback_service.generate_title(
                    first_message, max_length
                )

            logger.debug(f"Generated LLM title: '{generated_title}'")
            return generated_title

        except Exception as e:
            logger.warning(f"LLM title generation failed: {e}, using fallback service")
            return await self.fallback_service.generate_title(first_message, max_length)


def create_title_service(
    openai_client: Optional[AsyncOpenAI] = None, model: str = "gpt-35-turbo"
) -> TitleGenerationService:
    """Factory function to create the appropriate title generation service"""
    if openai_client:
        logger.info(f"Creating LLM title generation service with model: {model}")
        return LLMTitleGenerationService(openai_client, model)
    else:
        logger.info("Creating simple title generation service (no LLM available)")
        return SimpleTitleGenerationService()
