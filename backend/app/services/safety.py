import os
import re
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

class SafetyCheckService:
    """Content safety and moderation checks for generated clips."""
    
    # Categories that require special handling
    SENSITIVE_CATEGORIES = [
        "news_political",
        "health",
        "finance",
        "children",
        "identifiable_individual",
        "violent_graphic"
    ]
    
    # Keywords that flag content for review
    FLAG_KEYWORDS = {
        "news_political": [
            "election", "vote", "politician", "president", "congress",
            "senate", "legislation", "policy", "campaign", "party"
        ],
        "health": [
            "medical advice", "treatment", "diagnosis", "prescription",
            "medication", "cure", "disease", "condition"
        ],
        "finance": [
            "investment advice", "stock tip", "guaranteed return",
            "financial advice", "buy this", "sell now", "crypto"
        ],
        "children": [
            "child", "minor", "underage", "kid", "teenager"
        ],
        "violent_graphic": [
            "blood", "gore", "death", "killed", "murder", "attack",
            "violence", "weapon", "gun", "shooting"
        ]
    }
    
    async def check_content(
        self,
        text: str,
        video_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run content safety checks on clip text and video."""
        result = {
            "status": "pass",  # pass, review, or block
            "categories": [],
            "confidence": 0.0,
            "reasons": []
        }
        
        # Text-based checks
        text_lower = text.lower()
        
        for category, keywords in self.FLAG_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if category not in result["categories"]:
                        result["categories"].append(category)
                        result["reasons"].append(f"Keyword '{keyword}' flagged for {category}")
        
        # AI-based content moderation (if OpenAI key available)
        if settings.OPENAI_API_KEY:
            ai_result = await self._ai_moderation(text)
            if ai_result["flagged"]:
                result["categories"].extend(ai_result["categories"])
                result["reasons"].extend(ai_result["reasons"])
        
        # Determine overall status
        if result["categories"]:
            # If any sensitive categories found, require review
            sensitive_found = any(cat in self.SENSITIVE_CATEGORIES for cat in result["categories"])
            if sensitive_found:
                result["status"] = "review"
            else:
                result["status"] = "pass"
        
        # Calculate confidence based on number of flags
        result["confidence"] = min(len(result["categories"]) * 0.3, 1.0)
        
        return result
    
    async def _ai_moderation(self, text: str) -> Dict[str, Any]:
        """Use OpenAI moderation API for additional checks."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/moderations",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json={"input": text},
                    timeout=30
                )
                
                response.raise_for_status()
                data = response.json()
                
                result = {
                    "flagged": data["results"][0]["flagged"],
                    "categories": [],
                    "reasons": []
                }
                
                if result["flagged"]:
                    categories = data["results"][0]["categories"]
                    scores = data["results"][0]["category_scores"]
                    
                    for category, flagged in categories.items():
                        if flagged:
                            result["categories"].append(category)
                            result["reasons"].append(
                                f"OpenAI moderation: {category} (score: {scores[category]:.3f})"
                            )
                
                return result
        except Exception:
            # If AI moderation fails, return empty result
            return {"flagged": False, "categories": [], "reasons": []}
    
    def check_copyright(self, text: str) -> Dict[str, Any]:
        """Basic copyright checks."""
        result = {
            "likely_infringing": False,
            "reasons": []
        }
        
        # Check for common copyright phrases
        copyright_phrases = [
            "copyright", "all rights reserved", "do not copy",
            "not for redistribution", "proprietary"
        ]
        
        text_lower = text.lower()
        for phrase in copyright_phrases:
            if phrase in text_lower:
                result["reasons"].append(f"Found copyright phrase: '{phrase}'")
        
        result["likely_infringing"] = len(result["reasons"]) > 0
        return result
    
    def generate_safety_report(
        self,
        clip_id: str,
        checks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a human-readable safety report."""
        return {
            "clip_id": clip_id,
            "overall_status": checks["status"],
            "requires_human_review": checks["status"] == "review",
            "categories": checks["categories"],
            "explanation": "; ".join(checks["reasons"]) if checks["reasons"] else "No issues detected",
            "confidence": checks["confidence"],
            "recommended_action": (
                "Block" if checks["status"] == "block"
                else "Review" if checks["status"] == "review"
                else "Approve"
            )
        }

class ContentEnrichmentService:
    """Generate captions, hashtags, and descriptions for clips."""
    
    async def generate_caption(
        self,
        transcript: str,
        niche: str,
        platform: str,
        max_length: int = 150
    ) -> str:
        """Generate an engaging caption from transcript."""
        if not settings.OPENAI_API_KEY:
            # Fallback: use first sentence of transcript
            sentences = transcript.split(".")
            return sentences[0][:max_length] if sentences else "Check out this clip!"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": f"You are a social media expert for {niche} content. Write engaging {platform} captions."
                            },
                            {
                                "role": "user",
                                "content": f"Write a catchy caption (max {max_length} chars) for this video:\n\n{transcript[:500]}"
                            }
                        ],
                        "max_tokens": 100,
                        "temperature": 0.7
                    },
                    timeout=30
                )
                
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            # Fallback
            return transcript[:max_length]
    
    async def generate_hashtags(
        self,
        transcript: str,
        niche: str,
        platform: str,
        count: int = 5
    ) -> List[str]:
        """Generate relevant hashtags for a clip."""
        if not settings.OPENAI_API_KEY:
            # Fallback: basic hashtag generation
            return [f"#{niche.replace(' ', '')}", f"#{platform}content", "#viral", "#trending", "#fyp"]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": f"Generate {count} relevant hashtags for {platform} {niche} content. Return only the hashtags, comma-separated."
                            },
                            {
                                "role": "user",
                                "content": f"Generate hashtags for this content:\n\n{transcript[:300]}"
                            }
                        ],
                        "max_tokens": 50,
                        "temperature": 0.5
                    },
                    timeout=30
                )
                
                response.raise_for_status()
                data = response.json()
                hashtags_text = data["choices"][0]["message"]["content"].strip()
                
                # Parse hashtags
                hashtags = [tag.strip() for tag in hashtags_text.split(",")]
                hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
                
                return hashtags[:count]
        except Exception:
            return [f"#{niche.replace(' ', '')}", "#content", "#viral"]
    
    async def generate_title(
        self,
        transcript: str,
        niche: str
    ) -> str:
        """Generate a click-worthy title."""
        if not settings.OPENAI_API_KEY:
            # Fallback: extract first sentence
            sentences = transcript.split(".")
            return sentences[0][:80] if sentences else "Untitled Clip"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": f"Write click-worthy, concise titles for {niche} short-form video clips. Max 60 characters."
                            },
                            {
                                "role": "user",
                                "content": f"Write a title for this clip:\n\n{transcript[:300]}"
                            }
                        ],
                        "max_tokens": 50,
                        "temperature": 0.8
                    },
                    timeout=30
                )
                
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()[:60]
        except Exception:
            return transcript[:60]
