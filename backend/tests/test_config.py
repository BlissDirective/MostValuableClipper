import pytest
from app.core.config import Settings

class TestConfig:
    """Tests for application configuration."""

    def test_default_settings(self):
        """Test default settings load without errors."""
        settings = Settings()
        assert settings.APP_ENV in ["development", "test", "production"]
        assert settings.API_V1_PREFIX == "/api/v1"
        assert settings.CLOUDFLARE_R2_BUCKET == "mvc-clips"

    def test_cors_origins(self):
        """Test CORS origins are configured."""
        settings = Settings()
        assert len(settings.CORS_ORIGINS) > 0
        assert "http://localhost:3000" in settings.CORS_ORIGINS

    def test_stripe_price_ids(self):
        """Test Stripe price IDs are set."""
        settings = Settings()
        # In test env these may be empty, but they should exist as attributes
        assert hasattr(settings, 'STRIPE_PRICE_BASIC')
        assert hasattr(settings, 'STRIPE_PRICE_PRO')
        assert hasattr(settings, 'STRIPE_PRICE_ENTERPRISE')

    def test_supabase_url_format(self):
        """Test Supabase URL has correct format."""
        settings = Settings()
        # If set, should end with .supabase.co (production) or be localhost (test)
        if settings.SUPABASE_URL:
            assert (
                settings.SUPABASE_URL.endswith('.supabase.co')
                or 'localhost' in settings.SUPABASE_URL
                or '127.0.0.1' in settings.SUPABASE_URL
            )

    def test_r2_endpoint_format(self):
        """Test R2 endpoint has correct format."""
        settings = Settings()
        if settings.CLOUDFLARE_R2_ENDPOINT:
            assert (
                'cloudflarestorage.com' in settings.CLOUDFLARE_R2_ENDPOINT
                or 'localhost' in settings.CLOUDFLARE_R2_ENDPOINT
                or '127.0.0.1' in settings.CLOUDFLARE_R2_ENDPOINT
            )

    def test_app_secret_set(self):
        """Test app secret is not the default in production."""
        settings = Settings()
        if settings.APP_ENV == "production":
            assert settings.APP_SECRET != "change-me-in-production"
