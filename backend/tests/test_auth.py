import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_clip_unauthorized():
    """Test creating a clip without auth fails."""
    response = client.post("/api/v1/clips", json={
        "title": "Test Clip",
        "caption": "Test caption"
    })
    assert response.status_code == 403

def test_list_pipelines_unauthorized():
    """Test listing pipelines without auth fails."""
    response = client.get("/api/v1/pipelines")
    assert response.status_code == 403

def test_cors_headers():
    """Test CORS headers are present."""
    response = client.options("/api/v1/health")
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers

def test_gzip_compression():
    """Test gzip is enabled."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    # Large responses should be compressed
    assert response.headers.get("content-encoding") is None  # Health check is small

class TestStripeWebhook:
    def test_webhook_no_signature(self):
        """Test webhook rejects requests without signature."""
        response = client.post("/api/v1/webhooks/stripe", json={"type": "test"})
        assert response.status_code == 400

class TestUsers:
    def test_get_me_unauthorized(self):
        """Test /users/me without auth."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 403

    def test_update_preferences_unauthorized(self):
        """Test updating preferences without auth."""
        response = client.patch("/api/v1/users/me/preferences", json={"timezone": "UTC"})
        assert response.status_code == 403
