"""
Dependency Injection Container
Manages all application dependencies with smart fallback strategy
"""

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
import os
from typing import Optional

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
from app.auth.repositories.jwt_repository import (
    JWTRepository,
    ProductionJWTRepository,
    MockJWTRepository,
)
from app.services.domain.query_processing_service import QueryProcessingService
from app.services.domain.response_generation_service import ResponseGenerationService
from app.services.orchestration.ask_orchestration_service import AskOrchestrationService
from app.services.orchestration.chat_orchestration_service import (
    ChatOrchestrationService,
)
from app.auth.services.authentication_service import AuthenticationService


class ApplicationContainer(containers.DeclarativeContainer):
    """
    IoC Container with smart fallback strategy
    Production: Real services with fallback to mock
    Development/Testing: Mock services by default
    """

    # Configuration
    config = providers.Configuration()

    # Environment detection
    environment = providers.Factory(lambda: os.getenv("ENVIRONMENT", "development"))

    # Repository Factories with Fallback Strategy
    search_repository = providers.Factory(
        _create_search_repository, environment=environment
    )

    llm_repository = providers.Factory(_create_llm_repository, environment=environment)

    jwt_repository = providers.Factory(_create_jwt_repository, environment=environment)

    # Domain Services
    query_processing_service = providers.Factory(
        QueryProcessingService, search_repository=search_repository
    )

    response_generation_service = providers.Factory(
        ResponseGenerationService, llm_repository=llm_repository
    )

    authentication_service = providers.Factory(
        AuthenticationService, jwt_repository=jwt_repository
    )

    # Orchestration Services
    ask_orchestration_service = providers.Factory(
        AskOrchestrationService,
        query_processing_service=query_processing_service,
        response_generation_service=response_generation_service,
    )

    chat_orchestration_service = providers.Factory(
        ChatOrchestrationService,
        query_processing_service=query_processing_service,
        response_generation_service=response_generation_service,
    )


def _create_search_repository(environment: str) -> SearchRepository:
    """Factory function with fallback strategy for search repository"""
    if environment == "production":
        try:
            return AzureSearchRepository()
        except Exception as e:
            print(f"Warning: Failed to create AzureSearchRepository: {e}")
            print("Falling back to MockSearchRepository")
            return MockSearchRepository()
    else:
        return MockSearchRepository()


def _create_llm_repository(environment: str) -> LLMRepository:
    """Factory function with fallback strategy for LLM repository"""
    if environment == "production":
        try:
            return OpenAIRepository()
        except Exception as e:
            print(f"Warning: Failed to create OpenAIRepository: {e}")
            print("Falling back to MockLLMRepository")
            return MockLLMRepository()
    else:
        return MockLLMRepository()


def _create_jwt_repository(environment: str) -> JWTRepository:
    """Factory function with fallback strategy for JWT repository"""
    if environment == "production":
        try:
            return ProductionJWTRepository()
        except Exception as e:
            print(f"Warning: Failed to create ProductionJWTRepository: {e}")
            print("Falling back to MockJWTRepository")
            return MockJWTRepository()
    else:
        return MockJWTRepository()


# Global container instance
container = ApplicationContainer()


# Dependency injection helpers
def get_ask_service() -> AskOrchestrationService:
    """Helper function for FastAPI dependency injection"""
    return container.ask_orchestration_service()


def get_chat_service() -> ChatOrchestrationService:
    """Helper function for FastAPI dependency injection"""
    return container.chat_orchestration_service()


def get_authentication_service() -> AuthenticationService:
    """Helper function for FastAPI dependency injection"""
    return container.authentication_service()
