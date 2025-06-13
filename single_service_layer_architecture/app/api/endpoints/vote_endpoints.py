"""
Vote API Endpoints - Single Service Layer Architecture
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from loguru import logger

from app.auth.dependencies import get_current_user, AuthUser
from app.services.vote_service import VoteService, VoteRequest, VoteUpdateRequest


# Create service instance (in production, use dependency injection)
vote_service = VoteService()

# Create router
router = APIRouter()


# Request/Response models
class SubmitVoteRequest(BaseModel):
    """Request model for submitting a vote"""

    message_id: str
    session_id: str
    vote_type: str  # "thumbs_up" or "thumbs_down"
    feedback: Optional[str] = None


class UpdateVoteRequest(BaseModel):
    """Request model for updating a vote"""

    vote_type: Optional[str] = None
    feedback: Optional[str] = None


class VoteResponse(BaseModel):
    """Response model for vote operations"""

    vote_id: str
    message_id: str
    vote_type: str
    feedback: Optional[str]
    timestamp: str
    success: bool = True


class VoteSummaryResponse(BaseModel):
    """Response model for vote summary"""

    message_id: str
    stats: Dict
    user_vote: Optional[Dict] = None


class UserVotesResponse(BaseModel):
    """Response model for user votes"""

    votes: List[Dict]


class SessionVotesResponse(BaseModel):
    """Response model for session votes"""

    session_id: str
    overall_stats: Dict
    votes_by_message: Dict


class VotingAnalyticsResponse(BaseModel):
    """Response model for voting analytics"""

    user_id: str
    voting_pattern: Dict
    recent_activity: Dict
    engagement_metrics: Dict


@router.post("/submit", response_model=VoteResponse)
async def submit_vote(
    request: SubmitVoteRequest, user: AuthUser = Depends(get_current_user)
):
    """
    Submit a new vote for a message
    """
    try:
        # Convert request to service format
        vote_request = VoteRequest(
            message_id=request.message_id,
            session_id=request.session_id,
            vote_type=request.vote_type,
            feedback=request.feedback,
        )

        # Call service directly
        response = await vote_service.submit_vote(vote_request, user)

        # Convert response to API format
        return VoteResponse(
            vote_id=response.vote_id,
            message_id=response.message_id,
            vote_type=response.vote_type,
            feedback=response.feedback,
            timestamp=response.timestamp.isoformat(),
            success=response.success,
        )

    except ValueError as e:
        logger.error(f"Validation error in submit_vote: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in submit_vote: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{vote_id}", response_model=VoteResponse)
async def update_vote(
    vote_id: str, request: UpdateVoteRequest, user: AuthUser = Depends(get_current_user)
):
    """
    Update an existing vote
    """
    try:
        # Convert request to service format
        update_request = VoteUpdateRequest(
            vote_id=vote_id, vote_type=request.vote_type, feedback=request.feedback
        )

        # Call service directly
        response = await vote_service.update_vote(update_request, user)

        # Convert response to API format
        return VoteResponse(
            vote_id=response.vote_id,
            message_id=response.message_id,
            vote_type=response.vote_type,
            feedback=response.feedback,
            timestamp=response.timestamp.isoformat(),
            success=response.success,
        )

    except ValueError as e:
        logger.error(f"Validation error in update_vote: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in update_vote: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/messages/{message_id}/summary", response_model=VoteSummaryResponse)
async def get_vote_summary(message_id: str, user: AuthUser = Depends(get_current_user)):
    """
    Get vote summary for a message
    """
    try:
        # Call service directly
        summary = await vote_service.get_vote_summary(message_id, user)

        return VoteSummaryResponse(
            message_id=summary["message_id"],
            stats=summary["stats"],
            user_vote=summary["user_vote"],
        )

    except Exception as e:
        logger.error(f"Error in get_vote_summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/my-votes", response_model=UserVotesResponse)
async def get_user_votes(limit: int = 50, user: AuthUser = Depends(get_current_user)):
    """
    Get all votes by the current user
    """
    try:
        # Call service directly
        votes = await vote_service.get_user_votes(user, limit)

        return UserVotesResponse(votes=votes)

    except Exception as e:
        logger.error(f"Error in get_user_votes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}", response_model=SessionVotesResponse)
async def get_session_votes(
    session_id: str, user: AuthUser = Depends(get_current_user)
):
    """
    Get all votes for a session
    """
    try:
        # Call service directly
        session_votes = await vote_service.get_session_votes(session_id, user)

        return SessionVotesResponse(
            session_id=session_votes["session_id"],
            overall_stats=session_votes["overall_stats"],
            votes_by_message=session_votes["votes_by_message"],
        )

    except Exception as e:
        logger.error(f"Error in get_session_votes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{vote_id}")
async def delete_vote(vote_id: str, user: AuthUser = Depends(get_current_user)):
    """
    Delete a vote
    """
    try:
        # Call service directly
        success = await vote_service.delete_vote(vote_id, user)

        if not success:
            raise HTTPException(status_code=404, detail="Vote not found")

        return {"message": "Vote deleted successfully", "vote_id": vote_id}

    except PermissionError as e:
        logger.error(f"Permission error in delete_vote: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error in delete_vote: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics", response_model=VotingAnalyticsResponse)
async def get_voting_analytics(user: AuthUser = Depends(get_current_user)):
    """
    Get voting analytics for the current user
    """
    try:
        # Call service directly
        analytics = await vote_service.get_voting_analytics(user)

        return VotingAnalyticsResponse(
            user_id=analytics["user_id"],
            voting_pattern=analytics["voting_pattern"],
            recent_activity=analytics["recent_activity"],
            engagement_metrics=analytics["engagement_metrics"],
        )

    except Exception as e:
        logger.error(f"Error in get_voting_analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def vote_health():
    """Health check for vote service"""
    try:
        # Simple health check
        return {
            "status": "healthy",
            "service": "vote",
            "architecture": "single_service_layer",
            "components": {"vote_service": "✅"},
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


@router.get("/test")
async def test_endpoint():
    """Test endpoint for development"""
    return {
        "message": "Vote service is working",
        "architecture": "single_service_layer",
        "description": "Simplest clean architecture with combined service layer",
    }
