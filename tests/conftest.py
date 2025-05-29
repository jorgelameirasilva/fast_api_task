import pytest
from typing import Generator

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="function")
def client() -> Generator:
    """
    Create a test client for the FastAPI application.
    """
    with TestClient(app) as client:
        yield client
