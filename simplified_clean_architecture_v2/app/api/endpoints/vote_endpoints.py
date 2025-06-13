"""
Vote API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Optional
from loguru import logger

from app.auth.dependencies import get_current_user, AuthUser
from app.services.application.vote_application_service import (
    VoteApplicationService,
    VoteRequest,
    VoteResponse,
    VoteUpdateRequest,
)


router = APIRouter()

# Initialize application service
vote_service = VoteApplicationService()


@router.post("/submit", response_model=Dict)
async def submit_vote(
    message_id: str,
    session_id: str,
    vote_type: str,
    feedback: Optional[str] = None,
    current_user: AuthUser = Depends(get_current_user),
):
    """Submit a vote for a message"""

    try:
        request = VoteRequest(
            message_id=message_id,
            session_id=session_id,
            vote_type=vote_type,
            feedback=feedback,
        )

        response = await vote_service.submit_vote(request, current_user)

        return {
            "success": True,
            "data": {
                "vote_id": response.vote_id,
                "message_id": response.message_id,
                "vote_type": response.vote_type,
                "feedback": response.feedback,
                "timestamp": response.timestamp.isoformat(),
            },
            "message": "Vote submitted successfully",
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting vote: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/update/{vote_id}", response_model=Dict)
async def update_vote(
    vote_id: str,
    vote_type: Optional[str] = None,
    feedback: Optional[str] = None,
    current_user: AuthUser = Depends(get_current_user),
):
    """Update an existing vote"""

    try:
        request = VoteUpdateRequest(
            vote_id=vote_id, vote_type=vote_type, feedback=feedback
        )

        response = await vote_service.update_vote(request, current_user)

        return {
            "success": True,
            "data": {
                "vote_id": response.vote_id,
                "message_id": response.message_id,
                "vote_type": response.vote_type,
                "feedback": response.feedback,
                "timestamp": response.timestamp.isoformat(),
            },
            "message": "Vote updated successfully",
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating vote: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/message/{message_id}/summary", response_model=Dict)
async def get_message_vote_summary(
    message_id: str, current_user: AuthUser = Depends(get_current_user)
):
    """Get vote summary for a specific message"""

    try:
        summary = await vote_service.get_vote_summary(message_id, current_user)

        return {"success": True, "data": summary}

    except Exception as e:
        logger.error(f"Error getting vote summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/user/votes", response_model=Dict)
async def get_user_votes(
    limit: int = 50, current_user: AuthUser = Depends(get_current_user)
):
    """Get all votes by the current user"""

    try:
        votes = await vote_service.get_user_votes(current_user, limit)

        return {"success": True, "data": {"votes": votes, "count": len(votes)}}

    except Exception as e:
        logger.error(f"Error getting user votes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/session/{session_id}/votes", response_model=Dict)
async def get_session_votes(
    session_id: str, current_user: AuthUser = Depends(get_current_user)
):
    """Get all votes for a specific session"""

    try:
        votes = await vote_service.get_session_votes(session_id, current_user)

        return {"success": True, "data": votes}

    except Exception as e:
        logger.error(f"Error getting session votes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/{vote_id}", response_model=Dict)
async def delete_vote(vote_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Delete a vote"""

    try:
        success = await vote_service.delete_vote(vote_id, current_user)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Vote not found"
            )

        return {"success": True, "message": "Vote deleted successfully"}

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting vote: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/user/analytics", response_model=Dict)
async def get_voting_analytics(current_user: AuthUser = Depends(get_current_user)):
    """Get voting analytics for the current user"""

    try:
        analytics = await vote_service.get_voting_analytics(current_user)

        return {"success": True, "data": analytics}

    except Exception as e:
        logger.error(f"Error getting voting analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/health", response_model=Dict)
async def vote_health_check():
    """Health check for vote service"""

    try:
        # Basic health check
        return {
            "service": "vote",
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
        }

    except Exception as e:
        logger.error(f"Vote health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vote service unhealthy",
        )
