"""Tests for session-based vote functionality"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.schemas.session import SessionVoteRequest, Session, ChatMessage
from app.services.vote_service import VoteService
from app.orchestrators.vote_orchestrator import VoteOrchestrator


@pytest.fixture
def mock_cosmos_service():
    """Mock cosmos service"""
    return AsyncMock()


@pytest.fixture
def vote_service(mock_cosmos_service):
    """Vote service with mocked cosmos service"""
    return VoteService(mock_cosmos_service)


@pytest.fixture
def vote_orchestrator(vote_service):
    """Vote orchestrator with vote service"""
    return VoteOrchestrator(vote_service)


@pytest.fixture
def sample_session():
    """Sample session for testing"""
    return Session(
        id="session-123",
        user_id="user-456",
        messages=[
            ChatMessage(
                role="user",
                content="What is the vacation policy?",
                timestamp=datetime.utcnow(),
            ),
            ChatMessage(
                role="assistant",
                content="Our vacation policy allows 20 days per year...",
                timestamp=datetime.utcnow(),
            ),
        ],
        context={"department": "Engineering"},
        upvote=0,
        downvote=0,
        feedback=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        voted_at=None,
        is_active=True,
    )


@pytest.fixture
def upvote_request():
    """Sample upvote request"""
    return SessionVoteRequest(
        session_id="session-123",
        upvote=1,
        downvote=0,
        feedback="Very helpful explanation!",
    )


@pytest.fixture
def downvote_request():
    """Sample downvote request"""
    return SessionVoteRequest(
        session_id="session-123",
        upvote=0,
        downvote=1,
        feedback="Not accurate information",
    )


class TestVoteService:
    """Test vote service functionality"""

    @pytest.mark.asyncio
    async def test_process_upvote(
        self, vote_service, mock_cosmos_service, sample_session, upvote_request
    ):
        """Test processing an upvote"""
        # Setup mocks
        mock_cosmos_service.get_session.return_value = sample_session
        updated_session = sample_session.model_copy()
        updated_session.upvote = 1
        updated_session.feedback = "Very helpful explanation!"
        updated_session.voted_at = datetime.utcnow()
        mock_cosmos_service.update_session.return_value = updated_session

        # Process vote
        result = await vote_service.process_vote(upvote_request, "user-456")

        # Assertions
        assert result.upvote == 1
        assert result.downvote == 0
        assert result.feedback == "Very helpful explanation!"
        assert result.voted_at is not None
        mock_cosmos_service.get_session.assert_called_once_with(
            "session-123", "user-456"
        )
        mock_cosmos_service.update_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_downvote(
        self, vote_service, mock_cosmos_service, sample_session, downvote_request
    ):
        """Test processing a downvote"""
        # Setup mocks
        mock_cosmos_service.get_session.return_value = sample_session
        updated_session = sample_session.model_copy()
        updated_session.downvote = 1
        updated_session.feedback = "Not accurate information"
        updated_session.voted_at = datetime.utcnow()
        mock_cosmos_service.update_session.return_value = updated_session

        # Process vote
        result = await vote_service.process_vote(downvote_request, "user-456")

        # Assertions
        assert result.upvote == 0
        assert result.downvote == 1
        assert result.feedback == "Not accurate information"
        assert result.voted_at is not None

    @pytest.mark.asyncio
    async def test_process_vote_session_not_found(
        self, vote_service, mock_cosmos_service, upvote_request
    ):
        """Test processing vote when session not found"""
        # Setup mocks
        mock_cosmos_service.get_session.return_value = None

        # Process vote should raise error
        with pytest.raises(ValueError, match="Session session-123 not found"):
            await vote_service.process_vote(upvote_request, "user-456")

    @pytest.mark.asyncio
    async def test_get_session_votes(self, vote_service, mock_cosmos_service):
        """Test getting sessions with votes"""
        # Setup mocks
        voted_sessions = [
            Session(
                id="session-1",
                user_id="user-456",
                messages=[],
                upvote=1,
                downvote=0,
                feedback="Good",
                voted_at=datetime.utcnow(),
            ),
            Session(
                id="session-2",
                user_id="user-456",
                messages=[],
                upvote=0,
                downvote=1,
                feedback="Bad",
                voted_at=datetime.utcnow(),
            ),
        ]
        mock_cosmos_service.query_sessions.return_value = voted_sessions

        # Get votes
        result = await vote_service.get_session_votes("user-456", 20)

        # Assertions
        assert len(result) == 2
        assert all(session.voted_at is not None for session in result)
        mock_cosmos_service.query_sessions.assert_called_once_with(
            user_id="user-456", has_vote=True, limit=20
        )

    @pytest.mark.asyncio
    async def test_remove_vote(self, vote_service, mock_cosmos_service, sample_session):
        """Test removing a vote"""
        # Setup session with vote
        voted_session = sample_session.model_copy()
        voted_session.upvote = 1
        voted_session.feedback = "Good"
        voted_session.voted_at = datetime.utcnow()

        mock_cosmos_service.get_session.return_value = voted_session

        # Updated session without vote
        updated_session = voted_session.model_copy()
        updated_session.upvote = 0
        updated_session.downvote = 0
        updated_session.feedback = None
        updated_session.voted_at = None
        mock_cosmos_service.update_session.return_value = updated_session

        # Remove vote
        result = await vote_service.remove_vote("session-123", "user-456")

        # Assertions
        assert result.upvote == 0
        assert result.downvote == 0
        assert result.feedback is None
        assert result.voted_at is None


class TestVoteOrchestrator:
    """Test vote orchestrator functionality"""

    @pytest.mark.asyncio
    async def test_process_vote_request(self, vote_orchestrator, upvote_request):
        """Test orchestrator processing vote request"""
        # Mock the service method
        updated_session = Session(
            id="session-123",
            user_id="user-456",
            messages=[],
            upvote=1,
            downvote=0,
            feedback="Very helpful explanation!",
            voted_at=datetime.utcnow(),
        )
        vote_orchestrator.vote_service.process_vote = AsyncMock(
            return_value=updated_session
        )

        # Process vote
        result = await vote_orchestrator.process_vote_request(
            upvote_request, "user-456"
        )

        # Assertions
        assert result.upvote == 1
        assert result.feedback == "Very helpful explanation!"
        vote_orchestrator.vote_service.process_vote.assert_called_once_with(
            upvote_request, "user-456"
        )


class TestSessionVoteRequest:
    """Test SessionVoteRequest model validation"""

    def test_valid_upvote_request(self):
        """Test valid upvote request"""
        request = SessionVoteRequest(
            session_id="session-123", upvote=1, downvote=0, feedback="Good"
        )
        assert request.upvote == 1
        assert request.downvote == 0

    def test_valid_downvote_request(self):
        """Test valid downvote request"""
        request = SessionVoteRequest(
            session_id="session-123", upvote=0, downvote=1, feedback="Bad"
        )
        assert request.upvote == 0
        assert request.downvote == 1

    def test_invalid_both_votes(self):
        """Test invalid request with both votes"""
        with pytest.raises(ValueError, match="Both upvote and downvote cannot be 1"):
            SessionVoteRequest(
                session_id="session-123", upvote=1, downvote=1, feedback="Invalid"
            )

    def test_invalid_no_votes(self):
        """Test invalid request with no votes"""
        with pytest.raises(ValueError, match="Either upvote or downvote must be 1"):
            SessionVoteRequest(
                session_id="session-123", upvote=0, downvote=0, feedback="Invalid"
            )

    def test_invalid_upvote_value(self):
        """Test invalid upvote value"""
        with pytest.raises(ValueError, match="Upvote must be either 1 or 0"):
            SessionVoteRequest(
                session_id="session-123", upvote=2, downvote=0, feedback="Invalid"
            )

    def test_invalid_downvote_value(self):
        """Test invalid downvote value"""
        with pytest.raises(ValueError, match="Downvote must be either 1 or 0"):
            SessionVoteRequest(
                session_id="session-123", upvote=0, downvote=-1, feedback="Invalid"
            )
