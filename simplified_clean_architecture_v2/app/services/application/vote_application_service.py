"""
Vote Application Service - Coordinates voting workflow
"""

import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from app.auth.dependencies import AuthUser
from app.services.domain.vote_domain_service import (
    VoteDomainService,
    Vote,
    VoteType,
    VoteStats,
    VoteSummary,
)


@dataclass
class VoteRequest:
    """Vote request DTO"""

    message_id: str
    session_id: str
    vote_type: str  # "thumbs_up" or "thumbs_down"
    feedback: Optional[str] = None


@dataclass
class VoteResponse:
    """Vote response DTO"""

    vote_id: str
    message_id: str
    vote_type: str
    feedback: Optional[str]
    timestamp: datetime
    success: bool = True


@dataclass
class VoteUpdateRequest:
    """Vote update request DTO"""

    vote_id: str
    vote_type: Optional[str] = None
    feedback: Optional[str] = None


class VoteApplicationService:
    """Application service that coordinates voting workflow"""

    def __init__(self):
        # Initialize domain service
        self.vote_domain = VoteDomainService()

        # In-memory storage (replace with actual database in production)
        self.votes: Dict[str, Vote] = {}

    async def submit_vote(self, request: VoteRequest, user: AuthUser) -> VoteResponse:
        """Submit a new vote"""

        try:
            logger.info(f"Processing vote submission for user {user.user_id}")

            # Validate vote data
            is_valid, error_msg = self.vote_domain.validate_vote(
                request.vote_type, request.feedback
            )
            if not is_valid:
                raise ValueError(error_msg)

            # Check if user can vote on this message
            existing_votes = list(self.votes.values())
            can_vote, error_msg = self.vote_domain.can_user_vote(
                user.user_id, request.message_id, existing_votes
            )
            if not can_vote:
                raise ValueError(error_msg)

            # Create vote
            vote_id = str(uuid.uuid4())
            vote = self.vote_domain.create_vote(
                vote_id=vote_id,
                user_id=user.user_id,
                message_id=request.message_id,
                session_id=request.session_id,
                vote_type=request.vote_type,
                feedback=request.feedback,
            )

            # Store vote
            self.votes[vote_id] = vote

            logger.info(f"Vote {vote_id} submitted successfully by user {user.user_id}")

            return VoteResponse(
                vote_id=vote_id,
                message_id=request.message_id,
                vote_type=request.vote_type,
                feedback=request.feedback,
                timestamp=vote.timestamp,
                success=True,
            )

        except Exception as e:
            logger.error(f"Error submitting vote: {e}")
            raise

    async def update_vote(
        self, request: VoteUpdateRequest, user: AuthUser
    ) -> VoteResponse:
        """Update an existing vote"""

        try:
            logger.info(f"Processing vote update for user {user.user_id}")

            # Validate new vote data if provided
            if request.vote_type:
                is_valid, error_msg = self.vote_domain.validate_vote(
                    request.vote_type, request.feedback
                )
                if not is_valid:
                    raise ValueError(error_msg)

            # Check if user can update this vote
            existing_votes = list(self.votes.values())
            can_update, error_msg, original_vote = (
                self.vote_domain.can_user_update_vote(
                    user.user_id, request.vote_id, existing_votes
                )
            )
            if not can_update:
                raise ValueError(error_msg)

            # Update vote
            updated_vote = self.vote_domain.update_vote(
                original_vote,
                new_vote_type=request.vote_type,
                new_feedback=request.feedback,
            )

            # Store updated vote
            self.votes[request.vote_id] = updated_vote

            logger.info(
                f"Vote {request.vote_id} updated successfully by user {user.user_id}"
            )

            return VoteResponse(
                vote_id=request.vote_id,
                message_id=updated_vote.message_id,
                vote_type=updated_vote.vote_type.value,
                feedback=updated_vote.feedback,
                timestamp=updated_vote.timestamp,
                success=True,
            )

        except Exception as e:
            logger.error(f"Error updating vote: {e}")
            raise

    async def get_vote_summary(self, message_id: str, user: AuthUser) -> Dict:
        """Get vote summary for a message"""

        try:
            # Get vote summary
            all_votes = list(self.votes.values())
            summary = self.vote_domain.get_vote_summary(
                message_id, all_votes, user.user_id
            )

            # Format response
            return {
                "message_id": message_id,
                "stats": {
                    "total_votes": summary.stats.total_votes,
                    "thumbs_up_count": summary.stats.thumbs_up_count,
                    "thumbs_down_count": summary.stats.thumbs_down_count,
                    "satisfaction_rate": summary.stats.satisfaction_rate,
                    "common_feedback_themes": summary.stats.common_feedback_themes,
                },
                "user_vote": (
                    {
                        "vote_id": summary.user_vote.id,
                        "vote_type": summary.user_vote.vote_type.value,
                        "feedback": summary.user_vote.feedback,
                        "timestamp": summary.user_vote.timestamp.isoformat(),
                    }
                    if summary.user_vote
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error getting vote summary: {e}")
            raise

    async def get_user_votes(self, user: AuthUser, limit: int = 50) -> List[Dict]:
        """Get all votes by a user"""

        try:
            # Filter user votes
            user_votes = [
                vote for vote in self.votes.values() if vote.user_id == user.user_id
            ]

            # Sort by timestamp (most recent first)
            user_votes.sort(key=lambda v: v.timestamp, reverse=True)

            # Limit results
            user_votes = user_votes[:limit]

            # Format response
            formatted_votes = []
            for vote in user_votes:
                formatted_votes.append(
                    {
                        "vote_id": vote.id,
                        "message_id": vote.message_id,
                        "session_id": vote.session_id,
                        "vote_type": vote.vote_type.value,
                        "feedback": vote.feedback,
                        "timestamp": vote.timestamp.isoformat(),
                    }
                )

            return formatted_votes

        except Exception as e:
            logger.error(f"Error getting user votes: {e}")
            raise

    async def get_session_votes(self, session_id: str, user: AuthUser) -> Dict:
        """Get all votes for a session"""

        try:
            # Filter session votes
            session_votes = [
                vote for vote in self.votes.values() if vote.session_id == session_id
            ]

            # Calculate overall session stats
            stats = self.vote_domain.calculate_vote_stats(session_votes)

            # Group votes by message
            votes_by_message = {}
            for vote in session_votes:
                if vote.message_id not in votes_by_message:
                    votes_by_message[vote.message_id] = []
                votes_by_message[vote.message_id].append(
                    {
                        "vote_id": vote.id,
                        "user_id": (
                            vote.user_id
                            if vote.user_id == user.user_id
                            else "anonymous"
                        ),
                        "vote_type": vote.vote_type.value,
                        "feedback": (
                            vote.feedback if vote.user_id == user.user_id else None
                        ),
                        "timestamp": vote.timestamp.isoformat(),
                    }
                )

            return {
                "session_id": session_id,
                "overall_stats": {
                    "total_votes": stats.total_votes,
                    "thumbs_up_count": stats.thumbs_up_count,
                    "thumbs_down_count": stats.thumbs_down_count,
                    "satisfaction_rate": stats.satisfaction_rate,
                    "common_feedback_themes": stats.common_feedback_themes,
                },
                "votes_by_message": votes_by_message,
            }

        except Exception as e:
            logger.error(f"Error getting session votes: {e}")
            raise

    async def delete_vote(self, vote_id: str, user: AuthUser) -> bool:
        """Delete a vote"""

        try:
            vote = self.votes.get(vote_id)
            if not vote:
                return False

            # Check if user owns the vote
            if vote.user_id != user.user_id:
                raise PermissionError("User can only delete their own votes")

            # Delete vote
            del self.votes[vote_id]
            logger.info(f"Deleted vote {vote_id} by user {user.user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting vote: {e}")
            raise

    async def get_voting_analytics(self, user: AuthUser) -> Dict:
        """Get voting analytics for a user"""

        try:
            all_votes = list(self.votes.values())

            # Get user voting pattern
            user_pattern = self.vote_domain.get_user_voting_pattern(
                user.user_id, all_votes
            )

            # Get recent votes
            user_votes = [v for v in all_votes if v.user_id == user.user_id]
            recent_votes = sorted(user_votes, key=lambda v: v.timestamp, reverse=True)[
                :10
            ]

            # Calculate feedback quality (simple metric)
            feedback_votes = [v for v in user_votes if v.feedback]
            avg_feedback_length = (
                sum(len(v.feedback) for v in feedback_votes) / len(feedback_votes)
                if feedback_votes
                else 0
            )

            return {
                "user_id": user.user_id,
                "voting_pattern": user_pattern,
                "recent_activity": {
                    "recent_votes_count": len(recent_votes),
                    "avg_feedback_length": avg_feedback_length,
                    "last_vote_timestamp": (
                        recent_votes[0].timestamp.isoformat() if recent_votes else None
                    ),
                },
                "engagement_metrics": {
                    "feedback_engagement": user_pattern["provides_feedback_ratio"],
                    "positive_sentiment": user_pattern["thumbs_up_ratio"],
                    "overall_activity": (
                        "high"
                        if user_pattern["total_votes"] > 20
                        else "medium" if user_pattern["total_votes"] > 5 else "low"
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error getting voting analytics: {e}")
            raise
