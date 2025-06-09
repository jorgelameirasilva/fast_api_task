"""
Chat API Endpoints V2 - Using improved architecture with dependency injection.
This demonstrates the new clean architecture approach.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from typing import AsyncGenerator

from app.schemas.chat import AskRequest, AskResponse, ChatRequest, ChatResponse
from app.services.ask_orchestration_service import AskOrchestrationService
from app.services.chat_orchestration_service import ChatOrchestrationService
from app.core.container import (
    get_ask_orchestrator,
    get_chat_orchestrator,
    check_search_health,
    check_llm_health,
)

router = APIRouter(prefix="/v2", tags=["Chat V2"])


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    orchestrator: AskOrchestrationService = Depends(get_ask_orchestrator),
) -> AskResponse:
    """
    Ask a question and get an answer using the improved architecture.

    This endpoint demonstrates:
    - Proper dependency injection
    - Clean separation of concerns
    - Repository pattern for data access
    - Service layer for business logic
    """
    logger.info(f"V2 Ask request: {request.user_query[:50]}...")

    try:
        response = await orchestrator.process_ask_request(request, stream=False)
        logger.info("V2 Ask request processed successfully")
        return response

    except Exception as e:
        logger.error(f"Error processing V2 ask request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process ask request: {str(e)}",
        )


@router.post("/ask/stream")
async def ask_question_stream(
    request: AskRequest,
    orchestrator: AskOrchestrationService = Depends(get_ask_orchestrator),
) -> StreamingResponse:
    """
    Ask a question and get a streaming response.

    This shows how streaming can be implemented with the new architecture.
    """
    logger.info(f"V2 Streaming ask request: {request.user_query[:50]}...")

    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # For now, return the full response as a single chunk
            # This can be enhanced to true streaming later
            response = await orchestrator.process_ask_request(request, stream=True)

            # Format as SSE (Server-Sent Events)
            yield f"data: {response.chatbot_response}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in streaming ask: {e}")
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_conversation(
    request: ChatRequest,
    orchestrator: ChatOrchestrationService = Depends(get_chat_orchestrator),
) -> ChatResponse:
    """
    Continue a chat conversation using the improved architecture.

    This endpoint demonstrates:
    - Conversation history management
    - Context-aware responses
    - Session handling
    """
    logger.info(f"V2 Chat request with {len(request.messages)} messages")

    try:
        response = await orchestrator.process_chat_request(request, stream=False)
        logger.info("V2 Chat request processed successfully")
        return response

    except Exception as e:
        logger.error(f"Error processing V2 chat request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}",
        )


@router.post("/chat/stream")
async def chat_conversation_stream(
    request: ChatRequest,
    orchestrator: ChatOrchestrationService = Depends(get_chat_orchestrator),
) -> StreamingResponse:
    """
    Continue a chat conversation with streaming response.
    """
    logger.info(f"V2 Streaming chat request with {len(request.messages)} messages")

    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            response = await orchestrator.process_chat_request(request, stream=True)

            # Format as SSE (Server-Sent Events)
            yield f"data: {response.message.content}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in streaming chat: {e}")
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint that verifies all services are working.
    """
    try:
        # Check repository health using container functions
        search_health = await check_search_health()
        llm_health = await check_llm_health()

        overall_status = "healthy" if search_health and llm_health else "degraded"

        return {
            "status": overall_status,
            "services": {
                "search_repository": "healthy" if search_health else "unhealthy",
                "llm_repository": "healthy" if llm_health else "unhealthy",
            },
            "architecture": "v2_clean_architecture",
            "endpoints": {
                "ask": "/v2/ask",
                "ask_stream": "/v2/ask/stream",
                "chat": "/v2/chat",
                "chat_stream": "/v2/chat/stream",
                "health": "/v2/health",
                "architecture_info": "/v2/architecture/info",
            },
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service health check failed",
        )


@router.get("/architecture/info")
async def architecture_info() -> dict:
    """
    Return information about the current architecture.
    """
    return {
        "version": "2.0",
        "architecture_pattern": "Clean Architecture with DDD",
        "design_patterns": [
            "Repository Pattern",
            "Dependency Injection",
            "Service Layer",
            "Domain Driven Design",
            "Factory Pattern",
            "Strategy Pattern",
        ],
        "layers": {
            "presentation": "FastAPI Routers",
            "application": "Orchestration Services",
            "domain": "Domain Services (Query Processing, Response Generation)",
            "infrastructure": "Repositories (Search, LLM)",
        },
        "benefits": [
            "Testable - Easy to mock dependencies",
            "Maintainable - Clear separation of concerns",
            "Extensible - Easy to add new implementations",
            "Production Ready - Proper error handling and logging",
            "Performant - Lazy loading and connection pooling",
            "Configurable - Environment-specific implementations",
        ],
        "repositories": {
            "search_repository": {
                "interface": "SearchRepository",
                "implementations": ["AzureSearchRepository", "MockSearchRepository"],
                "fallback": "MockSearchRepository",
            },
            "llm_repository": {
                "interface": "LLMRepository",
                "implementations": ["OpenAIRepository", "MockLLMRepository"],
                "fallback": "MockLLMRepository",
            },
        },
        "services": {
            "domain_services": ["QueryProcessingService", "ResponseGenerationService"],
            "orchestration_services": [
                "AskOrchestrationService",
                "ChatOrchestrationService",
            ],
        },
    }


@router.get("/metrics")
async def get_metrics() -> dict:
    """
    Get application metrics and performance information.
    """
    try:
        # Basic metrics - can be extended with proper monitoring
        search_health = await check_search_health()
        llm_health = await check_llm_health()

        return {
            "health_status": {
                "search_repository": search_health,
                "llm_repository": llm_health,
                "overall": search_health and llm_health,
            },
            "architecture": {
                "version": "2.0",
                "pattern": "clean_architecture",
                "dependency_injection": True,
                "repository_pattern": True,
            },
            "endpoints": {
                "total_endpoints": 7,
                "v2_endpoints": 7,
                "streaming_endpoints": 2,
                "health_endpoints": 1,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )
