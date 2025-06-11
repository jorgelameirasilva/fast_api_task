from fastapi import APIRouter, status, HTTPException, Query, Depends
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

# Import services
from app.services.ask_service import ask_service
from app.services.vote_service import vote_service
from app.services.auth_service import auth_service

# Import dependencies
from app.core.dependencies import get_chat_service
from app.auth import get_current_user, AuthUser
from app.core.config import settings

# Clean router - auth applied per endpoint where needed
router = APIRouter()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    request: ChatRequest,
    current_user: AuthUser = Depends(get_current_user),  # Auth + user object
    stream: bool = Query(False, description="Whether to stream the response"),
):
    """
    Handle chat conversations using approaches
    Requires JWT authentication
    """
    logger.info(f"Chat endpoint called by user: {current_user.user_id}")

    try:
        # Validate request
        if not request.messages:
            raise ValueError("Request must contain messages")

        # Get chat service and process request
        chat_service = get_chat_service()
        response = await chat_service.process_chat(
            request=request, stream=stream, current_user=current_user
        )

        logger.info(f"Chat processed successfully for user: {current_user.user_id}")
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
    current_user: AuthUser = Depends(get_current_user),  # Auth + user object
    stream: bool = Query(False, description="Whether to stream the response"),
):
    """
    Handle user queries using approaches
    Requires JWT authentication
    """
    logger.info(f"Ask endpoint called by user: {current_user.user_id}")

    try:
        # Validate request
        if not request.user_query or not request.user_query.strip():
            raise ValueError("User query cannot be empty")

        # Process using the approach system
        response = await ask_service.process_ask(request, stream=stream)

        logger.info(f"Ask processed successfully for user: {current_user.user_id}")
        return response

    except ValueError as e:
        logger.error(f"Ask validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ask processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/vote", response_model=VoteResponse, status_code=status.HTTP_200_OK)
async def vote(
    request: VoteRequest,
    current_user: AuthUser = Depends(get_current_user),  # Auth + user object
):
    """
    Handle user feedback/voting on responses
    Requires JWT authentication
    """
    logger.info(f"Vote endpoint called by user: {current_user.user_id}")
    try:
        response = await vote_service.process_vote(request)
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
    Public endpoint - no authentication required
    """
    logger.info("Auth setup endpoint called")
    try:
        response = await auth_service.get_auth_setup()
        return response
    except Exception as e:
        logger.error(f"Auth setup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
