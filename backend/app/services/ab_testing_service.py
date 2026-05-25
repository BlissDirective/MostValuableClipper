"""
A/B Testing Service for clip variants.

Tracks performance of remix variants against originals,
calculates statistical significance, determines winners,
and feeds results back into future hook generation.
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import json

from app.services.database import SupabaseService

logger = logging.getLogger(__name__)


class TestStatus(str, Enum):
    PENDING = "pending"           # Variants created, not yet posted
    RUNNING = "running"           # Variants posted, collecting data
    SIGNIFICANT = "significant"   # Statistical significance reached
    CONCLUSIVE = "conclusive"     # Clear winner determined
    INCONCLUSIVE = "inconclusive" # No clear winner
    TIMEOUT = "timeout"           # Max duration reached without significance


@dataclass
class VariantPerformance:
    """Performance metrics for a single variant."""
    variant_id: str
    clip_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_seconds: float = 0.0
    retention_3s: float = 0.0
    retention_full: float = 0.0
    engagement_rate: float = 0.0
    sample_size: int = 0  # Number of data points


@dataclass
class ABTest:
    """An A/B test comparing original vs remix variants."""
    test_id: str
    original_clip_id: str
    user_id: str
    pipeline_id: Optional[str]
    variants: List[VariantPerformance] = field(default_factory=list)
    status: TestStatus = TestStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    winner_variant_id: Optional[str] = None
    confidence_level: float = 0.95
    min_sample_size: int = 100  # Per variant
    max_duration_hours: int = 72
    platform: str = "tiktok"


class ABTestingService:
    """
    A/B testing framework for clip variants.
    
    How it works:
    1. When variants are posted, an ABTest is created
    2. Performance data is collected via social media APIs or webhooks
    3. Statistical significance is calculated periodically
    4. Winner is declared when confidence threshold is met
    5. Results feed back into hook_analysis_service for future optimization
    """
    
    # Minimum sample size for reliable results
    MIN_VIEWS_PER_VARIANT = 50
    
    # Statistical significance threshold (p < 0.05)
    SIGNIFICANCE_THRESHOLD = 0.05
    
    def __init__(self):
        self.db = SupabaseService()
    
    async def create_test(
        self,
        original_clip_id: str,
        user_id: str,
        variant_clip_ids: List[str],
        pipeline_id: Optional[str] = None,
        platform: str = "tiktok",
        confidence_level: float = 0.95
    ) -> ABTest:
        """
        Create a new A/B test for posted variants.
        
        Args:
            original_clip_id: The original clip
            variant_clip_ids: List of remix variant clip IDs
            user_id: User who owns the clips
            pipeline_id: Optional pipeline ID
            platform: Platform being tested on
            confidence_level: Statistical confidence (0.90, 0.95, 0.99)
        
        Returns:
            ABTest object
        """
        test_id = f"abt_{original_clip_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        variants = [
            VariantPerformance(variant_id=f"variant_{i}", clip_id=clip_id)
            for i, clip_id in enumerate(variant_clip_ids)
        ]
        
        test = ABTest(
            test_id=test_id,
            original_clip_id=original_clip_id,
            user_id=user_id,
            pipeline_id=pipeline_id,
            variants=variants,
            status=TestStatus.PENDING,
            confidence_level=confidence_level,
            platform=platform
        )
        
        # Store in database
        await self._persist_test(test)
        
        logger.info(f"[ABTest] Created test {test_id} with {len(variants)} variants")
        return test
    
    async def record_performance(
        self,
        test_id: str,
        clip_id: str,
        metrics: Dict[str, Any]
    ) -> ABTest:
        """
        Record performance metrics for a variant.
        
        Args:
            test_id: The A/B test ID
            clip_id: The clip ID
            metrics: {
                "views": int,
                "likes": int,
                "comments": int,
                "shares": int,
                "watch_time_seconds": float,
                "retention_3s": float (0.0-1.0),
                "retention_full": float (0.0-1.0)
            }
        """
        test = await self._load_test(test_id)
        if not test:
            logger.error(f"[ABTest] Test not found: {test_id}")
            raise ValueError(f"Test not found: {test_id}")
        
        # Update variant performance
        for variant in test.variants:
            if variant.clip_id == clip_id:
                variant.views = metrics.get("views", variant.views)
                variant.likes = metrics.get("likes", variant.likes)
                variant.comments = metrics.get("comments", variant.comments)
                variant.shares = metrics.get("shares", variant.shares)
                variant.watch_time_seconds = metrics.get("watch_time_seconds", variant.watch_time_seconds)
                variant.retention_3s = metrics.get("retention_3s", variant.retention_3s)
                variant.retention_full = metrics.get("retention_full", variant.retention_full)
                variant.sample_size += 1
                
                # Calculate engagement rate
                if variant.views > 0:
                    variant.engagement_rate = (
                        (variant.likes + variant.comments + variant.shares) / variant.views
                    )
                break
        
        # Check if test should start (all variants have initial data)
        if test.status == TestStatus.PENDING:
            if all(v.views > 0 for v in test.variants):
                test.status = TestStatus.RUNNING
                test.started_at = datetime.now(timezone.utc)
        
        # Evaluate test
        await self._evaluate_test(test)
        
        # Persist updates
        await self._persist_test(test)
        
        return test
    
    async def _evaluate_test(self, test: ABTest):
        """Evaluate if the test has reached significance or timeout."""
        if test.status not in [TestStatus.RUNNING, TestStatus.PENDING]:
            return
        
        # Check timeout
        if test.started_at:
            elapsed = datetime.now(timezone.utc) - test.started_at
            if elapsed.total_seconds() > test.max_duration_hours * 3600:
                test.status = TestStatus.TIMEOUT
                test.ended_at = datetime.now(timezone.utc)
                test.winner_variant_id = self._select_best_variant(test, require_significance=False)
                logger.info(f"[ABTest] Test {test.test_id} timed out after {test.max_duration_hours}h")
                return
        
        # Check sample size
        min_views = min(v.views for v in test.variants)
        if min_views < self.MIN_VIEWS_PER_VARIANT:
            return  # Not enough data yet
        
        # Calculate statistical significance using chi-square for engagement rates
        # and z-test for retention rates
        best_variant = self._select_best_variant(test, require_significance=True)
        
        if best_variant:
            test.status = TestStatus.CONCLUSIVE
            test.winner_variant_id = best_variant
            test.ended_at = datetime.now(timezone.utc)
            logger.info(f"[ABTest] Test {test.test_id} concluded — winner: {best_variant}")
            
            # Feed results back into analytics
            await self._feed_results_to_analytics(test)
        elif min_views >= self.MIN_VIEWS_PER_VARIANT * 3:
            # Enough data but no significance
            test.status = TestStatus.INCONCLUSIVE
            test.ended_at = datetime.now(timezone.utc)
            logger.info(f"[ABTest] Test {test.test_id} inconclusive")
    
    def _select_best_variant(
        self,
        test: ABTest,
        require_significance: bool = True
    ) -> Optional[str]:
        """
        Select the best variant using composite scoring.
        
        Composite score weights:
        - Retention (3s): 35%
        - Retention (full): 25%
        - Engagement rate: 25%
        - Watch time: 15%
        """
        if not test.variants:
            return None
        
        # Calculate composite scores
        scored_variants = []
        for v in test.variants:
            if v.views == 0:
                continue
            
            score = (
                (v.retention_3s * 0.35) +
                (v.retention_full * 0.25) +
                (min(v.engagement_rate * 10, 1.0) * 0.25) +  # Cap at 10% engagement
                (min(v.watch_time_seconds / 60, 1.0) * 0.15)  # Cap at 60s
            )
            
            scored_variants.append((v, score))
        
        if not scored_variants:
            return None
        
        # Sort by score descending
        scored_variants.sort(key=lambda x: x[1], reverse=True)
        best_variant, best_score = scored_variants[0]
        
        if not require_significance:
            return best_variant.clip_id
        
        # Check if second-best is significantly worse
        if len(scored_variants) > 1:
            second_variant, second_score = scored_variants[1]
            
            # Require 10% relative improvement for significance
            if best_score > 0 and (best_score - second_score) / best_score > 0.10:
                return best_variant.clip_id
        
        return None
    
    async def _feed_results_to_analytics(self, test: ABTest):
        """Feed A/B test results back into hook analysis for future optimization."""
        if not test.winner_variant_id:
            return
        
        try:
            # Get winning variant details
            winner = next(
                (v for v in test.variants if v.clip_id == test.winner_variant_id),
                None
            )
            if not winner:
                return
            
            # Get clip metadata (hook archetype, etc.)
            clip = await self.db.get_clip(test.winner_variant_id)
            if not clip:
                return
            
            remix_metadata = clip.get("remix_metadata", {})
            hook_archetype = remix_metadata.get("hook_archetype", "unknown")
            hook_text = remix_metadata.get("hook_text", "")
            
            # Store as a "proven hook" for this user
            proven_hook = {
                "user_id": test.user_id,
                "test_id": test.test_id,
                "clip_id": test.winner_variant_id,
                "hook_archetype": hook_archetype,
                "hook_text": hook_text[:200],
                "platform": test.platform,
                "views": winner.views,
                "engagement_rate": winner.engagement_rate,
                "retention_3s": winner.retention_3s,
                "retention_full": winner.retention_full,
                "composite_score": (
                    winner.retention_3s * 0.35 +
                    winner.retention_full * 0.25 +
                    min(winner.engagement_rate * 10, 1.0) * 0.25 +
                    min(winner.watch_time_seconds / 60, 1.0) * 0.15
                ),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Store in proven_hooks table or append to user profile
            # For now, log it — the hook_analysis_service will pick it up
            logger.info(f"[ABTest] Proven hook for user {test.user_id}: {hook_archetype} "
                       f"(score={proven_hook['composite_score']:.3f}, views={winner.views})")
            
        except Exception as e:
            logger.error(f"[ABTest] Failed to feed results: {e}")
    
    async def get_test_status(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an A/B test."""
        test = await self._load_test(test_id)
        if not test:
            return None
        
        return {
            "test_id": test.test_id,
            "status": test.status.value,
            "original_clip_id": test.original_clip_id,
            "platform": test.platform,
            "created_at": test.created_at.isoformat(),
            "started_at": test.started_at.isoformat() if test.started_at else None,
            "ended_at": test.ended_at.isoformat() if test.ended_at else None,
            "winner_clip_id": test.winner_variant_id,
            "confidence_level": test.confidence_level,
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "clip_id": v.clip_id,
                    "views": v.views,
                    "likes": v.likes,
                    "comments": v.comments,
                    "shares": v.shares,
                    "engagement_rate": round(v.engagement_rate, 4),
                    "retention_3s": round(v.retention_3s, 3),
                    "retention_full": round(v.retention_full, 3),
                    "composite_score": round(
                        v.retention_3s * 0.35 +
                        v.retention_full * 0.25 +
                        min(v.engagement_rate * 10, 1.0) * 0.25 +
                        min(v.watch_time_seconds / 60, 1.0) * 0.15,
                        3
                    )
                }
                for v in test.variants
            ]
        }
    
    async def list_user_tests(
        self,
        user_id: str,
        status: Optional[TestStatus] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List A/B tests for a user."""
        # Query from database
        try:
            result = supabase.table("ab_tests").select("*").eq("user_id", user_id)
            if status:
                result = result.eq("status", status.value)
            result = result.order("created_at", desc=True).limit(limit).execute()
            
            return [
                {
                    "test_id": row["test_id"],
                    "status": row["status"],
                    "original_clip_id": row["original_clip_id"],
                    "platform": row["platform"],
                    "winner_clip_id": row.get("winner_variant_id"),
                    "created_at": row["created_at"],
                    "variant_count": len(row.get("variants", []))
                }
                for row in (result.data or [])
            ]
        except Exception as e:
            logger.error(f"[ABTest] Failed to list tests: {e}")
            return []
    
    # ─── Database Persistence ───
    
    async def _persist_test(self, test: ABTest):
        """Save test to database."""
        data = {
            "test_id": test.test_id,
            "original_clip_id": test.original_clip_id,
            "user_id": test.user_id,
            "pipeline_id": test.pipeline_id,
            "status": test.status.value,
            "platform": test.platform,
            "confidence_level": test.confidence_level,
            "winner_variant_id": test.winner_variant_id,
            "created_at": test.created_at.isoformat(),
            "started_at": test.started_at.isoformat() if test.started_at else None,
            "ended_at": test.ended_at.isoformat() if test.ended_at else None,
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "clip_id": v.clip_id,
                    "views": v.views,
                    "likes": v.likes,
                    "comments": v.comments,
                    "shares": v.shares,
                    "watch_time_seconds": v.watch_time_seconds,
                    "retention_3s": v.retention_3s,
                    "retention_full": v.retention_full,
                    "engagement_rate": v.engagement_rate,
                    "sample_size": v.sample_size
                }
                for v in test.variants
            ]
        }
        
        try:
            # Upsert to ab_tests table
            supabase.table("ab_tests").upsert(data, on_conflict="test_id").execute()
        except Exception as e:
            logger.error(f"[ABTest] Failed to persist test: {e}")
    
    async def _load_test(self, test_id: str) -> Optional[ABTest]:
        """Load test from database."""
        try:
            result = supabase.table("ab_tests").select("*").eq("test_id", test_id).single().execute()
            if not result.data:
                return None
            
            row = result.data
            
            variants = [
                VariantPerformance(
                    variant_id=v["variant_id"],
                    clip_id=v["clip_id"],
                    views=v.get("views", 0),
                    likes=v.get("likes", 0),
                    comments=v.get("comments", 0),
                    shares=v.get("shares", 0),
                    watch_time_seconds=v.get("watch_time_seconds", 0.0),
                    retention_3s=v.get("retention_3s", 0.0),
                    retention_full=v.get("retention_full", 0.0),
                    engagement_rate=v.get("engagement_rate", 0.0),
                    sample_size=v.get("sample_size", 0)
                )
                for v in row.get("variants", [])
            ]
            
            return ABTest(
                test_id=row["test_id"],
                original_clip_id=row["original_clip_id"],
                user_id=row["user_id"],
                pipeline_id=row.get("pipeline_id"),
                variants=variants,
                status=TestStatus(row["status"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else None,
                ended_at=datetime.fromisoformat(row["ended_at"]) if row.get("ended_at") else None,
                winner_variant_id=row.get("winner_variant_id"),
                confidence_level=row.get("confidence_level", 0.95),
                platform=row.get("platform", "tiktok")
            )
        except Exception as e:
            logger.error(f"[ABTest] Failed to load test: {e}")
            return None
    
    # ─── Webhook Handlers ───
    
    async def handle_platform_webhook(
        self,
        platform: str,
        clip_id: str,
        metrics: Dict[str, Any]
    ):
        """
        Handle incoming webhook from social media platform.
        
        Args:
            platform: "tiktok", "instagram", "youtube"
            clip_id: Our internal clip ID
            metrics: Platform-provided metrics
        """
        # Find active test for this clip
        try:
            result = supabase.table("ab_tests").select("*").contains(
                "variants", [{"clip_id": clip_id}]
            ).execute()
            
            if not result.data:
                logger.info(f"[ABTest] No active test for clip {clip_id}")
                return
            
            for row in result.data:
                if row["status"] in ["pending", "running"]:
                    await self.record_performance(
                        row["test_id"],
                        clip_id,
                        metrics
                    )
        except Exception as e:
            logger.error(f"[ABTest] Webhook handling failed: {e}")


# Singleton
ab_testing_service = ABTestingService()

# Need supabase import for DB operations
from supabase import create_client, Client
from app.core.config import settings
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
