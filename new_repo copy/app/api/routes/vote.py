"""Vote API routes following the orchestrator pattern"""

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import get_current_user
from app.models.document import MessageDocument, MessageVoteRequest
from app.orchestrators.vote_orchestrator import vote_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/vote")
async def vote_on_message(
    request: MessageVoteRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> MessageDocument:
    """Vote on a specific message"""
    try:
        return await vote_orchestrator.process_vote(request, current_user)
    except Exception as error:
        logger.error(f"Vote endpoint error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


@router.delete("/vote/{message_id}")
async def remove_vote(
    message_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> MessageDocument:
    """Remove a vote from a message"""
    try:
        return await vote_orchestrator.remove_vote(message_id, current_user)
    except Exception as error:
        logger.error(f"Remove vote endpoint error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/message/{message_id}")
async def get_message_with_vote(
    message_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> MessageDocument:
    """Get a specific message with its vote information"""
    try:
        return await vote_orchestrator.get_message_with_vote(message_id, current_user)
    except Exception as error:
        logger.error(f"Get message endpoint error: {error}")
        raise HTTPException(status_code=500, detail=str(error))
