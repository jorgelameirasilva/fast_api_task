from fastapi import APIRouter, status, HTTPException, Query
from loguru import logger
from typing import Optional

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    AskRequest,
    AskResponse,
    VoteRequest,
    VoteResponse,
    AuthSetupResponse,
)
from app.services.chat_service import chat_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    request: ChatRequest,
    approach: Optional[str] = Query(
        None,
        description="Specific approach to use (e.g., 'retrieve_then_read', 'chat_read_retrieve_read')",
    ),
    stream: bool = Query(False, description="Whether to stream the response"),
):
    """
    Handle chat conversations using the approaches system
    """
    logger.info("Chat endpoint called")
    if approach:
        logger.info(f"Using explicit approach for chat: {approach}")

    try:
        response = await chat_service.process_chat(
            request=request, approach_name=approach, stream=stream
        )
        return response
    except ValueError as e:
        logger.error(f"Chat validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
async def ask(
    request: AskRequest,
    approach: Optional[str] = Query(
        None,
        description="Specific approach to use (e.g., 'retrieve_then_read', 'chat_read_retrieve_read')",
    ),
    stream: bool = Query(False, description="Whether to stream the response"),
):
    """
    Handle user queries and return responses using the approaches system
    """
    logger.info(f"Ask endpoint called with query: {request.user_query[:50]}...")
    if approach:
        logger.info(f"Using explicit approach: {approach}")

    try:
        if approach:
            # Use specific approach if requested
            response = await chat_service.process_ask_with_approach(
                request=request, approach_name=approach, stream=stream
            )
        else:
            # Use automatic approach selection with streaming support
            response = await chat_service.process_ask(request, stream=stream)

        return response
    except ValueError as e:
        logger.error(f"Ask validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ask processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/vote", response_model=VoteResponse, status_code=status.HTTP_200_OK)
async def vote(request: VoteRequest):
    """
    Handle user feedback/voting on responses
    """
    logger.info(f"Vote endpoint called: upvote={request.upvote}")
    try:
        response = await chat_service.process_vote(request)
        return response
    except ValueError as e:
        logger.error(f"Vote validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Vote processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/auth_setup", response_model=AuthSetupResponse, status_code=status.HTTP_200_OK
)
async def auth_setup():
    """
    Get authentication setup configuration
    """
    logger.info("Auth setup endpoint called")
    try:
        response = await chat_service.get_auth_setup()
        return response
    except Exception as e:
        logger.error(f"Auth setup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
