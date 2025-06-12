"""
V2 API Endpoints with Clean Architecture and Dependency Injection
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from datetime import datetime

from app.models.dto import (
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
)
from app.services.orchestration.ask_orchestration_service import AskOrchestrationService
from app.services.orchestration.chat_orchestration_service import (
    ChatOrchestrationService,
)
from app.core.container import get_ask_service, get_chat_service
from app.auth.dependencies import (
    get_current_user,
    get_optional_user,
    get_auth_context,
    require_roles,
    require_scope,
    with_auth_context,
)
from app.auth.models import AuthUser, AuthContext
from app import __version__

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v2", tags=["V2 Endpoints"])


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    ask_service: AskOrchestrationService = Depends(get_ask_service),
    auth_context: AuthContext = Depends(with_auth_context()),
) -> AskResponse:
    """
    Ask a question and get an AI-generated response with sources

    This endpoint uses Clean Architecture with:
    - Dependency injection for service resolution
    - Repository pattern for external service abstraction
    - Domain services for business logic
    - Orchestration services for workflow coordination
    """
    try:
        logger.info(
            f"Ask request received: {request.query[:50]}... (user: {auth_context.user.user_id if auth_context.is_authenticated else 'anonymous'})"
        )

        # Build context with user information
        enhanced_context = request.context or {}
        if auth_context.is_authenticated:
            enhanced_context.update(
                {
                    "user_id": auth_context.user.user_id,
                    "user_roles": auth_context.user.roles,
                    "user_scopes": (
                        auth_context.user.scope.split()
                        if auth_context.user.scope
                        else []
                    ),
                }
            )

        # Delegate to orchestration service
        result = await ask_service.process_ask(
            query=request.query,
            context=enhanced_context,
            max_results=request.max_results,
        )

        # Handle error case
        if "error" in result:
            logger.error(f"Ask service error: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal processing error",
            )

        # Return successful response
        return AskResponse(
            answer=result["answer"],
            sources=result["sources"],
            confidence=result.get("confidence"),
            processing_time_ms=result.get("processing_time_ms"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ask endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process question",
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    chat_service: ChatOrchestrationService = Depends(get_chat_service),
    auth_context: AuthContext = Depends(with_auth_context()),
) -> ChatResponse:
    """
    Send a chat message and get a conversational response

    Features:
    - Conversation context management
    - Search-enhanced responses
    - Persistent conversation history
    """
    try:
        logger.info(
            f"Chat request received for conversation: {request.conversation_id} (user: {auth_context.user.user_id if auth_context.is_authenticated else 'anonymous'})"
        )

        # Convert history to the expected format
        history = None
        if request.history:
            history = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                }
                for msg in request.history
            ]

        # Delegate to orchestration service
        result = await chat_service.process_chat(
            message=request.message,
            conversation_id=request.conversation_id,
            history=history,
        )

        # Handle error case
        if "error" in result:
            logger.error(f"Chat service error: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal processing error",
            )

        # Return successful response
        return ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            sources=result["sources"],
            processing_time_ms=result.get("processing_time_ms"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message",
        )


@router.get("/chat/{conversation_id}/history")
async def get_chat_history(
    conversation_id: str,
    chat_service: ChatOrchestrationService = Depends(get_chat_service),
) -> Dict[str, Any]:
    """Get conversation history for a given conversation ID"""
    try:
        history = await chat_service.get_conversation_history(conversation_id)
        return {
            "conversation_id": conversation_id,
            "history": history,
            "message_count": len(history),
        }
    except Exception as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation history",
        )


@router.delete("/chat/{conversation_id}")
async def clear_chat_history(
    conversation_id: str,
    chat_service: ChatOrchestrationService = Depends(get_chat_service),
) -> Dict[str, Any]:
    """Clear conversation history for a given conversation ID"""
    try:
        success = await chat_service.clear_conversation(conversation_id)
        return {
            "conversation_id": conversation_id,
            "cleared": success,
            "message": (
                "Conversation cleared successfully"
                if success
                else "Conversation not found"
            ),
        }
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear conversation history",
        )


@router.get("/health", response_model=HealthResponse)
async def health_check(
    ask_service: AskOrchestrationService = Depends(get_ask_service),
    chat_service: ChatOrchestrationService = Depends(get_chat_service),
) -> HealthResponse:
    """
    Comprehensive health check for all services

    Checks:
    - Ask orchestration service
    - Chat orchestration service
    - All underlying repositories and domain services
    """
    try:
        # Check all services
        ask_health = await ask_service.health_check()
        chat_health = await chat_service.health_check()

        # Determine overall status
        overall_status = "healthy"
        if ask_health.get("status") not in ["healthy"] or chat_health.get(
            "status"
        ) not in ["healthy"]:
            overall_status = "degraded"

        dependencies = {
            "ask_service": ask_health.get("status", "unknown"),
            "chat_service": chat_health.get("status", "unknown"),
        }

        # Add detailed dependency status
        if "dependencies" in ask_health:
            dependencies.update(
                {f"ask_{k}": v for k, v in ask_health["dependencies"].items()}
            )

        if "dependencies" in chat_health:
            dependencies.update(
                {f"chat_{k}": v for k, v in chat_health["dependencies"].items()}
            )

        return HealthResponse(
            status=overall_status,
            version=__version__,
            timestamp=datetime.now(),
            dependencies=dependencies,
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            status="unhealthy",
            version=__version__,
            timestamp=datetime.now(),
            dependencies={"error": str(e)},
        )


@router.get("/info")
async def api_info() -> Dict[str, Any]:
    """Get API information and architecture details"""
    return {
        "api_version": "v2",
        "app_version": __version__,
        "architecture": "Clean Architecture with Dependency Injection",
        "features": [
            "Repository Pattern for external services",
            "Domain Services for business logic",
            "Orchestration Services for workflow coordination",
            "Smart fallback strategy for service availability",
            "Comprehensive health monitoring",
            "Conversation context management",
            "JWT Authentication with RBAC",
            "Mock authentication for development",
        ],
        "endpoints": {
            "ask": "POST /v2/ask - Question answering with sources (optional auth)",
            "chat": "POST /v2/chat - Conversational chat interface (optional auth)",
            "chat_history": "GET /v2/chat/{id}/history - Get conversation history",
            "clear_chat": "DELETE /v2/chat/{id} - Clear conversation",
            "profile": "GET /v2/profile - User profile (requires auth)",
            "admin": "GET /v2/admin/stats - Admin statistics (requires admin role)",
            "health": "GET /v2/health - Service health check",
            "info": "GET /v2/info - API information",
            "auth_info": "GET /v2/auth/info - Authentication information",
        },
    }


@router.get("/profile")
async def get_user_profile(
    current_user: AuthUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get authenticated user profile

    Requires: Authentication
    """
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "name": current_user.name,
        "username": current_user.preferred_username,
        "roles": current_user.roles,
        "groups": current_user.groups,
        "scopes": current_user.scope.split() if current_user.scope else [],
        "issued_at": current_user.issued_at,
        "expires_at": current_user.expires_at,
    }


@router.get("/admin/stats", dependencies=[Depends(require_roles(["admin"]))])
async def get_admin_stats(
    ask_service: AskOrchestrationService = Depends(get_ask_service),
    chat_service: ChatOrchestrationService = Depends(get_chat_service),
    current_user: AuthUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get administrative statistics

    Requires: admin role
    """
    # Get service health information
    ask_health = await ask_service.health_check()
    chat_health = await chat_service.health_check()

    return {
        "accessed_by": {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "roles": current_user.roles,
        },
        "services": {"ask_service": ask_health, "chat_service": chat_health},
        "conversation_stats": {
            "active_conversations": chat_health.get("active_conversations", 0)
        },
    }


@router.get("/auth/info")
async def get_auth_info(
    auth_context: AuthContext = Depends(with_auth_context()),
) -> Dict[str, Any]:
    """
    Get authentication information for current request

    Works with or without authentication
    """
    if auth_context.is_authenticated:
        return {
            "authenticated": True,
            "user": {
                "user_id": auth_context.user.user_id,
                "email": auth_context.user.email,
                "roles": auth_context.user.roles,
                "scopes": (
                    auth_context.user.scope.split() if auth_context.user.scope else []
                ),
            },
            "auth_method": auth_context.auth_method,
            "request_id": auth_context.request_id,
        }
    else:
        return {
            "authenticated": False,
            "user": None,
            "auth_method": None,
            "request_id": auth_context.request_id,
            "mock_tokens": {
                "admin": "mock-token-admin",
                "user": "mock-token-user",
                "readonly": "mock-token-readonly",
            },
        }
