import os
import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings

class ZernioService:
    """Unified social media API via Zernio.
    
    Posts to TikTok, Instagram, YouTube, Facebook, Twitter/X, LinkedIn
    with a single API call. Handles token refresh, rate limits, retries.
    """
    
    BASE_URL = "https://api.zernio.com/v1"
    
    def __init__(self):
        self.api_key = settings.ZERNIO_API_KEY or os.getenv("ZERNIO_API_KEY")
        if not self.api_key:
            raise ValueError("ZERNIO_API_KEY not configured")
    
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def list_connected_accounts(self) -> List[Dict[str, Any]]:
        """Get all connected social accounts."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts",
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("accounts", [])
    
    async def get_account(self, account_id: str) -> Dict[str, Any]:
        """Get a specific connected account."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{account_id}",
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def post_clip(
        self,
        video_url: str,
        caption: str,
        platforms: List[str],
        account_ids: Optional[List[str]] = None,
        schedule_time: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a clip to one or more platforms.
        
        Args:
            video_url: Publicly accessible video URL
            caption: Post caption/text
            platforms: List of platform names (tiktok, instagram, youtube, etc.)
            account_ids: Specific Zernio account IDs to post to (optional)
            schedule_time: ISO datetime for scheduled posts (optional)
            hashtags: List of hashtags to append (optional)
            title: Video title for YouTube (optional)
        """
        payload = {
            "video_url": video_url,
            "caption": caption,
            "platforms": platforms,
            "post_now": schedule_time is None
        }
        
        if account_ids:
            payload["account_ids"] = account_ids
        if schedule_time:
            payload["scheduled_time"] = schedule_time
        if hashtags:
            payload["hashtags"] = hashtags
        if title:
            payload["title"] = title
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/posts",
                headers=self._headers(),
                json=payload,
                timeout=120  # Video upload can take time
            )
            response.raise_for_status()
            return response.json()
    
    async def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """Check status of a posted clip."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/posts/{post_id}",
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def get_metrics(
        self,
        account_id: str,
        post_ids: Optional[List[str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get metrics for posts on a connected account.
        
        Args:
            account_id: Zernio account ID
            post_ids: Specific post IDs (optional, gets all if omitted)
            since: Start date ISO string (optional)
            until: End date ISO string (optional)
        """
        params = {"account_id": account_id}
        if post_ids:
            params["post_ids"] = ",".join(post_ids)
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/metrics",
                headers=self._headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_post(self, post_id: str) -> Dict[str, Any]:
        """Delete a posted clip from platforms."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/posts/{post_id}",
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def get_oauth_url(self, platform: str, profile_id: str, redirect_url: str) -> Dict[str, Any]:
        """Get OAuth authorization URL for a platform.
        
        Args:
            platform: Platform name (tiktok, instagram, youtube, etc.)
            profile_id: Your Zernio profile ID
            redirect_url: URL to redirect user after authorization
            
        Returns:
            Dict with auth_url and other connection metadata
        """
        mapped = self.map_platform_to_zernio(platform)
        params = {
            "profileId": profile_id,
            "redirect_url": redirect_url
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/connect/{mapped}",
                headers=self._headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def handle_oauth_callback(self, platform: str, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Complete OAuth callback by exchanging tokens with Zernio.
        
        Args:
            platform: Platform name
            query_params: Query parameters from the OAuth redirect (accountId, handle, etc.)
            
        Returns:
            Connected account details
        """
        mapped = self.map_platform_to_zernio(platform)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/connect/{mapped}",
                headers=self._headers(),
                json=query_params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

    async def get_platforms(self) -> List[Dict[str, Any]]:
        """List all supported platforms and their capabilities."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/platforms",
                headers=self._headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("platforms", [])
    
    @staticmethod
    def map_platform_to_zernio(platform: str) -> str:
        """Map internal platform names to Zernio platform names."""
        mapping = {
            "tiktok": "tiktok",
            "instagram": "instagram",
            "youtube": "youtube",
            "facebook": "facebook",
            "twitter": "twitter",
            "x": "twitter",
            "linkedin": "linkedin"
        }
        return mapping.get(platform.lower(), platform.lower())
    
    @staticmethod
    def map_zernio_to_platform(zernio_platform: str) -> str:
        """Map Zernio platform names to internal platform names."""
        mapping = {
            "tiktok": "tiktok",
            "instagram": "instagram",
            "youtube": "youtube",
            "facebook": "facebook",
            "twitter": "twitter",
            "linkedin": "linkedin"
        }
        return mapping.get(zernio_platform.lower(), zernio_platform.lower())