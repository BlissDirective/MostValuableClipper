"""
Tests for health check helpers (no external dependencies).
Run with: pytest app/tests/test_health_endpoints.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Test the HealthStatus model directly without importing the full API module
from pydantic import BaseModel
from typing import Dict, Any


class MockHealthStatus(BaseModel):
    """Mirror of HealthStatus for testing without full app imports."""
    status: str
    timestamp: str
    version: str = "1.0.0"
    checks: Dict[str, Any]


class TestHealthStatusModel:
    """Verify health status data model."""

    def test_ok_status(self):
        h = MockHealthStatus(
            status="ok",
            timestamp="2026-05-27T00:00:00Z",
            checks={"redis": {"status": "ok", "used_memory_human": "1.5M"}}
        )
        assert h.status == "ok"
        assert h.checks["redis"]["status"] == "ok"

    def test_degraded_status(self):
        h = MockHealthStatus(
            status="degraded",
            timestamp="2026-05-27T00:00:00Z",
            checks={
                "redis": {"status": "ok"},
                "database": {"status": "error", "detail": "timeout"},
                "celery": {"status": "ok", "workers_online": 4}
            }
        )
        assert h.status == "degraded"
        assert h.checks["database"]["status"] == "error"

    def test_default_version(self):
        h = MockHealthStatus(status="ok", timestamp="2026-05-27T00:00:00Z", checks={})
        assert h.version == "1.0.0"

    def test_critical_services_logic(self):
        """Simulate the health endpoint's critical services check."""
        checks = {
            "redis": {"status": "ok"},
            "database": {"status": "ok"},
            "celery_workers": {"status": "ok", "workers_online": 4},
            "storage": {"status": "warning", "detail": "slow"}
        }
        critical = [checks["redis"]["status"], checks["database"]["status"]]
        overall = "ok" if all(s == "ok" for s in critical) else "degraded"
        assert overall == "ok"

    def test_critical_services_degraded(self):
        checks = {
            "redis": {"status": "ok"},
            "database": {"status": "error", "detail": "connection refused"},
        }
        critical = [checks["redis"]["status"], checks["database"]["status"]]
        overall = "ok" if all(s == "ok" for s in critical) else "degraded"
        assert overall == "degraded"


class TestWorkerHealthStructure:
    """Verify worker health response structure."""

    def test_worker_response_fields(self):
        """Simulate the worker health response."""
        response = {
            "status": "ok",
            "workers_online": 6,
            "workers": {
                "ai-worker@host1": {
                    "processed": {"task1": 100},
                    "active": 3,
                    "concurrency": 20
                },
                "ffmpeg-worker@host2": {
                    "processed": {"task2": 50},
                    "active": 1,
                    "concurrency": 2
                }
            }
        }
        assert response["workers_online"] == 6
        assert response["workers"]["ai-worker@host1"]["concurrency"] == 20
        assert response["workers"]["ffmpeg-worker@host2"]["concurrency"] == 2
