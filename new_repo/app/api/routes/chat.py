"""
Chat API Routes - Thin HTTP layer following SOLID principles
Single Responsibility: Handle HTTP requests and delegate to business services
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.orchestrators.chat_orchestrator import chat_orchestrator
from app.api.dependencies.auth import RequireAuth

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    auth_claims: Dict[str, Any] = RequireAuth,
):
    """
    Chat endpoint - Clean, focused HTTP handler

    Single Responsibility:
    - Receive HTTP request
    - Delegate to orchestrator service
    - Return HTTP response

    Business logic is handled by ChatOrchestrator and its dependencies
    """
    try:
        logger.info(
            f"Chat request: {len(request.messages)} messages, "
            f"session_state: {request.session_state}, stream: {request.stream}"
        )

        # Delegate all processing to orchestrator - it returns unified StreamingResponse
        result = await chat_orchestrator.process_chat_request(
            request=request, auth_claims=auth_claims
        )

        return result

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as error:
        logger.exception(f"Chat endpoint error: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"The app encountered an error processing your request. Error type: {type(error).__name__}",
        )
