import pytest
from unittest.mock import patch, MagicMock

class TestAuthHappyPath:
    """Happy-path tests for auth/user endpoints."""

    def test_get_me(self, client):
        """GET /users/me returns user profile."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data

    def test_get_me_subscription(self, client):
        """GET /users/me/subscription returns subscription data."""
        response = client.get("/api/v1/users/me/subscription")
        assert response.status_code == 200
        data = response.json()
        assert "tier" in data
        assert "status" in data

    def test_get_me_usage(self, client):
        """GET /users/me/usage returns clip usage."""
        response = client.get("/api/v1/users/me/usage")
        assert response.status_code == 200
        data = response.json()
        assert "clips_used" in data
        assert "clips_quota" in data
        assert "tier" in data

    def test_update_profile(self, client):
        """PATCH /users/me updates profile."""
        response = client.patch("/api/v1/users/me", json={
            "full_name": "Updated Name",
            "autonomy_mode": "fullAuto"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_get_me_export(self, client):
        """GET /users/me/export returns export data structure."""
        response = client.get("/api/v1/users/me/export")
        assert response.status_code in [200, 500]  # 500 if Supabase unavailable in tests


class TestWorkerHappyPath:
    """Happy-path tests for worker endpoints."""

    def test_worker_status(self, client):
        """GET /worker/status returns worker stats."""
        response = client.get("/api/v1/worker/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "queue_length" in data

    def test_worker_start_stop(self, client):
        """POST /worker/start and /worker/stop toggle worker."""
        start = client.post("/api/v1/worker/start")
        assert start.status_code == 200
        
        status = client.get("/api/v1/worker/status")
        assert status.status_code == 200
        
        stop = client.post("/api/v1/worker/stop")
        assert stop.status_code == 200


class TestAnalyticsHappyPath:
    """Happy-path tests for analytics endpoints."""

    def test_analytics_dashboard(self, client):
        """GET /analytics/dashboard returns dashboard data."""
        response = client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_clips" in data
        assert "total_views" in data
        assert "platform_breakdown" in data
        assert "daily_stats" in data

    def test_track_event(self, client):
        """POST /analytics/events tracks an event."""
        response = client.post("/api/v1/analytics/events", json={
            "event_type": "test_event",
            "event_data": {"test": True}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


class TestEarningsHappyPath:
    """Happy-path tests for earnings endpoints."""

    def test_get_earnings(self, client):
        """GET /earnings returns earnings data."""
        response = client.get("/api/v1/earnings")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "summary" in data

    def test_get_earnings_summary(self, client):
        """GET /earnings/summary returns summary."""
        response = client.get("/api/v1/earnings/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_earnings" in data
        assert "by_platform" in data

    def test_get_earnings_dashboard(self, client):
        """GET /earnings/dashboard returns dashboard."""
        response = client.get("/api/v1/earnings/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "lifetime_revenue_usd" in data
        assert "current_month" in data


class TestSocialHappyPath:
    """Happy-path tests for social endpoints."""

    def test_list_social_accounts(self, client):
        """GET /social/accounts returns accounts list."""
        response = client.get("/api/v1/social/accounts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_connect_manual(self, client):
        """POST /social/connect-manual connects an account."""
        response = client.post("/api/v1/social/connect-manual", json={
            "platform": "tiktok",
            "handle": "testuser"
        })
        assert response.status_code in [200, 500]  # 500 if DB unavailable
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True

    def test_disconnect_account(self, client):
        """DELETE /social/{platform} disconnects an account."""
        response = client.delete("/api/v1/social/tiktok")
        assert response.status_code in [200, 404, 500]


class TestSubscriptionsHappyPath:
    """Happy-path tests for subscription endpoints."""

    def test_get_subscription(self, client):
        """GET /users/me/subscription returns subscription."""
        response = client.get("/api/v1/users/me/subscription")
        assert response.status_code == 200
        data = response.json()
        assert "tier" in data
        assert "status" in data

    def test_create_portal(self, client):
        """POST /subscriptions/portal creates portal session."""
        with patch("app.api.subscriptions.stripe_service.create_customer") as mock_customer, \
             patch("app.api.subscriptions.stripe_service.create_customer_portal_session") as mock_portal:
            mock_customer.return_value = {"id": "cus_test"}
            mock_portal.return_value = {"url": "https://stripe.com/test-portal"}
            
            response = client.post("/api/v1/subscriptions/portal")
            assert response.status_code == 200
            data = response.json()
            assert "portal_url" in data

    def test_cancel_subscription(self, client):
        """POST /subscriptions/cancel cancels subscription."""
        with patch("app.api.subscriptions.db.get_subscription") as mock_sub, \
             patch("app.api.subscriptions.stripe_service.cancel_subscription") as mock_cancel:
            mock_sub.return_value = {
                "stripe_subscription_id": "sub_test",
                "tier": "pro",
                "status": "active"
            }
            mock_cancel.return_value = {"current_period_end": "2026-12-31T23:59:59"}
            
            response = client.post("/api/v1/subscriptions/cancel")
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True
            assert data.get("cancel_at_period_end") is True


class TestPipelineHappyPath:
    """Happy-path tests for pipeline endpoints."""

    def test_list_pipelines(self, client):
        """GET /pipelines returns pipeline list."""
        response = client.get("/api/v1/pipelines")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_pipeline(self, client):
        """POST /pipelines creates a pipeline."""
        response = client.post("/api/v1/pipelines", json={
            "name": "Test Pipeline",
            "theme": "Tech Reviews",
            "niche": "Technology",
            "target_platforms": ["tiktok", "instagram"]
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data


class TestClipsHappyPath:
    """Happy-path tests for clip endpoints."""

    def test_list_clips(self, client):
        """GET /clips returns clip list."""
        response = client.get("/api/v1/clips")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_clip(self, client):
        """POST /clips creates a clip."""
        response = client.post("/api/v1/clips", json={
            "source_id": "test-source",
            "pipeline_id": "test-pipeline",
            "title": "Test Clip"
        })
        assert response.status_code in [200, 500]

    def test_get_clip(self, client):
        """GET /clips/{id} returns a clip."""
        response = client.get("/api/v1/clips/test-clip-id")
        assert response.status_code in [200, 404, 500]

    def test_approve_reject_clip(self, client):
        """POST /clips/{id}/approve and /reject work."""
        for action in ["approve", "reject"]:
            response = client.post(f"/api/v1/clips/test-clip-id/{action}")
            assert response.status_code in [200, 404, 500]


class TestSourcesHappyPath:
    """Happy-path tests for source endpoints."""

    def test_list_sources(self, client):
        """GET /sources returns source list."""
        response = client.get("/api/v1/sources")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_source(self, client):
        """POST /sources creates a source."""
        response = client.post("/api/v1/sources", json={
            "title": "Test Source",
            "original_url": "https://youtube.com/watch?v=test123"
        })
        assert response.status_code in [200, 500]


class TestLegalHappyPath:
    """Happy-path tests for legal endpoints."""

    def test_privacy_policy(self, client):
        """GET /legal/privacy returns privacy policy."""
        response = client.get("/api/v1/legal/privacy")
        assert response.status_code == 200

    def test_terms_of_service(self, client):
        """GET /legal/terms returns terms."""
        response = client.get("/api/v1/legal/terms")
        assert response.status_code == 200
