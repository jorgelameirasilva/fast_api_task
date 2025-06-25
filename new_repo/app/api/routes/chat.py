"""
Chat API Routes - Thin HTTP layer following SOLID principles
Single Responsibility: Handle HTTP requests and delegate to business services
"""

import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies.auth import get_current_user
from app.schemas.chat import ChatRequest
from app.orchestrators.chat_orchestrator import chat_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Chat endpoint - Just call orchestrator like old design
    """
    try:
        # Just call orchestrator and return result
        return await chat_orchestrator.process_chat_request(request, current_user)
    except Exception as error:
        logger.error(f"Chat endpoint error: {error}")
        raise HTTPException(status_code=500, detail=str(error))
