import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestPipelinesAPI:
    """Tests for pipeline endpoints."""

    def test_list_pipelines_unauthorized(self):
        """Test listing pipelines without auth fails."""
        response = client.get("/api/v1/pipelines")
        assert response.status_code == 401

    def test_create_pipeline_unauthorized(self):
        """Test creating a pipeline without auth fails."""
        response = client.post("/api/v1/pipelines", json={
            "name": "Test Pipeline",
            "theme": "Tech Reviews",
            "niche": "Technology"
        })
        assert response.status_code == 401

    def test_get_pipeline_unauthorized(self):
        """Test getting a single pipeline without auth fails."""
        response = client.get("/api/v1/pipelines/test-id")
        assert response.status_code == 401

    def test_update_pipeline_unauthorized(self):
        """Test updating a pipeline without auth fails."""
        response = client.patch("/api/v1/pipelines/test-id", json={
            "status": "paused"
        })
        assert response.status_code == 401

    def test_delete_pipeline_unauthorized(self):
        """Test deleting a pipeline without auth fails."""
        response = client.delete("/api/v1/pipelines/test-id")
        assert response.status_code == 401

    def test_toggle_pipeline_unauthorized(self):
        """Test toggling a pipeline without auth fails."""
        response = client.post("/api/v1/pipelines/test-id/toggle")
        assert response.status_code == 401


class TestClipsAPI:
    """Tests for clip endpoints."""

    def test_list_clips_unauthorized(self):
        """Test listing clips without auth fails."""
        response = client.get("/api/v1/clips")
        assert response.status_code == 401

    def test_list_clips_with_filters_unauthorized(self):
        """Test listing clips with status filter without auth fails."""
        response = client.get("/api/v1/clips?status=pending")
        assert response.status_code == 401

    def test_create_clip_unauthorized(self):
        """Test creating a clip without auth fails."""
        response = client.post("/api/v1/clips", json={
            "source_id": "test-source-id",
            "pipeline_id": "test-pipeline-id"
        })
        assert response.status_code == 401

    def test_get_clip_unauthorized(self):
        """Test getting a single clip without auth fails."""
        response = client.get("/api/v1/clips/test-id")
        assert response.status_code == 401

    def test_approve_clip_unauthorized(self):
        """Test approving a clip without auth fails."""
        response = client.post("/api/v1/clips/test-id/approve")
        assert response.status_code == 401

    def test_reject_clip_unauthorized(self):
        """Test rejecting a clip without auth fails."""
        response = client.post("/api/v1/clips/test-id/reject")
        assert response.status_code == 401

    def test_schedule_clip_unauthorized(self):
        """Test scheduling a clip without auth fails."""
        response = client.patch("/api/v1/clips/test-id/schedule", json={
            "scheduled_post_time": "2026-01-01T12:00:00Z"
        })
        assert response.status_code == 401

    def test_delete_clip_unauthorized(self):
        """Test deleting a clip returns 405 (DELETE not implemented for clips)."""
        response = client.delete("/api/v1/clips/test-id")
        assert response.status_code == 405


class TestSourcesAPI:
    """Tests for source endpoints."""

    def test_list_sources_unauthorized(self):
        """Test listing sources without auth fails."""
        response = client.get("/api/v1/sources")
        assert response.status_code == 401

    def test_create_source_unauthorized(self):
        """Test creating a source without auth fails."""
        response = client.post("/api/v1/sources", json={
            "title": "Test Source",
            "original_url": "https://youtube.com/watch?v=test"
        })
        assert response.status_code == 401

    def test_get_source_unauthorized(self):
        """Test getting a single source without auth fails."""
        response = client.get("/api/v1/sources/test-id")
        assert response.status_code == 401

    def test_delete_source_unauthorized(self):
        """Test deleting a source without auth fails."""
        response = client.delete("/api/v1/sources/test-id")
        assert response.status_code == 401


class TestEarningsAPI:
    """Tests for earnings endpoints."""

    def test_list_earnings_unauthorized(self):
        """Test listing earnings without auth fails."""
        response = client.get("/api/v1/earnings")
        assert response.status_code == 401

    def test_get_earnings_summary_unauthorized(self):
        """Test getting earnings summary without auth fails."""
        response = client.get("/api/v1/earnings/summary")
        assert response.status_code == 401


class TestSocialAccountsAPI:
    """Tests for social accounts endpoints."""

    def test_list_social_accounts_unauthorized(self):
        """Test listing social accounts without auth fails."""
        response = client.get("/api/v1/social/accounts")
        assert response.status_code == 401

    def test_connect_social_account_unauthorized(self):
        """Test connecting a social account without auth fails."""
        response = client.post("/api/v1/social/connect", json={
            "platform": "tiktok",
            "redirect_uri": "mvc-app://callback"
        })
        assert response.status_code == 401


class TestSubscriptionAPI:
    """Tests for subscription/billing endpoints."""

    def test_get_current_subscription_unauthorized(self):
        """Test getting subscription without auth fails."""
        response = client.get("/api/v1/users/me/subscription")
        assert response.status_code == 401

    def test_create_checkout_unauthorized(self):
        """Test creating checkout session without auth returns 401."""
        response = client.post("/api/v1/subscriptions/checkout", json={
            "tier": "pro"
        })
        assert response.status_code == 401

    def test_cancel_subscription_unauthorized(self):
        """Test canceling subscription without auth returns 401."""
        response = client.post("/api/v1/subscriptions/cancel")
        assert response.status_code == 401


class TestValidation:
    """Tests for input validation."""

    def test_create_source_invalid_url(self):
        """Test creating source with invalid URL format."""
        response = client.post("/api/v1/sources", json={
            "title": "Test",
            "original_url": "not-a-valid-url"
        })
        assert response.status_code in [401, 422]

    def test_create_pipeline_missing_name(self):
        """Test creating pipeline without required name."""
        response = client.post("/api/v1/pipelines", json={
            "theme": "Tech"
        })
        assert response.status_code in [401, 422]

    def test_clip_status_invalid_value(self):
        """Test filtering clips with invalid status."""
        response = client.get("/api/v1/clips?status=invalid_status")
        assert response.status_code in [401, 422]


class TestStripeWebhooks:
    """Tests for Stripe webhook handling."""

    def test_stripe_webhook_invalid_signature(self):
        """Test webhook rejects invalid signature."""
        response = client.post("/api/v1/webhooks/stripe", json={
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "test"}}
        })
        assert response.status_code == 400

    def test_stripe_webhook_empty_body(self):
        """Test webhook rejects empty body."""
        response = client.post("/api/v1/webhooks/stripe")
        assert response.status_code == 400


class TestHealthAndInfo:
    """Tests for health and info endpoints."""

    def test_health_check(self):
        """Test health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_info(self):
        """Test API info endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "MVC API" in data.get("message", "")

    def test_404_handler(self):
        """Test 404 handling for unknown routes."""
        response = client.get("/api/v1/nonexistent-route")
        assert response.status_code == 404

    def test_openapi_docs(self):
        """Test OpenAPI docs are accessible."""
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
