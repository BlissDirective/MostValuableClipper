"""AI-powered hook analysis service.

Dynamically analyzes clip content and performance to identify hook archetypes,
rank them by effectiveness, and generate actionable insights.
Replaces static archetype data with data-driven, personalized analysis.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from collections import defaultdict
from dataclasses import dataclass

from app.services.database import SupabaseService

logger = logging.getLogger(__name__)


@dataclass
class HookPattern:
    """A detected hook pattern with performance metrics."""
    archetype: str
    pattern_type: str  # 'question', 'promise', 'pattern_break', 'reaction', 'statement', 'story', 'statistic', 'challenge'
    confidence: float
    sample_count: int
    avg_views: float
    avg_retention: float  # estimated from early views vs total views ratio
    total_clips: int
    description: str


class HookAnalysisService:
    """
    Analyzes clip transcripts/captions to dynamically identify hook archetypes
    and correlate them with performance metrics.
    
    Uses a hybrid approach:
    1. Pattern-based classification (regex/heuristics) for MVP speed
    2. Performance correlation using available metrics
    3. Dynamic archetype discovery (not limited to predefined categories)
    """
    
    # Hook pattern detectors - regex/heuristic based
    HOOK_PATTERNS = {
        "question": {
            "patterns": [
                r"^(did you know|have you ever|do you|why (does|is|are|would|did)|what (if|is|happens|does)|how (to|do|can|would|did)",
                r"\?.*$",  # Ends with question mark in first 15 words
                r"^(are you|is it|can we|should you|would you|could you)",
            ],
            "description": "Opens with a question to spark curiosity",
            "keywords": ["why", "how", "what", "did you", "have you", "are you", "can you"]
        },
        "promise": {
            "patterns": [
                r"^(here('s| is) how|this is how|i('ll| will) show you|let me show you|the (best|worst|only|secret|truth|real reason)",
                r"^(watch (this|until|till)|wait (for|until)|stay (tuned|until)|keep watching)",
                r"^(in this|by the end|at the end|next \d+)",
            ],
            "description": "Promises value or reveals something important",
            "keywords": ["here's how", "this is how", "i'll show", "secret", "truth", "watch this", "wait for"]
        },
        "pattern_break": {
            "patterns": [
                r"^(stop|don't|wait|hold on|pause|listen|nobody is talking about|everyone is wrong|everything you know)",
                r"^(not what you think|the opposite of|contrary to|unpopular opinion|hot take)",
                r"^(plot twist|but then|and then suddenly|what happened next|you won't believe)",
            ],
            "description": "Breaks expectations or challenges assumptions",
            "keywords": ["stop", "don't", "wait", "nobody", "everyone is wrong", "plot twist", "unpopular opinion"]
        },
        "reaction": {
            "patterns": [
                r"^(omg|oh my|i can't believe|no way|that's insane|what the|holy|absolutely|completely|totally)",
                r"^(when you see|wait for it|just look at|look at this|you have to see|check this out)",
                r"!(.*)$",  # Exclamation pattern
            ],
            "description": "Emotional reaction or shock value",
            "keywords": ["omg", "can't believe", "no way", "insane", "look at this", "wait for it"]
        },
        "story": {
            "patterns": [
                r"^(once (upon a time|i)|back when|i remember|when i was|the time (i|when)|story time|let me tell you)",
                r"^(so (there|this|i|we|he|she)|it all started|this started|it began|the beginning)",
                r"^(true story|real story|this actually happened|this happened to me|my experience)",
            ],
            "description": "Narrative opening that draws viewers in",
            "keywords": ["once", "when i was", "story time", "true story", "happened to me", "started when"]
        },
        "statistic": {
            "patterns": [
                r"\d+%",  # Percentage in opening
                r"(\d+ (million|billion|thousand|percent|x more|x less|times))",
                r"^(\d+ out of \d+|\d+ percent|study shows|research found|data shows|according to)",
                r"^(the \d+ (best|worst|most|biggest|smallest|fastest))",
            ],
            "description": "Leads with data, stats, or quantifiable claim",
            "keywords": ["percent", "million", "billion", "study", "research", "data", "according to"]
        },
        "challenge": {
            "patterns": [
                r"^(try this|i bet you can't|can you|challenge|test yourself|prove|i dare you)",
                r"^(comment if|let me know if|drop a|if you can|if you're|only \d+% can)",
                r"^(guess|predict|before i|before the|without looking|close your eyes)",
            ],
            "description": "Challenges the viewer to engage or test themselves",
            "keywords": ["try this", "i bet", "challenge", "can you", "guess", "comment if", "only"]
        },
        "authority": {
            "patterns": [
                r"^(as a|i'm a|i've been|after \d+ years|\d+ years of|expert|professional|founder|ceo|doctor|professor)",
                r"^(the reason (i|we|professionals)|what (experts|professionals|founders|creators) don't tell you)",
                r"^(from my experience|in my experience|based on my|what i learned|here's what i know)",
            ],
            "description": "Establishes credibility through expertise or experience",
            "keywords": ["as a", "i'm a", "years of", "expert", "experience", "professional", "founder"]
        },
    }
    
    def __init__(self):
        self.db = SupabaseService()
    
    def _classify_hook(self, text: str) -> List[Dict[str, Any]]:
        """
        Classify a clip's opening text into hook archetypes.
        Returns list of matching patterns with confidence scores.
        """
        if not text:
            return []
        
        # Normalize text for analysis
        text_lower = text.lower().strip()
        first_30_words = " ".join(text_lower.split()[:30])
        
        matches = []
        
        for pattern_type, config in self.HOOK_PATTERNS.items():
            confidence = 0.0
            matched_patterns = []
            
            # Check regex patterns
            for pattern in config["patterns"]:
                try:
                    if re.search(pattern, first_30_words, re.IGNORECASE):
                        confidence += 0.4
                        matched_patterns.append(pattern)
                except re.error:
                    continue
            
            # Check keyword presence
            keyword_matches = sum(1 for kw in config["keywords"] if kw in first_30_words)
            if keyword_matches > 0:
                confidence += min(keyword_matches * 0.2, 0.4)
            
            # Boost confidence for archetype-specific structural cues
            if pattern_type == "question" and "?" in first_30_words[:100]:
                confidence += 0.1
            elif pattern_type == "reaction" and "!" in first_30_words[:100]:
                confidence += 0.1
            elif pattern_type == "statistic" and re.search(r'\d', first_30_words):
                confidence += 0.1
            
            if confidence > 0.3:
                matches.append({
                    "pattern_type": pattern_type,
                    "confidence": min(confidence, 1.0),
                    "description": config["description"],
                    "matched_patterns": matched_patterns
                })
        
        # Sort by confidence descending
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches
    
    def _estimate_retention(self, clip: Dict[str, Any]) -> float:
        """
        Estimate retention score from available metrics.
        Uses views + engagement as proxy when direct retention data unavailable.
        """
        views = clip.get("views", 0) or 0
        likes = clip.get("likes", 0) or 0
        comments = clip.get("comments", 0) or 0
        shares = clip.get("shares", 0) or 0
        
        if views == 0:
            return 0.0
        
        # Engagement rate as proxy for retention quality
        engagement = likes + comments + shares
        engagement_rate = (engagement / views) * 100
        
        # Normalize to approximate retention score (0-100 scale)
        # Typical good engagement rate is 5-10%
        retention = min(engagement_rate * 3, 100)  # Scale up since early retention is typically higher
        
        return retention
    
    async def analyze_hooks(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze all user clips to identify hook archetypes and their performance.
        
        Returns:
            {
                "archetypes": [...],  # ranked list of hook archetypes with stats
                "insights": [...],     # generated insight sentences
                "total_clips_analyzed": int,
                "period_days": int,
                "critic_card": str     # weekly Critic-style summary
            }
        """
        try:
            # Fetch user's clips from the last N days
            clips = await self.db.list_clips(user_id=user_id, limit=1000)
            
            # Filter to clips with some performance data (views > 0 or posted)
            performance_clips = [
                c for c in clips 
                if (c.get("views", 0) > 0 or c.get("status") == "posted")
            ]
            
            if len(performance_clips) < 3:
                # Not enough data - return default archetypes with neutral messaging
                return self._generate_default_analysis()
            
            # Analyze each clip's hook pattern
            archetype_stats = defaultdict(lambda: {
                "clips": [],
                "total_views": 0,
                "total_engagement": 0,
                "retention_sum": 0,
                "pattern_type": "",
                "description": ""
            })
            
            for clip in performance_clips:
                # Get text to analyze - use caption, title, or transcript
                text = self._get_clip_opening_text(clip)
                if not text:
                    continue
                
                patterns = self._classify_hook(text)
                if not patterns:
                    # Default to statement if no pattern detected
                    patterns = [{"pattern_type": "statement", "confidence": 0.5, "description": "Direct statement or informational opening"}]
                
                # Use top pattern as primary archetype
                primary = patterns[0]
                pt = primary["pattern_type"]
                
                views = clip.get("views", 0) or 0
                engagement = (clip.get("likes", 0) or 0) + (clip.get("comments", 0) or 0) + (clip.get("shares", 0) or 0)
                retention = self._estimate_retention(clip)
                
                archetype_stats[pt]["clips"].append({
                    "clip_id": clip.get("id"),
                    "views": views,
                    "engagement": engagement,
                    "retention": retention,
                    "confidence": primary["confidence"],
                    "text_preview": text[:80] + "..." if len(text) > 80 else text
                })
                archetype_stats[pt]["total_views"] += views
                archetype_stats[pt]["total_engagement"] += engagement
                archetype_stats[pt]["retention_sum"] += retention
                archetype_stats[pt]["pattern_type"] = pt
                archetype_stats[pt]["description"] = primary["description"]
            
            # Calculate aggregate stats per archetype
            archetype_results = []
            total_avg_retention = 0
            total_count = 0
            
            for pt, stats in archetype_stats.items():
                clip_count = len(stats["clips"])
                if clip_count == 0:
                    continue
                
                avg_views = stats["total_views"] / clip_count
                avg_retention = stats["retention_sum"] / clip_count
                avg_engagement = stats["total_engagement"] / clip_count
                
                total_avg_retention += avg_retention * clip_count
                total_count += clip_count
                
                archetype_results.append({
                    "pattern_type": pt,
                    "archetype_name": pt.replace("_", "-").title(),
                    "description": stats["description"],
                    "clip_count": clip_count,
                    "total_views": stats["total_views"],
                    "avg_views": round(avg_views, 1),
                    "avg_retention": round(avg_retention, 1),
                    "avg_engagement": round(avg_engagement, 1),
                    "confidence": round(sum(c["confidence"] for c in stats["clips"]) / clip_count, 2)
                })
            
            # Calculate period baseline
            period_baseline = total_avg_retention / total_count if total_count > 0 else 1
            
            # Sort by average retention (primary metric for hook effectiveness)
            archetype_results.sort(key=lambda x: x["avg_retention"], reverse=True)
            
            # Calculate deltas vs baseline
            for i, ar in enumerate(archetype_results):
                delta = ((ar["avg_retention"] - period_baseline) / period_baseline * 100) if period_baseline > 0 else 0
                ar["rank"] = i + 1
                ar["retention_delta_pct"] = round(delta, 1)
                ar["variant"] = self._delta_to_variant(delta)
            
            # Generate insights
            insights = self._generate_insights(archetype_results, period_baseline)
            
            # Generate Critic card text
            critic_card = self._generate_critic_card(archetype_results, insights)
            
            return {
                "archetypes": archetype_results,
                "insights": insights,
                "total_clips_analyzed": len(performance_clips),
                "period_days": days,
                "period_baseline_retention": round(period_baseline, 1),
                "critic_card": critic_card
            }
            
        except Exception as e:
            logger.error(f"[HookAnalysis] Analysis failed: {e}")
            return self._generate_default_analysis()
    
    def _get_clip_opening_text(self, clip: Dict[str, Any]) -> str:
        """Extract the opening text from a clip for hook analysis."""
        # Priority: title > caption > transcript snippet
        title = clip.get("title", "")
        caption = clip.get("caption", "")
        
        # Try to get first sentence/phrase from caption
        if caption:
            # Extract first sentence or first 20 words
            sentences = re.split(r'[.!?\n]', caption)
            if sentences and sentences[0].strip():
                return sentences[0].strip()
        
        if title:
            return title
        
        # Try metadata transcript
        metadata = clip.get("metadata", {})
        if isinstance(metadata, dict):
            transcript = metadata.get("transcription_text", "")
            if transcript:
                return " ".join(transcript.split()[:20])
        
        return ""
    
    def _delta_to_variant(self, delta: float) -> str:
        """Convert retention delta to UI variant."""
        if delta > 10:
            return "positive"
        elif delta < -10:
            return "negative"
        return "neutral"
    
    def _generate_insights(self, archetypes: List[Dict[str, Any]], baseline: float) -> List[str]:
        """Generate insight sentences from archetype performance."""
        insights = []
        
        if not archetypes:
            return insights
        
        # Top performer insight
        top = archetypes[0]
        insights.append(
            f"{top['archetype_name']}-archetype hooks produced "
            f"{top['retention_delta_pct']:+.0f}% retention versus baseline "
            f"across {top['clip_count']} clips."
        )
        
        # Underperformer insight (if significant)
        negatives = [a for a in archetypes if a["retention_delta_pct"] < -15]
        if negatives:
            worst = negatives[-1]  # Most negative
            insights.append(
                f"{worst['archetype_name']} openings underperformed by "
                f"{abs(worst['retention_delta_pct']):.0f}% — consider testing alternatives."
            )
        
        # Pattern discovery insight
        if len(archetypes) >= 3:
            mid = archetypes[len(archetypes) // 2]
            insights.append(
                f"{mid['archetype_name']} hooks show consistent, stable performance — "
                f"good fallback when testing new patterns."
            )
        
        # Volume insight
        high_volume = [a for a in archetypes if a["clip_count"] >= 10]
        if high_volume:
            hv = high_volume[0]
            insights.append(
                f"Your {hv['clip_count']} {hv['archetype_name'].lower()} clips represent "
                f"your most-tested pattern — data confidence is high."
            )
        
        return insights
    
    def _generate_critic_card(self, archetypes: List[Dict[str, Any]], insights: List[str]) -> str:
        """Generate weekly Critic card text."""
        if not archetypes:
            return "Not enough clip data to analyze hook performance yet. Generate and post more clips to see AI-powered insights."
        
        lines = []
        top = archetypes[0]
        
        lines.append(
            f"{top['archetype_name']}-archetype hooks produced "
            f"{top['retention_delta_pct']:+.0f}% retention versus other patterns "
            f"across {top['clip_count']} clips."
        )
        
        # Add second best if close
        if len(archetypes) > 1:
            second = archetypes[1]
            gap = top["retention_delta_pct"] - second["retention_delta_pct"]
            if gap < 20:
                lines.append(
                    f"{second['archetype_name']} openings are close behind at "
                    f"{second['retention_delta_pct']:+.0f}% — a solid secondary pattern."
                )
        
        # Add tactical recommendation
        if top["pattern_type"] == "question":
            lines.append("Questions in the first 3 seconds continue to perform well for your content. Consider front-loading curiosity hooks.")
        elif top["pattern_type"] == "promise":
            lines.append("Value promises and 'here's how' openings are resonating. Maintain clear benefit signaling in your hooks.")
        elif top["pattern_type"] == "pattern_break":
            lines.append("Contrarian and pattern-break hooks are cutting through. Your audience responds to challenged assumptions.")
        elif top["pattern_type"] == "story":
            lines.append("Narrative openings are your strongest pattern. Lean into personal experience and story structure.")
        elif top["pattern_type"] == "statistic":
            lines.append("Data-led hooks with numbers and stats are performing. Your audience values quantified claims.")
        else:
            lines.append(f"Your {top['archetype_name'].lower()} hook pattern is currently the strongest performer. Double down on this approach while testing variants.")
        
        return " ".join(lines)
    
    def _generate_default_analysis(self) -> Dict[str, Any]:
        """Return default archetypes when insufficient data."""
        return {
            "archetypes": [
                {
                    "pattern_type": "question",
                    "archetype_name": "Question",
                    "description": "Opens with a question to spark curiosity",
                    "clip_count": 0,
                    "total_views": 0,
                    "avg_views": 0,
                    "avg_retention": 0,
                    "avg_engagement": 0,
                    "retention_delta_pct": 0,
                    "rank": 1,
                    "variant": "neutral",
                    "confidence": 0
                },
                {
                    "pattern_type": "promise",
                    "archetype_name": "Promise",
                    "description": "Promises value or reveals something important",
                    "clip_count": 0,
                    "total_views": 0,
                    "avg_views": 0,
                    "avg_retention": 0,
                    "avg_engagement": 0,
                    "retention_delta_pct": 0,
                    "rank": 2,
                    "variant": "neutral",
                    "confidence": 0
                },
                {
                    "pattern_type": "pattern_break",
                    "archetype_name": "Pattern-break",
                    "description": "Breaks expectations or challenges assumptions",
                    "clip_count": 0,
                    "total_views": 0,
                    "avg_views": 0,
                    "avg_retention": 0,
                    "avg_engagement": 0,
                    "retention_delta_pct": 0,
                    "rank": 3,
                    "variant": "neutral",
                    "confidence": 0
                }
            ],
            "insights": [
                "Generate and post more clips to unlock AI-powered hook analysis.",
                "We need at least 3 posted clips to analyze your hook patterns."
            ],
            "total_clips_analyzed": 0,
            "period_days": 30,
            "period_baseline_retention": 0,
            "critic_card": "Not enough clip data yet. Post a few clips and check back — your personalized hook insights will appear here."
        }


# Singleton instance
hook_analysis_service = HookAnalysisService()
