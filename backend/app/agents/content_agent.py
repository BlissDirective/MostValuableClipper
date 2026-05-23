"""ContentAgent — proactively scans pipeline sources, identifies viral-worthy moments,
and generates clip proposals with timestamps, captions, and predicted performance.

Architecture:
  1. Source Scanning    — RSS feeds, YouTube channels, uploaded files
  2. Viral Detection    — Engagement spike detection, transcript quotability, duration sweet spot
  3. Proposal Generation — Start/end timestamps, hook caption, hashtags, predicted reach
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

from app.services.database import SupabaseService, supabase
from app.services.video_download import VideoDownloadService
from app.services.transcription import TranscriptionService
from app.services.claude_hook_service import ClaudeHookService
from app.services.queue import QueueService

logger = logging.getLogger(__name__)


@dataclass
class ClipProposal:
    """A generated clip proposal ready for human review or auto-approval."""
    proposal_id: str
    source_id: str
    pipeline_id: str
    user_id: str
    
    # Timestamps within the source video
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    
    # Content
    title: str
    caption: str
    hashtags: List[str]
    hook_text: str
    hook_archetype: str
    
    # Prediction
    predicted_reach: int          # Estimated views in first 24h
    predicted_retention_pct: float  # Estimated % watching past 3s
    confidence_score: float        # 0.0-1.0 based on signal strength
    
    # Source metadata
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_platform: Optional[str] = None
    
    # Processing state
    status: str = "pending"  # pending, approved, rejected, processing, posted
    created_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContentAgent:
    """Proactive content discovery and clip proposal generation."""
    
    # Duration sweet spot for short-form platforms
    MIN_DURATION = 15.0
    MAX_DURATION = 60.0
    TARGET_DURATION = 30.0
    
    # Viral signal thresholds
    ENGAGEMENT_SPIKE_THRESHOLD = 2.5   # 2.5x avg engagement = spike
    QUOTEABLE_MIN_LENGTH = 12          # Min words for a quotable moment
    QUOTEABLE_MAX_LENGTH = 40          # Max words for a quotable moment
    
    def __init__(self):
        self.db = SupabaseService()
        self.downloader = VideoDownloadService()
        self.transcriber = TranscriptionService()
        self.hook_service = ClaudeHookService()
        self.queue = QueueService()
    
    # ═══════════════════════════════════════════════════════════
    #  1. SOURCE SCANNING
    # ═══════════════════════════════════════════════════════════
    
    async def scan_pipeline_sources(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Scan all sources attached to a pipeline and return fresh content items.
        
        Returns list of content items with: id, url, title, published_at, platform,
        duration, view_count, engagement_score
        """
        pipeline = await self.db.get_pipeline(pipeline_id)
        if not pipeline:
            logger.warning(f"[ContentAgent] Pipeline {pipeline_id} not found")
            return []
        
        source_ids = pipeline.get("source_ids", []) or []
        user_id = pipeline.get("user_id", "")
        
        fresh_items = []
        
        for source_id in source_ids:
            source = await self.db.get_source(source_id)
            if not source:
                continue
            
            items = await self._scan_single_source(source, pipeline_id, user_id)
            fresh_items.extend(items)
            
            # Update source freshness
            await self.db.update_source(source_id, {
                "last_scanned_at": datetime.now(timezone.utc).isoformat(),
                "total_items_found": source.get("total_items_found", 0) + len(items)
            })
        
        logger.info(f"[ContentAgent] Pipeline {pipeline_id}: {len(fresh_items)} fresh items from {len(source_ids)} sources")
        return fresh_items
    
    async def _scan_single_source(
        self,
        source: Dict[str, Any],
        pipeline_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Scan a single source based on its type."""
        source_type = source.get("type", "")
        source_url = source.get("url", "")
        
        # Check last scan to avoid re-processing
        last_scanned = source.get("last_scanned_at")
        since = None
        if last_scanned:
            try:
                since = datetime.fromisoformat(last_scanned.replace("Z", "+00:00"))
            except:
                since = datetime.now(timezone.utc) - timedelta(hours=24)
        else:
            since = datetime.now(timezone.utc) - timedelta(hours=24)
        
        try:
            if source_type in ["youtube", "url"]:
                return await self._scan_youtube_source(source, since)
            elif source_type == "rss":
                return await self._scan_rss_source(source, since)
            elif source_type == "upload":
                return await self._scan_upload_source(source, pipeline_id, user_id)
            else:
                logger.warning(f"[ContentAgent] Unknown source type: {source_type}")
                return []
        except Exception as e:
            logger.error(f"[ContentAgent] Failed to scan source {source.get('id')}: {e}")
            # Increment failure count
            failures = source.get("consecutive_failures", 0) + 1
            await self.db.update_source(source["id"], {
                "consecutive_failures": failures,
                "last_error": str(e)[:500]
            })
            return []
    
    async def _scan_youtube_source(
        self,
        source: Dict[str, Any],
        since: datetime
    ) -> List[Dict[str, Any]]:
        """Scan a YouTube channel/playlist for recent videos."""
        # Use yt-dlp to get recent videos from channel
        url = source.get("url", "")
        if not url:
            return []
        
        try:
            # Extract channel info and recent videos
            info = await self.downloader.extract_info(url, extract_flat=True)
            if not info:
                return []
            
            entries = info.get("entries", [])[:20]  # Last 20 videos
            items = []
            
            for entry in entries:
                published = entry.get("upload_date")
                if published:
                    pub_dt = datetime.strptime(published, "%Y%m%d").replace(tzinfo=timezone.utc)
                    if pub_dt < since:
                        continue
                
                # Get full video info for engagement data
                video_id = entry.get("id", "")
                video_url = f"https://youtube.com/watch?v={video_id}"
                
                items.append({
                    "id": video_id,
                    "url": video_url,
                    "title": entry.get("title", ""),
                    "published_at": published,
                    "platform": "youtube",
                    "duration": entry.get("duration", 0),
                    "view_count": entry.get("view_count", 0),
                    "like_count": entry.get("like_count", 0),
                    "channel": entry.get("channel", ""),
                    "source_id": source["id"],
                })
            
            return items
            
        except Exception as e:
            logger.error(f"[ContentAgent] YouTube scan failed for {url}: {e}")
            return []
    
    async def _scan_rss_source(
        self,
        source: Dict[str, Any],
        since: datetime
    ) -> List[Dict[str, Any]]:
        """Scan an RSS feed for media enclosures."""
        import feedparser
        
        url = source.get("url", "")
        if not url:
            return []
        
        try:
            feed = feedparser.parse(url)
            items = []
            
            for entry in feed.entries[:20]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < since:
                        continue
                
                # Find media enclosures
                enclosures = entry.get("enclosures", [])
                media_url = None
                for enc in enclosures:
                    if enc.get("type", "").startswith("audio/") or enc.get("type", "").startswith("video/"):
                        media_url = enc.get("href", "")
                        break
                
                if not media_url:
                    # Try links
                    links = entry.get("links", [])
                    for link in links:
                        if link.get("type", "").startswith("audio/") or link.get("type", "").startswith("video/"):
                            media_url = link.get("href", "")
                            break
                
                if media_url:
                    items.append({
                        "id": entry.get("id", entry.get("guid", media_url)),
                        "url": media_url,
                        "title": entry.get("title", ""),
                        "published_at": datetime(*published[:6], tzinfo=timezone.utc).isoformat() if published else None,
                        "platform": "rss",
                        "duration": 0,  # Will be determined on download
                        "view_count": 0,
                        "source_id": source["id"],
                    })
            
            return items
            
        except Exception as e:
            logger.error(f"[ContentAgent] RSS scan failed for {url}: {e}")
            return []
    
    async def _scan_upload_source(
        self,
        source: Dict[str, Any],
        pipeline_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Scan uploaded files that haven't been processed yet."""
        # Find uploaded clips with status "uploaded" (not yet processed)
        try:
            result = supabase.table("clips")\
                .select("id, video_url, title, duration, created_at, status")\
                .eq("pipeline_id", pipeline_id)\
                .eq("user_id", user_id)\
                .eq("status", "uploaded")\
                .execute()
            
            clips = result.data or []
            items = []
            
            for clip in clips:
                items.append({
                    "id": clip["id"],
                    "url": clip.get("video_url", ""),
                    "title": clip.get("title", "Uploaded content"),
                    "published_at": clip.get("created_at"),
                    "platform": "upload",
                    "duration": clip.get("duration", 0),
                    "view_count": 0,
                    "source_id": source["id"],
                })
            
            return items
            
        except Exception as e:
            logger.error(f"[ContentAgent] Upload scan failed: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════
    #  2. VIRAL MOMENT DETECTION
    # ═══════════════════════════════════════════════════════════
    
    async def detect_viral_moments(
        self,
        content_item: Dict[str, Any],
        pipeline_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Analyze a content item and detect viral-worthy segments.
        
        Returns segments with: start, end, duration, viral_score, signals
        """
        video_url = content_item.get("url", "")
        source_id = content_item.get("source_id", "")
        
        if not video_url:
            return []
        
        segments = []
        
        try:
            # Step 1: Get video metadata
            info = await self.downloader.extract_info(video_url, extract_flat=False)
            duration = info.get("duration", 0) if info else content_item.get("duration", 0)
            
            if duration < self.MIN_DURATION:
                logger.info(f"[ContentAgent] Video too short ({duration}s), skipping: {video_url}")
                return []
            
            # Step 2: Transcribe for text-based signals
            transcript_result = await self.transcriber.transcribe(video_url)
            transcript_segments = transcript_result.get("segments", []) if transcript_result else []
            
            # Step 3: Analyze each transcript segment for quotability
            quotable_moments = self._find_quotable_moments(transcript_segments)
            
            # Step 4: Score each potential segment
            for moment in quotable_moments:
                start = moment["start"]
                end = moment["end"]
                seg_duration = end - start
                
                # Skip if outside sweet spot
                if seg_duration < self.MIN_DURATION or seg_duration > self.MAX_DURATION:
                    continue
                
                # Calculate viral score (0-1)
                score = self._calculate_viral_score(
                    moment=moment,
                    full_duration=duration,
                    content_item=content_item,
                    seg_duration=seg_duration
                )
                
                if score > 0.3:  # Minimum threshold
                    segments.append({
                        "start": start,
                        "end": end,
                        "duration": seg_duration,
                        "viral_score": round(score, 3),
                        "signals": moment.get("signals", []),
                        "transcript": moment.get("text", ""),
                        "hook_text": moment.get("hook_candidate", ""),
                    })
            
            # Step 5: If no quotable moments, generate evenly spaced segments
            if not segments and duration >= self.MIN_DURATION:
                segments = self._generate_fallback_segments(duration)
            
            # Sort by viral score descending
            segments.sort(key=lambda s: s["viral_score"], reverse=True)
            
            logger.info(f"[ContentAgent] Detected {len(segments)} viral moments from {content_item.get('title', '')[:50]}")
            return segments[:5]  # Top 5 segments max
            
        except Exception as e:
            logger.error(f"[ContentAgent] Viral detection failed for {video_url}: {e}")
            return []
    
    def _find_quotable_moments(self, transcript_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find quotable/viral-worthy moments from transcript segments."""
        if not transcript_segments:
            return []
        
        moments = []
        
        for i, seg in enumerate(transcript_segments):
            text = seg.get("text", "").strip()
            words = text.split()
            word_count = len(words)
            
            if word_count < self.QUOTEABLE_MIN_LENGTH:
                continue
            
            signals = []
            
            # Signal: Question hook
            if "?" in text:
                signals.append("question_hook")
            
            # Signal: Strong statement (starts with verb or number)
            if words and words[0][0].isupper() and words[0].lower() in [
                "here", "this", "why", "how", "what", "the", "never", "always",
                "stop", "start", "don", "do", "you", "we", "i", "they"
            ]:
                signals.append("strong_opener")
            
            # Signal: Emotional words
            emotional_words = [
                "amazing", "incredible", "shocking", "surprising", "unbelievable",
                "heartbreaking", "inspiring", "terrifying", "beautiful", "powerful",
                "love", "hate", "fear", "hope", "dream", "struggle", "win", "lose"
            ]
            if any(w.lower() in emotional_words for w in words):
                signals.append("emotional_language")
            
            # Signal: Number/Statistic
            if re.search(r'\d+%?|\d+\.\d+|\$\d+', text):
                signals.append("statistic")
            
            # Signal: Controversy/contrast
            contrast_markers = ["but", "however", "although", "instead", "unlike", "versus", "vs"]
            if any(w.lower() in contrast_markers for w in words):
                signals.append("contrast")
            
            # Signal: Action words
            action_words = ["learn", "discover", "find", "see", "watch", "try", "build", "create", "make"]
            if any(w.lower() in action_words for w in words):
                signals.append("call_to_action")
            
            # Calculate hook candidate (first sentence or key phrase)
            hook_candidate = text[:120] if len(text) > 120 else text
            
            if signals:  # Only include if there are signals
                # Extend window for context
                start = seg.get("start", 0)
                end = seg.get("end", start + 5)
                
                # Look ahead to extend to target duration
                for j in range(i + 1, min(i + 5, len(transcript_segments))):
                    next_seg = transcript_segments[j]
                    end = next_seg.get("end", end)
                    if end - start >= self.TARGET_DURATION:
                        break
                
                moments.append({
                    "start": start,
                    "end": end,
                    "text": text,
                    "hook_candidate": hook_candidate,
                    "signals": signals,
                    "signal_count": len(signals),
                    "word_count": word_count,
                })
        
        return moments
    
    def _calculate_viral_score(
        self,
        moment: Dict[str, Any],
        full_duration: float,
        content_item: Dict[str, Any],
        seg_duration: float
    ) -> float:
        """Calculate a viral score (0-1) based on multiple signals."""
        score = 0.0
        
        # Base: Signal strength (0-0.4)
        signal_count = moment.get("signal_count", 0)
        score += min(0.4, signal_count * 0.12)
        
        # Duration sweet spot bonus (0-0.2)
        # Peak at 30s, fall off toward edges
        duration_score = 1.0 - abs(seg_duration - self.TARGET_DURATION) / self.TARGET_DURATION
        score += max(0, duration_score * 0.2)
        
        # Engagement proxy from source (0-0.2)
        view_count = content_item.get("view_count", 0)
        if view_count > 100000:
            score += 0.2
        elif view_count > 10000:
            score += 0.15
        elif view_count > 1000:
            score += 0.1
        
        # Transcript density (0-0.1)
        word_count = moment.get("word_count", 0)
        words_per_second = word_count / max(1, seg_duration)
        if 2.0 <= words_per_second <= 4.5:  # Optimal speaking pace
            score += 0.1
        
        # Hook quality heuristic (0-0.1)
        hook = moment.get("hook_text", "")
        if hook and len(hook) <= 90:
            score += 0.05  # Short hook bonus
        if "?" in hook or "!" in hook:
            score += 0.05  # Punctuation energy
        
        return min(1.0, score)
    
    def _generate_fallback_segments(self, duration: float) -> List[Dict[str, Any]]:
        """Generate evenly spaced segments when no quotable moments found."""
        segments = []
        
        # Split into ~30s chunks
        num_segments = max(1, int(duration / self.TARGET_DURATION))
        chunk_size = duration / num_segments
        
        for i in range(min(num_segments, 3)):  # Max 3 fallback segments
            start = i * chunk_size
            end = min(start + self.TARGET_DURATION, duration)
            
            if end - start >= self.MIN_DURATION:
                segments.append({
                    "start": start,
                    "end": end,
                    "duration": end - start,
                    "viral_score": 0.35,  # Neutral fallback score
                    "signals": ["fallback_segmentation"],
                    "transcript": "",
                    "hook_text": "",
                })
        
        return segments
    
    # ═══════════════════════════════════════════════════════════
    #  3. PROPOSAL GENERATION
    # ═══════════════════════════════════════════════════════════
    
    async def generate_proposals(
        self,
        content_item: Dict[str, Any],
        viral_segments: List[Dict[str, Any]],
        pipeline_id: str,
        user_id: str
    ) -> List[ClipProposal]:
        """Generate full clip proposals from viral segments."""
        if not viral_segments:
            return []
        
        proposals = []
        
        # Get user's top hook archetypes for personalization
        user_archetypes = await self._get_user_top_archetypes(user_id)
        
        # Get pipeline settings for platform targeting
        pipeline = await self.db.get_pipeline(pipeline_id)
        target_platforms = pipeline.get("target_platforms", ["tiktok", "instagram"]) if pipeline else ["tiktok"]
        
        for segment in viral_segments:
            try:
                proposal = await self._generate_single_proposal(
                    content_item=content_item,
                    segment=segment,
                    pipeline_id=pipeline_id,
                    user_id=user_id,
                    target_platforms=target_platforms,
                    user_archetypes=user_archetypes
                )
                proposals.append(proposal)
            except Exception as e:
                logger.error(f"[ContentAgent] Proposal generation failed for segment: {e}")
                continue
        
        return proposals
    
    async def _generate_single_proposal(
        self,
        content_item: Dict[str, Any],
        segment: Dict[str, Any],
        pipeline_id: str,
        user_id: str,
        target_platforms: List[str],
        user_archetypes: List[str]
    ) -> ClipProposal:
        """Generate a single clip proposal from a viral segment."""
        
        start = segment["start"]
        end = segment["end"]
        duration = end - start
        transcript = segment.get("transcript", "")
        hook_text = segment.get("hook_text", "")
        viral_score = segment.get("viral_score", 0.5)
        
        # Generate hook/caption via Claude
        hooks = await self.hook_service.generate_hooks(
            transcript_text=transcript or hook_text or content_item.get("title", ""),
            user_top_archetypes=user_archetypes,
            num_variants=1,
            platform=target_platforms[0] if target_platforms else "tiktok"
        )
        
        generated_hook = hooks[0] if hooks else None
        
        caption = generated_hook.text if generated_hook else hook_text[:200]
        hook_archetype = generated_hook.archetype if generated_hook else "unknown"
        
        # Generate hashtags based on content + platform
        hashtags = self._generate_hashtags(
            content_title=content_item.get("title", ""),
            hook_text=caption,
            platform=target_platforms[0] if target_platforms else "tiktok"
        )
        
        # Predict reach based on viral score + source popularity
        predicted_reach = self._predict_reach(
            viral_score=viral_score,
            source_views=content_item.get("view_count", 0),
            platform=target_platforms[0] if target_platforms else "tiktok"
        )
        
        # Predict retention (higher for strong hooks)
        predicted_retention = 0.35 + (viral_score * 0.45)  # 35-80% range
        
        proposal = ClipProposal(
            proposal_id=f"prop-{uuid.uuid4().hex[:12]}",
            source_id=content_item.get("source_id", ""),
            pipeline_id=pipeline_id,
            user_id=user_id,
            start_seconds=round(start, 2),
            end_seconds=round(end, 2),
            duration_seconds=round(duration, 2),
            title=caption[:80] if caption else "Clip Proposal",
            caption=caption,
            hashtags=hashtags,
            hook_text=generated_hook.text if generated_hook else hook_text,
            hook_archetype=hook_archetype,
            predicted_reach=predicted_reach,
            predicted_retention_pct=round(predicted_retention, 2),
            confidence_score=round(viral_score, 3),
            source_url=content_item.get("url"),
            source_title=content_item.get("title"),
            source_platform=content_item.get("platform"),
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        return proposal
    
    def _generate_hashtags(self, content_title: str, hook_text: str, platform: str) -> List[str]:
        """Generate platform-appropriate hashtags."""
        # Extract keywords from title + hook
        text = f"{content_title} {hook_text}".lower()
        
        # Common niche hashtags (would be personalized per pipeline in production)
        base_hashtags = {
            "tiktok": ["fyp", "viral", "trending", "foryou", "foryoupage"],
            "instagram": ["reels", "instagood", "viral", "trending", "explore"],
            "youtube": ["shorts", "viral", "trending", "youtubeshorts"],
            "facebook": ["reels", "viral", "trending"],
            "twitter": ["viral", "trending", "fyp"],
        }
        
        platform_tags = base_hashtags.get(platform, base_hashtags["tiktok"])
        
        # Extract content-specific tags from text
        content_tags = []
        keyword_map = {
            "tech": ["tech", "technology", "ai", "software", "coding", "developer"],
            "business": ["business", "entrepreneur", "startup", "money", "finance"],
            "health": ["health", "fitness", "wellness", "gym", "workout"],
            "entertainment": ["funny", "comedy", "entertainment", "meme", "lol"],
            "education": ["learn", "education", "tutorial", "howto", "tips"],
            "motivation": ["motivation", "inspiration", "success", "mindset", "goals"],
        }
        
        for category, keywords in keyword_map.items():
            if any(kw in text for kw in keywords):
                content_tags.append(category)
                break
        
        # Combine: platform tags + content tags + generic viral tags
        all_tags = platform_tags[:3] + content_tags + ["viral", "trending"]
        
        # Platform-specific limits
        if platform == "tiktok":
            return all_tags[:5]
        elif platform == "instagram":
            return all_tags[:8]
        else:
            return all_tags[:5]
    
    def _predict_reach(self, viral_score: float, source_views: int, platform: str) -> int:
        """Predict 24h reach based on signals."""
        base_reach = 500  # Baseline for new account
        
        # Viral score multiplier (1x-5x)
        viral_multiplier = 1.0 + (viral_score * 4.0)
        
        # Source popularity boost
        source_boost = 0
        if source_views > 1000000:
            source_boost = 5000
        elif source_views > 100000:
            source_boost = 2000
        elif source_views > 10000:
            source_boost = 500
        
        # Platform multiplier
        platform_multipliers = {
            "tiktok": 1.5,      # Higher viral potential
            "instagram": 1.2,
            "youtube": 1.0,
            "facebook": 0.8,
            "twitter": 0.7,
        }
        platform_mult = platform_multipliers.get(platform, 1.0)
        
        predicted = int((base_reach + source_boost) * viral_multiplier * platform_mult)
        return min(50000, predicted)  # Cap at 50K for sanity
    
    async def _get_user_top_archetypes(self, user_id: str) -> List[str]:
        """Fetch user's top-performing hook archetypes from analytics."""
        try:
            from app.services.hook_analysis_service import hook_analysis_service
            result = await hook_analysis_service.analyze_hooks(user_id=user_id, days=30)
            archetypes = result.get("archetypes", [])
            # Return top 3 archetype names
            return [a.get("archetype_name", "").lower().replace(" ", "_") for a in archetypes[:3]]
        except Exception:
            return []
    
    # ═══════════════════════════════════════════════════════════
    #  4. PERSISTENCE
    # ═══════════════════════════════════════════════════════════
    
    async def save_proposals(self, proposals: List[ClipProposal]) -> List[str]:
        """Save proposals to database as pending clips.
        
        Returns list of created clip IDs.
        """
        created_ids = []
        
        for proposal in proposals:
            try:
                clip_data = {
                    "user_id": proposal.user_id,
                    "pipeline_id": proposal.pipeline_id,
                    "source_id": proposal.source_id,
                    "title": proposal.title,
                    "caption": proposal.caption,
                    "hashtags": proposal.hashtags,
                    "status": "pending_review",  # Goes to approval queue
                    "video_url": proposal.source_url,
                    "start_time": proposal.start_seconds,
                    "end_time": proposal.end_seconds,
                    "duration": proposal.duration_seconds,
                    "predicted_reach": proposal.predicted_reach,
                    "predicted_retention_pct": proposal.predicted_retention_pct,
                    "confidence_score": proposal.confidence_score,
                    "hook_text": proposal.hook_text,
                    "hook_archetype": proposal.hook_archetype,
                    "source_platform": proposal.source_platform,
                    "source_title": proposal.source_title,
                    "proposal_id": proposal.proposal_id,
                    "created_at": proposal.created_at,
                    "updated_at": proposal.created_at,
                }
                
                result = await self.db.create_clip(clip_data)
                if result and result.get("id"):
                    created_ids.append(result["id"])
                    logger.info(f"[ContentAgent] Saved proposal {proposal.proposal_id} as clip {result['id']}")
                
            except Exception as e:
                logger.error(f"[ContentAgent] Failed to save proposal: {e}")
                continue
        
        return created_ids
    
    # ═══════════════════════════════════════════════════════════
    #  5. FULL PIPELINE (orchestrator entry point)
    # ═══════════════════════════════════════════════════════════
    
    async def run_content_discovery(
        self,
        pipeline_id: str,
        user_id: Optional[str] = None,
        max_proposals: int = 5
    ) -> Dict[str, Any]:
        """Run full content discovery pipeline for a pipeline.
        
        1. Scan all sources
        2. Detect viral moments from each fresh item
        3. Generate proposals
        4. Save to approval queue
        
        Returns summary of discovery run.
        """
        start_time = time.time()
        
        logger.info(f"[ContentAgent] Starting content discovery for pipeline {pipeline_id}")
        
        # Get pipeline if user_id not provided
        if not user_id:
            pipeline = await self.db.get_pipeline(pipeline_id)
            user_id = pipeline.get("user_id", "") if pipeline else ""
        
        # Step 1: Scan sources
        fresh_items = await self.scan_pipeline_sources(pipeline_id)
        
        if not fresh_items:
            logger.info(f"[ContentAgent] No fresh content found for pipeline {pipeline_id}")
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "items_scanned": 0,
                "proposals_generated": 0,
                "clips_created": 0,
                "duration_seconds": round(time.time() - start_time, 2),
                "message": "No fresh content found"
            }
        
        # Step 2+3: Detect viral moments and generate proposals
        all_proposals = []
        
        for item in fresh_items[:10]:  # Process max 10 items per run
            try:
                segments = await self.detect_viral_moments(item, pipeline_id, user_id)
                if segments:
                    proposals = await self.generate_proposals(item, segments, pipeline_id, user_id)
                    all_proposals.extend(proposals)
            except Exception as e:
                logger.error(f"[ContentAgent] Failed processing item {item.get('id')}: {e}")
                continue
        
        # Step 4: Save to approval queue
        created_ids = await self.save_proposals(all_proposals[:max_proposals])
        
        duration = round(time.time() - start_time, 2)
        
        logger.info(f"[ContentAgent] Discovery complete: {len(created_ids)} clips created from {len(fresh_items)} items")
        
        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "items_scanned": len(fresh_items),
            "viral_segments_detected": len(all_proposals),
            "proposals_generated": len(all_proposals),
            "clips_created": len(created_ids),
            "clip_ids": created_ids,
            "duration_seconds": duration,
        }


# Global instance
content_agent = ContentAgent()
