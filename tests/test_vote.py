"""
Comprehensive tests for vote endpoint matching the old repo
"""

import pytest


@pytest.mark.asyncio
async def test_vote_endpoint(client, sample_vote_request):
    """Test basic upvote functionality"""

    # Make request to vote endpoint
    response = await client.post("/vote", json=sample_vote_request)

    # Verify we get a successful response
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/json"

    # Parse the JSON response
    data = response.json()

    # Verify response structure matches exactly what original app.py returns
    assert "user_query" in data
    assert "chatbot_response" in data
    assert "upvote" in data
    assert "downvote" in data
    assert "count" in data

    # Verify response values match the request exactly
    assert data["user_query"] == sample_vote_request["user_query"]
    assert data["chatbot_response"] == sample_vote_request["chatbot_response"]
    assert data["upvote"] == sample_vote_request["upvote"]
    assert data["downvote"] == sample_vote_request["downvote"]
    assert data["count"] == sample_vote_request["count"]


@pytest.mark.asyncio
async def test_downvote_basic_functionality(client, sample_downvote_request):
    """Test basic downvote functionality"""

    # Make request to vote endpoint
    response = await client.post("/vote", json=sample_downvote_request)

    # Verify we get a successful response
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/json"

    # Parse the JSON response
    data = response.json()

    # Verify response values match the request exactly
    assert data["user_query"] == sample_downvote_request["user_query"]
    assert data["chatbot_response"] == sample_downvote_request["chatbot_response"]
    assert data["upvote"] == 0
    assert data["downvote"] == 1
    assert data["count"] == 1


@pytest.mark.asyncio
async def test_vote_endpoint_invalid_inputs(client, invalid_vote_inputs):
    """Test vote endpoint with various invalid inputs"""

    for invalid_input in invalid_vote_inputs:
        # Make request to vote endpoint
        response = await client.post("/vote", json=invalid_input)

        # Should get validation error (422 for FastAPI validation errors)
        assert response.status_code == 422
        assert response.headers.get("content-type") == "application/json"

        # Parse the JSON response
        data = response.json()

        # Verify error structure
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0


@pytest.mark.asyncio
async def test_empty_post(client):
    """Test empty POST request"""

    # Create empty test payload
    test_payload = {}

    # Make request to vote endpoint
    response = await client.post("/vote", json=test_payload)

    # Should get validation error
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_more_inputs(client, more_vote_inputs):
    """Test additional vote scenarios"""

    for test_input in more_vote_inputs:
        # Make request to vote endpoint
        response = await client.post("/vote", json=test_input)

        # Should be successful
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"

        # Parse the JSON response
        data = response.json()

        # Verify basic structure
        assert "user_query" in data
        assert "chatbot_response" in data
        assert "upvote" in data
        assert "downvote" in data
        assert "count" in data

        # Verify response values match the request
        assert data["user_query"] == test_input["user_query"]
        assert data["chatbot_response"] == test_input["chatbot_response"]
        assert data["upvote"] == test_input["upvote"]
        assert data["downvote"] == test_input["downvote"]
        assert data["count"] == test_input["count"]


@pytest.mark.asyncio
async def test_vote_endpoint_invalid_inputs_detailed(client):
    """Test specific invalid input scenarios"""

    # Test invalid count values
    count_invalid_inputs = [-123, 0, 2, 123, 1.23, "123", [1, 2, 3], (1, 2, 3)]

    for invalid_count in count_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": invalid_count,
        }

        response = await client.post("/vote", json=test_payload)
        assert response.status_code == 422

    # Test invalid string inputs
    str_invalid_inputs = [123, 1.23, (1, 2), 3.4, (1, 2, 3), (1, 2, 3)]

    for invalid_input in str_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": -1,
            "reason_multiple_choice": invalid_input,
        }

        response = await client.post("/vote", json=test_payload)
        assert response.status_code == 422
