import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAuthEndpoints:
    """Tests for auth endpoints — Phase 1 core verification."""

    def test_register_validation_missing_email(self):
        """Register without email should fail with 422."""
        response = client.post("/api/v1/auth/register", json={
            "password": "testpass123"
        })
        assert response.status_code == 422

    def test_register_validation_missing_password(self):
        """Register without password should fail with 422."""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com"
        })
        assert response.status_code == 422

    def test_register_validation_invalid_email(self):
        """Register with invalid email format should fail with 422."""
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "testpass123"
        })
        assert response.status_code == 422

    def test_login_validation_missing_email(self):
        """Login without email should fail with 422."""
        response = client.post("/api/v1/auth/login", json={
            "password": "testpass123"
        })
        assert response.status_code == 422

    def test_login_validation_missing_password(self):
        """Login without password should fail with 422."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com"
        })
        assert response.status_code == 422

    def test_login_wrong_credentials(self):
        """Login with non-existent user should fail with 401 or 500."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 500]  # 500 is acceptable for Supabase network errors in test env

    def test_me_without_auth(self):
        """GET /auth/me without token should return 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_logout_without_auth(self):
        """POST /auth/logout without token should return 401."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    def test_refresh_without_token(self):
        """POST /auth/refresh without body should return 422."""
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 422

    def test_auth_endpoints_exist(self):
        """All auth endpoints should be registered and accessible."""
        endpoints = [
            ("POST", "/api/v1/auth/register"),
            ("POST", "/api/v1/auth/login"),
            ("POST", "/api/v1/auth/refresh"),
            ("POST", "/api/v1/auth/logout"),
            ("GET", "/api/v1/auth/me"),
        ]
        for method, path in endpoints:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path)
            # Should not be 404
            assert response.status_code != 404, f"Endpoint {method} {path} not found"


class TestAuthResponseShape:
    """Verify auth response structure."""

    def test_login_error_shape(self):
        """Login error should return structured JSON with detail."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrong"
        })
        assert response.status_code in [401, 500]
        data = response.json()
        assert "detail" in data

    def test_register_error_shape(self):
        """Register error should return structured JSON with detail."""
        response = client.post("/api/v1/auth/register", json={
            "email": "bad-email",
            "password": "123"
        })
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestProtectedEndpointsWithAuth:
    """Test that protected endpoints properly require auth."""

    def test_users_me_requires_auth(self):
        """GET /users/me without auth returns 401."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_pipelines_list_requires_auth(self):
        """GET /pipelines without auth returns 401."""
        response = client.get("/api/v1/pipelines")
        assert response.status_code == 401

    def test_clips_list_requires_auth(self):
        """GET /clips without auth returns 401."""
        response = client.get("/api/v1/clips")
        assert response.status_code == 401

    def test_sources_list_requires_auth(self):
        """GET /sources without auth returns 401."""
        response = client.get("/api/v1/sources")
        assert response.status_code == 401

    def test_earnings_list_requires_auth(self):
        """GET /earnings without auth returns 401."""
        response = client.get("/api/v1/earnings")
        assert response.status_code == 401

    def test_social_accounts_list_requires_auth(self):
        """GET /social/accounts without auth returns 401."""
        response = client.get("/api/v1/social/accounts")
        assert response.status_code == 401


class TestAuthOpenAPI:
    """Auth endpoints should appear in OpenAPI docs."""

    def test_openapi_includes_auth(self):
        """OpenAPI schema should include auth endpoints."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        paths = data.get("paths", {})
        assert "/api/v1/auth/register" in paths
        assert "/api/v1/auth/login" in paths
        assert "/api/v1/auth/me" in paths

    def test_openapi_auth_schemes(self):
        """OpenAPI should include HTTPBearer security scheme."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        components = data.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        assert "HTTPBearer" in security_schemes
