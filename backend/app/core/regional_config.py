"""
Regional Configuration — Multi-Region Deployment Awareness (Phase 4)

Handles region-specific settings, database read replicas, and latency-based
routing for multi-region Fly.io deployments.

Regions:
  lax — Los Angeles (primary, default)
  iad — Washington DC (East Coast)
  fra — Frankfurt (Europe)

Usage:
    from app.core.regional_config import get_region_config
    region = get_region_config()
    db_url = region.database_url  # regional read replica
"""
from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegionConfig:
    """Immutable configuration for a deployment region."""
    code: str
    name: str
    timezone: str
    database_url: Optional[str]  # Regional read replica URL
    redis_url: Optional[str]     # Regional Redis cache
    storage_region: str          # R2/S3 storage region for this geography
    worker_capacity: int         # Max concurrent workers in this region
    latency_target_ms: int       # Target API latency for this region
    is_primary: bool             # Whether this is the primary region

    @property
    def full_name(self) -> str:
        return f"{self.name} ({self.code.upper()})"


# ---------------------------------------------------------------------------
# Regional Registry
# ---------------------------------------------------------------------------

REGION_REGISTRY: Dict[str, RegionConfig] = {
    "lax": RegionConfig(
        code="lax", name="Los Angeles", timezone="America/Los_Angeles",
        database_url=None, redis_url=None,
        storage_region="wnam", worker_capacity=50,
        latency_target_ms=100, is_primary=True,
    ),
    "iad": RegionConfig(
        code="iad", name="Washington DC", timezone="America/New_York",
        database_url=None, redis_url=None,
        storage_region="enam", worker_capacity=30,
        latency_target_ms=100, is_primary=False,
    ),
    "fra": RegionConfig(
        code="fra", name="Frankfurt", timezone="Europe/Berlin",
        database_url=None, redis_url=None,
        storage_region="weur", worker_capacity=20,
        latency_target_ms=150, is_primary=False,
    ),
}

# Environment variable overrides per region
ENV_PREFIXES = {
    "lax": "PRIMARY_",
    "iad": "EAST_",
    "fra": "EUROPE_",
}


def get_current_region() -> str:
    """Detect the current deployment region from environment.

    Checks in order:
      1. FLY_REGION (Fly.io automatic)
      2. DEPLOY_REGION (manual override)
      3. DEFAULT_REGION config
      4. Fallback to 'lax'
    """
    return (
        os.environ.get("FLY_REGION") or
        os.environ.get("DEPLOY_REGION") or
        os.environ.get("DEFAULT_REGION", "lax").lower()
    )


def get_region_config(region_code: Optional[str] = None) -> RegionConfig:
    """Get configuration for a specific region (or current region).

    Applies environment variable overrides for regional database URLs,
    Redis URLs, and worker capacity.
    """
    code = (region_code or get_current_region()).lower()

    if code not in REGION_REGISTRY:
        logger.warning(f"[Region] Unknown region '{code}', falling back to lax")
        code = "lax"

    base = REGION_REGISTRY[code]
    prefix = ENV_PREFIXES.get(code, "")

    # Apply environment overrides
    db_url = os.environ.get(f"{prefix}DATABASE_URL") or base.database_url
    redis_url = os.environ.get(f"{prefix}REDIS_URL") or base.redis_url
    capacity = int(os.environ.get(f"{prefix}WORKER_CAPACITY", base.worker_capacity))

    return RegionConfig(
        code=base.code, name=base.name, timezone=base.timezone,
        database_url=db_url, redis_url=redis_url,
        storage_region=base.storage_region, worker_capacity=capacity,
        latency_target_ms=base.latency_target_ms, is_primary=base.is_primary,
    )


def get_all_regions() -> Dict[str, RegionConfig]:
    """Get configurations for all deployed regions."""
    deployed = os.environ.get("DEPLOYED_REGIONS", "lax").split(",")
    return {r.strip(): get_region_config(r.strip()) for r in deployed if r.strip()}


def get_nearest_region(client_region_hint: Optional[str] = None) -> str:
    """Determine the nearest deployed region for a client.

    Uses a simple geographic mapping. For production, consider
    using a GeoIP service or latency-based routing.
    """
    if not client_region_hint:
        return get_current_region()

    hint = client_region_hint.lower()
    deployed = list(get_all_regions().keys())

    # North America East → iad
    if hint in ("us-east", "east", "nyc", "mia", "atl", "bos"):
        return "iad" if "iad" in deployed else "lax"

    # Europe → fra
    if hint in ("eu", "europe", "de", "fr", "uk", "nl"):
        return "fra" if "fra" in deployed else "lax"

    # Default → primary
    return "lax"


def is_primary_region() -> bool:
    """Check if running in the primary region."""
    return get_region_config().is_primary


def get_regional_database_url() -> Optional[str]:
    """Get the database URL for the current region (read replica)."""
    return get_region_config().database_url


def get_regional_redis_url() -> Optional[str]:
    """Get the Redis URL for the current region."""
    return get_region_config().redis_url
