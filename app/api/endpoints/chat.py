from fastapi import APIRouter, status, HTTPException
from loguru import logger

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
async def chat(request: ChatRequest):
    """
    Handle chat conversations
    """
    logger.info("Chat endpoint called")
    try:
        response = await chat_service.process_chat(request)
        return response
    except ValueError as e:
        logger.error(f"Chat validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
async def ask(request: AskRequest):
    """
    Handle user queries and return responses
    """
    logger.info(f"Ask endpoint called with query: {request.user_query[:50]}...")
    try:
        response = await chat_service.process_ask(request)
        return response
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
