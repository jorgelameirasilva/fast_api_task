"""
Dependency Injection Container for FastAPI application.
This provides proper IoC (Inversion of Control) for clean architecture.
"""

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from loguru import logger

from app.core.config import settings
from app.repositories.search_repository import (
    SearchRepository,
    AzureSearchRepository,
    MockSearchRepository,
)
from app.repositories.llm_repository import (
    LLMRepository,
    OpenAIRepository,
    MockLLMRepository,
)
from app.services.query_processing_service import QueryProcessingService
from app.services.response_generation_service import ResponseGenerationService
from app.services.chat_orchestration_service import ChatOrchestrationService
from app.services.ask_orchestration_service import AskOrchestrationService


def create_search_repository() -> SearchRepository:
    """Factory function to create search repository with fallback"""
    try:
        # Check if we have Azure Search configuration
        if all(
            [
                settings.AZURE_SEARCH_SERVICE,
                settings.SEARCH_API_KEY,
                settings.AZURE_SEARCH_INDEX,
            ]
        ):
            logger.info("Creating Azure Search repository")
            return AzureSearchRepository(
                service_name=settings.AZURE_SEARCH_SERVICE,
                api_key=settings.SEARCH_API_KEY,
                index_name=settings.AZURE_SEARCH_INDEX,
                content_field=settings.KB_FIELDS_CONTENT,
                source_field=settings.KB_FIELDS_SOURCEPAGE,
                title_field="title",
            )
        else:
            logger.warning("Azure Search not configured, using mock repository")
            return MockSearchRepository()
    except Exception as e:
        logger.error(f"Failed to create Azure Search repository: {e}")
        logger.info("Falling back to mock search repository")
        return MockSearchRepository()


def create_llm_repository() -> LLMRepository:
    """Factory function to create LLM repository with fallback"""
    try:
        # Check if we have OpenAI configuration
        if settings.OPENAI_API_KEY:
            logger.info(f"Creating OpenAI repository (host: {settings.OPENAI_HOST})")

            is_azure = settings.OPENAI_HOST == "azure"
            azure_endpoint = None

            if is_azure and settings.AZURE_OPENAI_SERVICE:
                azure_endpoint = (
                    f"https://{settings.AZURE_OPENAI_SERVICE}.openai.azure.com"
                )

            return OpenAIRepository(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_CHATGPT_MODEL,
                azure_endpoint=azure_endpoint,
                is_azure=is_azure,
                embedding_model=settings.OPENAI_EMB_MODEL,
                organization=settings.OPENAI_ORGANIZATION,
            )
        else:
            logger.warning("OpenAI not configured, using mock repository")
            return MockLLMRepository()
    except Exception as e:
        logger.error(f"Failed to create OpenAI repository: {e}")
        logger.info("Falling back to mock LLM repository")
        return MockLLMRepository()


class Container(containers.DeclarativeContainer):
    """Application IoC container"""

    # Configuration
    config = providers.Configuration()

    # Repositories with factory functions for proper fallback handling
    search_repository = providers.Singleton(create_search_repository)
    llm_repository = providers.Singleton(create_llm_repository)

    # Domain services
    query_processor = providers.Factory(
        QueryProcessingService,
        search_repository=search_repository,
        llm_repository=llm_repository,
    )

    response_generator = providers.Factory(
        ResponseGenerationService,
        llm_repository=llm_repository,
    )

    # Orchestration services (main business logic)
    ask_orchestrator = providers.Factory(
        AskOrchestrationService,
        query_processor=query_processor,
        response_generator=response_generator,
    )

    chat_orchestrator = providers.Factory(
        ChatOrchestrationService,
        query_processor=query_processor,
        response_generator=response_generator,
    )


# Global container instance
container = Container()


# Initialize container with settings
def initialize_container():
    """Initialize the container with application settings"""
    try:
        logger.info("Initializing dependency injection container...")

        # Configure the container with settings
        container.config.from_dict(
            {
                "AZURE_SEARCH_SERVICE": settings.AZURE_SEARCH_SERVICE,
                "SEARCH_API_KEY": settings.SEARCH_API_KEY,
                "AZURE_SEARCH_INDEX": settings.AZURE_SEARCH_INDEX,
                "OPENAI_API_KEY": settings.OPENAI_API_KEY,
                "OPENAI_CHATGPT_MODEL": settings.OPENAI_CHATGPT_MODEL,
                "AZURE_OPENAI_SERVICE": settings.AZURE_OPENAI_SERVICE,
                "OPENAI_HOST": settings.OPENAI_HOST,
            }
        )

        logger.info("Container initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize container: {e}")
        raise


# FastAPI dependency functions
async def get_ask_orchestrator() -> AskOrchestrationService:
    """FastAPI dependency for ask orchestrator"""
    return container.ask_orchestrator()


async def get_chat_orchestrator() -> ChatOrchestrationService:
    """FastAPI dependency for chat orchestrator"""
    return container.chat_orchestrator()


async def get_query_processor() -> QueryProcessingService:
    """FastAPI dependency for query processor"""
    return container.query_processor()


async def get_response_generator() -> ResponseGenerationService:
    """FastAPI dependency for response generator"""
    return container.response_generator()


# Health check functions
async def check_search_health() -> bool:
    """Check search repository health"""
    try:
        search_repo = container.search_repository()
        return await search_repo.health_check()
    except Exception as e:
        logger.error(f"Search health check failed: {e}")
        return False


async def check_llm_health() -> bool:
    """Check LLM repository health"""
    try:
        llm_repo = container.llm_repository()
        return await llm_repo.health_check()
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return False
