"""
Vote Service - Single service combining coordination + business logic
"""

import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from loguru import logger

from app.auth.dependencies import AuthUser


class VoteType(Enum):
    """Vote types"""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


@dataclass
class Vote:
    """Vote model"""

    id: str
    user_id: str
    message_id: str
    session_id: str
    vote_type: VoteType
    feedback: Optional[str] = None
    timestamp: datetime = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class VoteStats:
    """Vote statistics"""

    total_votes: int
    thumbs_up_count: int
    thumbs_down_count: int
    satisfaction_rate: float
    common_feedback_themes: List[str]


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


class VoteService:
    """
    Single service handling both coordination and business logic for voting
    Combines what used to be Application Service + Domain Service
    """

    def __init__(self):
        # Business logic configuration
        self.max_feedback_length = 1000
        self.min_feedback_length = 5

        # In-memory storage (replace with actual database in production)
        self.votes: Dict[str, Vote] = {}

    # =============================================================================
    # PUBLIC API METHODS (called by endpoints)
    # =============================================================================

    async def submit_vote(self, request: VoteRequest, user: AuthUser) -> VoteResponse:
        """Submit a new vote"""

        try:
            logger.info(f"Processing vote submission for user {user.user_id}")

            # Validate vote data (business logic)
            self._validate_vote(request.vote_type, request.feedback)

            # Check if user can vote on this message (business logic)
            existing_votes = list(self.votes.values())
            self._check_can_user_vote(user.user_id, request.message_id, existing_votes)

            # Create vote (business logic + coordination)
            vote_id = str(uuid.uuid4())
            vote = self._create_vote(
                vote_id=vote_id,
                user_id=user.user_id,
                message_id=request.message_id,
                session_id=request.session_id,
                vote_type=request.vote_type,
                feedback=request.feedback,
            )

            # Store vote (coordination)
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

            # Validate new vote data if provided (business logic)
            if request.vote_type:
                self._validate_vote(request.vote_type, request.feedback)

            # Check if user can update this vote (business logic)
            existing_votes = list(self.votes.values())
            original_vote = self._check_can_user_update_vote(
                user.user_id, request.vote_id, existing_votes
            )

            # Update vote (business logic)
            updated_vote = self._update_vote(
                original_vote,
                new_vote_type=request.vote_type,
                new_feedback=request.feedback,
            )

            # Store updated vote (coordination)
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
            # Get vote summary (business logic + coordination)
            all_votes = list(self.votes.values())
            summary = self._get_vote_summary_for_message(
                message_id, all_votes, user.user_id
            )

            return summary

        except Exception as e:
            logger.error(f"Error getting vote summary: {e}")
            raise

    async def get_user_votes(self, user: AuthUser, limit: int = 50) -> List[Dict]:
        """Get all votes by a user"""

        try:
            # Filter user votes (coordination)
            user_votes = [
                vote for vote in self.votes.values() if vote.user_id == user.user_id
            ]

            # Sort by timestamp (business logic)
            user_votes.sort(key=lambda v: v.timestamp, reverse=True)

            # Limit results (business logic)
            user_votes = user_votes[:limit]

            # Format response (coordination)
            return self._format_votes_response(user_votes)

        except Exception as e:
            logger.error(f"Error getting user votes: {e}")
            raise

    async def get_session_votes(self, session_id: str, user: AuthUser) -> Dict:
        """Get all votes for a session"""

        try:
            # Filter session votes (coordination)
            session_votes = [
                vote for vote in self.votes.values() if vote.session_id == session_id
            ]

            # Calculate overall session stats (business logic)
            stats = self._calculate_vote_stats(session_votes)

            # Group votes by message (coordination)
            votes_by_message = self._group_votes_by_message(session_votes, user.user_id)

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

            # Check if user owns the vote (business logic)
            if vote.user_id != user.user_id:
                raise PermissionError("User can only delete their own votes")

            # Delete vote (coordination)
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

            # Get user voting pattern (business logic)
            user_pattern = self._get_user_voting_pattern(user.user_id, all_votes)

            # Get recent votes (coordination)
            user_votes = [v for v in all_votes if v.user_id == user.user_id]
            recent_votes = sorted(user_votes, key=lambda v: v.timestamp, reverse=True)[
                :10
            ]

            # Calculate feedback quality (business logic)
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

    # =============================================================================
    # PRIVATE METHODS (internal business logic + coordination)
    # =============================================================================

    def _validate_vote(self, vote_type: str, feedback: Optional[str] = None) -> None:
        """Validate vote data (business logic)"""

        # Validate vote type
        try:
            VoteType(vote_type)
        except ValueError:
            raise ValueError(
                f"Invalid vote type: {vote_type}. Must be 'thumbs_up' or 'thumbs_down'"
            )

        # Validate feedback if provided
        if feedback is not None:
            if len(feedback.strip()) < self.min_feedback_length:
                raise ValueError(
                    f"Feedback must be at least {self.min_feedback_length} characters"
                )

            if len(feedback) > self.max_feedback_length:
                raise ValueError(
                    f"Feedback must not exceed {self.max_feedback_length} characters"
                )

            # Check for potentially harmful content
            harmful_patterns = ["<script", "javascript:", "eval(", "exec("]
            if any(pattern in feedback.lower() for pattern in harmful_patterns):
                raise ValueError("Feedback contains potentially harmful content")

    def _check_can_user_vote(
        self, user_id: str, message_id: str, existing_votes: List[Vote]
    ) -> None:
        """Check if user can vote on a message (business logic)"""

        # Check if user already voted on this message
        user_votes = [
            v
            for v in existing_votes
            if v.user_id == user_id and v.message_id == message_id
        ]

        if user_votes:
            raise ValueError("User has already voted on this message")

    def _check_can_user_update_vote(
        self, user_id: str, vote_id: str, existing_votes: List[Vote]
    ) -> Vote:
        """Check if user can update a specific vote (business logic)"""

        # Find the vote
        vote = next((v for v in existing_votes if v.id == vote_id), None)

        if not vote:
            raise ValueError("Vote not found")

        if vote.user_id != user_id:
            raise ValueError("User can only update their own votes")

        # Check if vote is not too old (allow updates within 24 hours)
        hours_since_vote = (datetime.utcnow() - vote.timestamp).total_seconds() / 3600
        if hours_since_vote > 24:
            raise ValueError("Vote is too old to be updated (max 24 hours)")

        return vote

    def _create_vote(
        self,
        vote_id: str,
        user_id: str,
        message_id: str,
        session_id: str,
        vote_type: str,
        feedback: Optional[str] = None,
    ) -> Vote:
        """Create a new vote (business logic)"""

        return Vote(
            id=vote_id,
            user_id=user_id,
            message_id=message_id,
            session_id=session_id,
            vote_type=VoteType(vote_type),
            feedback=feedback.strip() if feedback else None,
            timestamp=datetime.utcnow(),
        )

    def _update_vote(
        self,
        original_vote: Vote,
        new_vote_type: Optional[str] = None,
        new_feedback: Optional[str] = None,
    ) -> Vote:
        """Update an existing vote (business logic)"""

        # Create updated vote
        updated_vote = Vote(
            id=original_vote.id,
            user_id=original_vote.user_id,
            message_id=original_vote.message_id,
            session_id=original_vote.session_id,
            vote_type=(
                VoteType(new_vote_type) if new_vote_type else original_vote.vote_type
            ),
            feedback=new_feedback.strip() if new_feedback else original_vote.feedback,
            timestamp=datetime.utcnow(),  # Update timestamp
            metadata=original_vote.metadata,
        )

        return updated_vote

    def _calculate_vote_stats(self, votes: List[Vote]) -> VoteStats:
        """Calculate statistics from votes (business logic)"""

        if not votes:
            return VoteStats(
                total_votes=0,
                thumbs_up_count=0,
                thumbs_down_count=0,
                satisfaction_rate=0.0,
                common_feedback_themes=[],
            )

        thumbs_up_count = sum(1 for v in votes if v.vote_type == VoteType.THUMBS_UP)
        thumbs_down_count = sum(1 for v in votes if v.vote_type == VoteType.THUMBS_DOWN)

        satisfaction_rate = thumbs_up_count / len(votes) if votes else 0.0

        # Extract common feedback themes (simple keyword analysis)
        feedback_themes = self._extract_feedback_themes(votes)

        return VoteStats(
            total_votes=len(votes),
            thumbs_up_count=thumbs_up_count,
            thumbs_down_count=thumbs_down_count,
            satisfaction_rate=satisfaction_rate,
            common_feedback_themes=feedback_themes,
        )

    def _extract_feedback_themes(self, votes: List[Vote]) -> List[str]:
        """Extract common themes from feedback (business logic)"""

        feedback_texts = [v.feedback for v in votes if v.feedback]

        if not feedback_texts:
            return []

        # Simple keyword extraction
        common_words = {}
        for feedback in feedback_texts:
            words = feedback.lower().split()
            for word in words:
                if len(word) > 3:  # Only consider words longer than 3 characters
                    common_words[word] = common_words.get(word, 0) + 1

        # Get most common themes
        sorted_themes = sorted(common_words.items(), key=lambda x: x[1], reverse=True)
        return [theme[0] for theme in sorted_themes[:5]]  # Top 5 themes

    def _get_vote_summary_for_message(
        self, message_id: str, all_votes: List[Vote], user_id: str
    ) -> Dict:
        """Get vote summary for a specific message (business logic)"""

        # Filter votes for this message
        message_votes = [v for v in all_votes if v.message_id == message_id]

        # Calculate stats
        stats = self._calculate_vote_stats(message_votes)

        # Find user's vote if user_id provided
        user_vote = next((v for v in message_votes if v.user_id == user_id), None)

        return {
            "message_id": message_id,
            "stats": {
                "total_votes": stats.total_votes,
                "thumbs_up_count": stats.thumbs_up_count,
                "thumbs_down_count": stats.thumbs_down_count,
                "satisfaction_rate": stats.satisfaction_rate,
                "common_feedback_themes": stats.common_feedback_themes,
            },
            "user_vote": (
                {
                    "vote_id": user_vote.id,
                    "vote_type": user_vote.vote_type.value,
                    "feedback": user_vote.feedback,
                    "timestamp": user_vote.timestamp.isoformat(),
                }
                if user_vote
                else None
            ),
        }

    def _format_votes_response(self, votes: List[Vote]) -> List[Dict]:
        """Format votes for API response (coordination)"""

        formatted_votes = []
        for vote in votes:
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

    def _group_votes_by_message(self, votes: List[Vote], current_user_id: str) -> Dict:
        """Group votes by message ID (coordination)"""

        votes_by_message = {}
        for vote in votes:
            if vote.message_id not in votes_by_message:
                votes_by_message[vote.message_id] = []
            votes_by_message[vote.message_id].append(
                {
                    "vote_id": vote.id,
                    "user_id": (
                        vote.user_id if vote.user_id == current_user_id else "anonymous"
                    ),
                    "vote_type": vote.vote_type.value,
                    "feedback": (
                        vote.feedback if vote.user_id == current_user_id else None
                    ),
                    "timestamp": vote.timestamp.isoformat(),
                }
            )

        return votes_by_message

    def _get_user_voting_pattern(self, user_id: str, all_votes: List[Vote]) -> Dict:
        """Analyze user's voting pattern (business logic)"""

        user_votes = [v for v in all_votes if v.user_id == user_id]

        if not user_votes:
            return {
                "total_votes": 0,
                "thumbs_up_ratio": 0.0,
                "provides_feedback_ratio": 0.0,
                "most_active_period": None,
            }

        thumbs_up_count = sum(
            1 for v in user_votes if v.vote_type == VoteType.THUMBS_UP
        )
        feedback_count = sum(1 for v in user_votes if v.feedback)

        return {
            "total_votes": len(user_votes),
            "thumbs_up_ratio": thumbs_up_count / len(user_votes),
            "provides_feedback_ratio": feedback_count / len(user_votes),
            "most_active_period": self._get_most_active_period(user_votes),
        }

    def _get_most_active_period(self, votes: List[Vote]) -> Optional[str]:
        """Get the most active voting period for a user (business logic)"""

        if not votes:
            return None

        # Group by hour of day
        hour_counts = {}
        for vote in votes:
            hour = vote.timestamp.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        # Find most active hour
        most_active_hour = max(hour_counts.items(), key=lambda x: x[1])[0]

        # Convert to period description
        if 6 <= most_active_hour < 12:
            return "morning"
        elif 12 <= most_active_hour < 18:
            return "afternoon"
        elif 18 <= most_active_hour < 22:
            return "evening"
        else:
            return "night"
