from fastapi import HTTPException, status
from typing import Dict, Any
import httpx
from app.core.config import settings

class TikTokService:
    """TikTok API integration service."""
    
    BASE_URL = "https://open.tiktokapis.com/v2"
    
    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/oauth/token/",
                data={
                    "client_key": settings.TIKTOK_CLIENT_ID,
                    "client_secret": settings.TIKTOK_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": "https://your-app.com/auth/tiktok/callback"
                }
            )
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get TikTok user info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/user/info/",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": ["open_id", "union_id", "avatar_url", "display_name"]}
            )
            return response.json()
    
    async def get_video_metrics(self, access_token: str, video_id: str) -> Dict[str, Any]:
        """Get video analytics."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/video/query/",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"filters": {"video_ids": [video_id]}}
            )
            return response.json()

class InstagramService:
    """Instagram Graph API integration."""
    
    BASE_URL = "https://graph.instagram.com/v18.0"
    
    async def get_account_info(self, access_token: str) -> Dict[str, Any]:
        """Get Instagram account info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/me",
                params={"access_token": access_token, "fields": "id,username,account_type,media_count"}
            )
            return response.json()
    
    async def get_media_metrics(self, access_token: str, media_id: str) -> Dict[str, Any]:
        """Get media insights."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/{media_id}/insights",
                params={"access_token": access_token, "metric": "engagement,impressions,reach,saved"}
            )
            return response.json()

class YouTubeService:
    """YouTube Data API integration."""
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    async def get_channel_info(self, access_token: str) -> Dict[str, Any]:
        """Get YouTube channel info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/channels",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"part": "snippet,statistics", "mine": "true"}
            )
            return response.json()
    
    async def get_video_analytics(self, access_token: str, video_id: str) -> Dict[str, Any]:
        """Get video statistics."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/videos",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"part": "statistics", "id": video_id}
            )
            return response.json()
