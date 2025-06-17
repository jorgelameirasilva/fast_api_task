"""
Chat API Routes - Thin HTTP layer following SOLID principles
Single Responsibility: Handle HTTP requests and delegate to business services
"""

import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.orchestrators.chat_orchestrator import chat_orchestrator
from app.api.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """
    Process a chat request and return a streaming response.

    This endpoint always returns a streaming response for consistency,
    even when stream=False in the request.
    """
    try:
        logger.info(
            f"Chat request received from user: {current_user.get('oid', 'unknown')}"
        )

        # Process the chat request through the orchestrator
        response = await chat_orchestrator.process_chat_request(request, current_user)

        return response

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"The app encountered an error processing your request. Error type: {type(e).__name__}",
        )
