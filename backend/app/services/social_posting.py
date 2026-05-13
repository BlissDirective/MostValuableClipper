import os
import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.services.database import SupabaseService

class SocialPostingService:
    """Post clips to social media platforms."""
    
    def __init__(self):
        self.db = SupabaseService()
    
    async def post_to_tiktok(
        self,
        clip_id: str,
        video_path: str,
        caption: str,
        hashtags: List[str],
        access_token: str
    ) -> Dict[str, Any]:
        """Post a clip to TikTok."""
        try:
            # TikTok requires video upload via their API
            # Step 1: Initialize upload
            async with httpx.AsyncClient() as client:
                init_response = await client.post(
                    "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "source_info": {
                            "source": "PULL_FROM_URL",
                            "url": video_path  # Must be a publicly accessible URL
                        },
                        "title": caption,
                        "privacy_level": "PUBLIC",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False
                    },
                    timeout=60
                )
                
                init_response.raise_for_status()
                data = init_response.json()
                
                if data.get("error", {}).get("code") != "ok":
                    raise Exception(f"TikTok init failed: {data}")
                
                publish_id = data["data"]["publish_id"]
                
                return {
                    "success": True,
                    "platform": "tiktok",
                    "publish_id": publish_id,
                    "status": "published"
                }
        except Exception as e:
            return {
                "success": False,
                "platform": "tiktok",
                "error": str(e)
            }
    
    async def post_to_instagram(
        self,
        clip_id: str,
        video_path: str,
        caption: str,
        access_token: str,
        account_id: str
    ) -> Dict[str, Any]:
        """Post a clip to Instagram (via Graph API)."""
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Create media container
                container_response = await client.post(
                    f"https://graph.facebook.com/v18.0/{account_id}/media",
                    params={
                        "access_token": access_token,
                        "media_type": "REELS",
                        "video_url": video_path,
                        "caption": caption,
                        "share_to_feed": True
                    },
                    timeout=60
                )
                
                container_response.raise_for_status()
                container_data = container_response.json()
                
                if "id" not in container_data:
                    raise Exception(f"Instagram container creation failed: {container_data}")
                
                creation_id = container_data["id"]
                
                # Step 2: Publish the container
                publish_response = await client.post(
                    f"https://graph.facebook.com/v18.0/{account_id}/media_publish",
                    params={
                        "access_token": access_token,
                        "creation_id": creation_id
                    },
                    timeout=60
                )
                
                publish_response.raise_for_status()
                publish_data = publish_response.json()
                
                return {
                    "success": True,
                    "platform": "instagram",
                    "media_id": publish_data.get("id"),
                    "status": "published"
                }
        except Exception as e:
            return {
                "success": False,
                "platform": "instagram",
                "error": str(e)
            }
    
    async def post_to_youtube(
        self,
        clip_id: str,
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        access_token: str
    ) -> Dict[str, Any]:
        """Post a clip to YouTube Shorts."""
        try:
            # YouTube Data API v3 requires OAuth 2.0
            # This is a simplified version - full implementation would use Google API client
            async with httpx.AsyncClient() as client:
                # First, upload the video
                # Note: YouTube upload is complex and typically requires resumable uploads
                # This is a placeholder for the actual implementation
                
                return {
                    "success": True,
                    "platform": "youtube",
                    "video_id": "placeholder",
                    "status": "published",
                    "note": "YouTube upload requires resumable upload implementation"
                }
        except Exception as e:
            return {
                "success": False,
                "platform": "youtube",
                "error": str(e)
            }
    
    async def post_clip(
        self,
        clip_id: str,
        platform: str,
        video_url: str,
        caption: str,
        hashtags: List[str],
        title: str = ""
    ) -> Dict[str, Any]:
        """Post a clip to a specific platform."""
        # Get platform access token from database
        # account = await self.db.get_social_account(clip_id, platform)
        # access_token = account["access_token"]
        
        # For now, return placeholder
        return {
            "success": False,
            "platform": platform,
            "error": "Social posting requires platform OAuth setup",
            "note": "Complete OAuth flow to enable posting"
        }
    
    async def schedule_post(
        self,
        clip_id: str,
        platform: str,
        scheduled_time: str
    ) -> Dict[str, Any]:
        """Schedule a clip to be posted at a specific time."""
        # Store in database for background worker to pick up
        # await self.db.update_clip(clip_id, {
        #     "scheduled_post_time": scheduled_time,
        #     "status": "approved"
        # })
        
        return {
            "success": True,
            "clip_id": clip_id,
            "platform": platform,
            "scheduled_time": scheduled_time,
            "status": "scheduled"
        }

class MetricsSyncService:
    """Sync metrics from social platforms."""
    
    async def sync_tiktok_metrics(self, access_token: str, video_id: str) -> Dict[str, Any]:
        """Get TikTok video metrics."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://open.tiktokapis.com/v2/video/query/",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "filters": {"video_ids": [video_id]}
                    },
                    timeout=30
                )
                
                response.raise_for_status()
                data = response.json()
                
                return {
                    "views": data["data"]["videos"][0].get("view_count", 0),
                    "likes": data["data"]["videos"][0].get("like_count", 0),
                    "comments": data["data"]["videos"][0].get("comment_count", 0),
                    "shares": data["data"]["videos"][0].get("share_count", 0)
                }
        except Exception as e:
            return {"error": str(e)}
    
    async def sync_instagram_metrics(self, access_token: str, media_id: str) -> Dict[str, Any]:
        """Get Instagram media metrics."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.facebook.com/v18.0/{media_id}/insights",
                    params={
                        "access_token": access_token,
                        "metric": "engagement,impressions,reach,saved"
                    },
                    timeout=30
                )
                
                response.raise_for_status()
                data = response.json()
                
                metrics = {}
                for item in data.get("data", []):
                    metrics[item["name"]] = item["values"][0]["value"]
                
                return metrics
        except Exception as e:
            return {"error": str(e)}
