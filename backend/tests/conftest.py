import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app
from app.services.auth import get_current_user

class MockUser:
    def __init__(self, user_id="test-user-123", email="test@example.com"):
        self.id = user_id
        self.email = email
        self.user_metadata = {"full_name": "Test User"}
        self.created_at = "2026-01-01T00:00:00"

    def model_dump(self):
        return {"id": self.id, "email": self.email}

@pytest.fixture(scope="module")
def mock_user():
    return MockUser()

@pytest.fixture(scope="module")
def client(mock_user):
    """TestClient with mocked auth dependency."""
    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="module")
def authed_client(client, mock_user):
    """Client that includes a fake Bearer token header."""
    # The override handles auth, but some middleware might inspect headers
    return client
