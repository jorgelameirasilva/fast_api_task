import sys
import pytest
import pytest_asyncio
from quart import Quart
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app import create_app


@pytest_asyncio.fixture
def test_app():
    """Fixture to create a test client for the Quart app."""
    app = create_app()
    app.testing = True
    return app.test_client()


@pytest.mark.asyncio
async def test_empty_post(test_app):
    # Create the test payload
    test_payload = {}
    # Use POST request to test the endpoint
    response = await test_app.post("/vote", json=test_payload)
    # Parse the response
    assert response.status_code == 200  # Check if the request was successful
    data = await response.get_json()
    assert data == {
        "user_query": {},
        "chatbot_response": {},
        "upvote": {},
        "downvote": {},
        "count": {},
    }


@pytest.mark.asyncio
async def test_more_inputs(test_app):
    # Create the test payload
    test_payload = {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 1,
        "count": 1,
        "date": "01/01/01",
        "time": "00:00:00",
        "email_address": "example.email@axax1.com",
    }
    # Use POST request to test the endpoint
    response = await test_app.post("/vote", json=test_payload)
    # Parse the response
    assert response.status_code == 200  # Check if the request was successful
    data = await response.get_json()
    assert data == {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 1,
        "count": 1,
    }


@pytest.mark.asyncio
async def test_count_invalid_inputs(test_app):
    count_invalid_inputs = [-123, 0, 2, 123, 1.23, "123", [1, 2, 3], (1, 2, 3)]
    for input in count_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": input,
        }
        # Use POST request to test the endpoint
        response = await test_app.post("/vote", json=test_payload)
        # Parse the response
        assert response.status_code == 400  # Check if the request was unsuccessful


@pytest.mark.asyncio
async def test_str_invalid_inputs(test_app):
    str_invalid_inputs = [123, 1.23, {1: 2, 3: 4}, [1, 2, 3], (1, 2, 3)]
    for input in str_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": 1,
            "reason_multiple_choice": input,
        }
        # Use POST request to test the endpoint
        response = await test_app.post("/vote", json=test_payload)
        # Parse the response
        assert response.status_code == 400  # Check if the request was unsuccessful

    for input in str_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": 1,
            "additional_comments": input,
        }
        # Use POST request to test the endpoint
        response = await test_app.post("/vote", json=test_payload)
        # Parse the response
        assert response.status_code == 400  # Check if the request was unsuccessful


@pytest.mark.asyncio
async def test_upvote_basic_functionality(test_app):
    # Create the test payload
    test_payload = {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 1,
        "downvote": 0,
        "count": 1,
    }
    # Use POST request to test the endpoint
    response = await test_app.post("/vote", json=test_payload)
    # Parse the response
    assert response.status_code == 200  # Check if the request was successful
    data = await response.get_json()
    assert data == {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 1,
        "downvote": 0,
        "count": 1,
    }


@pytest.mark.asyncio
async def test_downvote_basic_functionality(test_app):
    # Create the test payload
    test_payload = {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 1,
        "count": 1,
        "reason_multiple_choice": "other",
        "additional_comments": "More comments",
    }
    # Use POST request to test the endpoint
    response = await test_app.post("/vote", json=test_payload)
    # Parse the response
    assert response.status_code == 200  # Check if the request was successful
    data = await response.get_json()
    assert data == {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 1,
        "count": 1,
    }


@pytest.mark.asyncio
async def test_vote_endpoint_invalid_inputs(test_app):
    # Create the test payload
    vote_invalid_inputs = [-123, -1, 2, 123, 1.23, "123", [1, 2, 3], (1, 2, 3)]
    for input in vote_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": input,
            "downvote": 0,
            "count": 1,
        }
        # Use POST request to test the endpoint
        response = await test_app.post("/vote", json=test_payload)
        # Parse the response
        assert response.status_code == 400  # Check if the request was unsuccessful

    for input in vote_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": input,
            "count": 1,
        }
        # Use POST request to test the endpoint
        response = await test_app.post("/vote", json=test_payload)
        # Parse the response
        assert response.status_code == 400  # Check if the request was unsuccessful
