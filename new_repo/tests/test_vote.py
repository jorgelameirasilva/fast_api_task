"""Tests for vote endpoint - matches original test patterns"""

import pytest
from fastapi.testclient import TestClient


def test_upvote_basic_functionality(client: TestClient):
    """Test basic upvote functionality"""
    test_payload = {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 1,
        "downvote": 0,
        "count": 1,
    }

    response = client.post("/vote", json=test_payload)

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "user_query": "How do I report an illness?",
        "message": "To report an illness, follow these steps:",
        "upvote": 1,
        "downvote": 0,
        "count": 1,
    }


def test_downvote_basic_functionality(client: TestClient):
    """Test basic downvote functionality"""
    test_payload = {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 1,
        "count": 1,
        "reason_multiple_choice": "other",
        "additional_comments": "More comments",
    }

    response = client.post("/vote", json=test_payload)

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "user_query": "How do I report an illness?",
        "message": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 1,
        "count": 1,
    }


def test_empty_post(client: TestClient):
    """Test empty POST request"""
    test_payload = {}

    response = client.post("/vote", json=test_payload)

    # Should get validation error for missing fields
    assert response.status_code == 422


def test_more_inputs(client: TestClient):
    """Test with extra fields that should be ignored"""
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

    response = client.post("/vote", json=test_payload)

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "user_query": "How do I report an illness?",
        "message": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 1,
        "count": 1,
    }


def test_count_invalid_inputs(client: TestClient):
    """Test invalid count values"""
    count_invalid_inputs = [-123, 0, 2, 123, 1.23, "123", [1, 2, 3], (1, 2, 3)]

    for invalid_input in count_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": invalid_input,
        }

        response = client.post("/vote", json=test_payload)
        assert response.status_code == 400 or response.status_code == 422


def test_vote_invalid_inputs(client: TestClient):
    """Test invalid upvote/downvote values"""
    vote_invalid_inputs = [-123, -1, 2, 123, 1.23, "123", [1, 2, 3], (1, 2, 3)]

    # Test invalid upvote values
    for invalid_input in vote_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": invalid_input,
            "downvote": 0,
            "count": 1,
        }

        response = client.post("/vote", json=test_payload)
        assert response.status_code == 400 or response.status_code == 422

    # Test invalid downvote values
    for invalid_input in vote_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": invalid_input,
            "count": 1,
        }

        response = client.post("/vote", json=test_payload)
        assert response.status_code == 400 or response.status_code == 422


def test_str_invalid_inputs(client: TestClient):
    """Test invalid string inputs for reason and comments"""
    str_invalid_inputs = [123, 1.23, {1: 2, 3: 4}, [1, 2, 3], (1, 2, 3)]

    # Test invalid reason_multiple_choice
    for invalid_input in str_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": 1,
            "reason_multiple_choice": invalid_input,
        }

        response = client.post("/vote", json=test_payload)
        assert response.status_code == 400 or response.status_code == 422

    # Test invalid additional_comments
    for invalid_input in str_invalid_inputs:
        test_payload = {
            "user_query": "How do I report an illness?",
            "chatbot_response": "To report an illness, follow these steps:",
            "upvote": 0,
            "downvote": 1,
            "count": 1,
            "additional_comments": invalid_input,
        }

        response = client.post("/vote", json=test_payload)
        assert response.status_code == 400 or response.status_code == 422


def test_both_votes_error(client: TestClient):
    """Test error when both upvote and downvote are 1"""
    test_payload = {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 1,
        "downvote": 1,
        "count": 1,
    }

    response = client.post("/vote", json=test_payload)
    assert response.status_code == 400 or response.status_code == 422


def test_neither_votes_error(client: TestClient):
    """Test error when both upvote and downvote are 0"""
    test_payload = {
        "user_query": "How do I report an illness?",
        "chatbot_response": "To report an illness, follow these steps:",
        "upvote": 0,
        "downvote": 0,
        "count": 1,
    }

    response = client.post("/vote", json=test_payload)
    assert response.status_code == 400 or response.status_code == 422

