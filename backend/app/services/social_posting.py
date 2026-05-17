import os
import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.services.database import SupabaseService
from app.services.zernio_service import ZernioService

class SocialPostingService:
    """Post clips to social media platforms via Zernio unified API."""
    
    def __init__(self):
        self.db = SupabaseService()
        self.zernio: Optional[ZernioService] = None
        try:
            self.zernio = ZernioService()
        except ValueError:
            self.zernio = None
    
    async def post_clip(
        self,
        clip_id: str,
        platform: str,
        video_url: str,
        caption: str,
        hashtags: List[str],
        title: str = ""
    ) -> Dict[str, Any]:
        """Post a clip to a specific platform via Zernio."""
        if not self.zernio:
            return {
                "success": False,
                "platform": platform,
                "error": "Zernio not configured. Set ZERNIO_API_KEY to enable social posting."
            }
        
        try:
            zernio_platform = ZernioService.map_platform_to_zernio(platform)
            result = await self.zernio.post_clip(
                video_url=video_url,
                caption=caption,
                platforms=[zernio_platform],
                hashtags=hashtags,
                title=title
            )
            
            # Extract platform-specific result
            platform_result = next(
                (p for p in result.get("platforms", []) 
                 if ZernioService.map_zernio_to_platform(p.get("platform", "")) == platform),
                None
            )
            
            if platform_result and platform_result.get("success"):
                return {
                    "success": True,
                    "platform": platform,
                    "post_id": platform_result.get("post_id"),
                    "post_url": platform_result.get("post_url"),
                    "status": "published"
                }
            else:
                return {
                    "success": False,
                    "platform": platform,
                    "error": platform_result.get("error") if platform_result else "Unknown error"
                }
                
        except Exception as e:
            return {
                "success": False,
                "platform": platform,
                "error": str(e)
            }
    
    async def post_to_multiple_platforms(
        self,
        clip_id: str,
        video_url: str,
        caption: str,
        platforms: List[str],
        hashtags: List[str],
        title: str = ""
    ) -> Dict[str, Any]:
        """Post a clip to multiple platforms in one Zernio call."""
        if not self.zernio:
            return {
                "success": False,
                "error": "Zernio not configured. Set ZERNIO_API_KEY to enable social posting.",
                "platforms": {p: {"success": False, "error": "Zernio not configured"} for p in platforms}
            }
        
        try:
            zernio_platforms = [ZernioService.map_platform_to_zernio(p) for p in platforms]
            result = await self.zernio.post_clip(
                video_url=video_url,
                caption=caption,
                platforms=zernio_platforms,
                hashtags=hashtags,
                title=title
            )
            
            platform_results = {}
            for platform_result in result.get("platforms", []):
                platform_name = ZernioService.map_zernio_to_platform(platform_result.get("platform", ""))
                platform_results[platform_name] = {
                    "success": platform_result.get("success", False),
                    "post_id": platform_result.get("post_id"),
                    "post_url": platform_result.get("post_url"),
                    "status": "posted" if platform_result.get("success") else "failed",
                    "error": platform_result.get("error")
                }
            
            all_success = all(r.get("success", False) for r in platform_results.values())
            
            return {
                "success": all_success,
                "clip_id": clip_id,
                "zernio_post_id": result.get("post_id"),
                "platforms": platform_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "platforms": {p: {"success": False, "error": str(e)} for p in platforms}
            }
    
    async def schedule_post(
        self,
        clip_id: str,
        platform: str,
        scheduled_time: str
    ) -> Dict[str, Any]:
        """Schedule a clip to be posted at a specific time via Zernio."""
        if not self.zernio:
            return {
                "success": False,
                "error": "Zernio not configured. Set ZERNIO_API_KEY to enable scheduling."
            }
        
        try:
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return {"success": False, "error": "Clip not found"}
            
            zernio_platform = ZernioService.map_platform_to_zernio(platform)
            result = await self.zernio.post_clip(
                video_url=clip.get("video_url", ""),
                caption=clip.get("caption", ""),
                platforms=[zernio_platform],
                schedule_time=scheduled_time,
                hashtags=clip.get("tags", [])
            )
            
            return {
                "success": True,
                "clip_id": clip_id,
                "platform": platform,
                "scheduled_time": scheduled_time,
                "zernio_post_id": result.get("post_id"),
                "status": "scheduled"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """Check status of a posted clip via Zernio."""
        if not self.zernio:
            return {"error": "Zernio not configured"}
        
        try:
            return await self.zernio.get_post_status(post_id)
        except Exception as e:
            return {"error": str(e)}


class MetricsSyncService:
    """Sync metrics from social platforms via Zernio."""
    
    def __init__(self):
        self.zernio: Optional[ZernioService] = None
        try:
            self.zernio = ZernioService()
        except ValueError:
            self.zernio = None
    
    async def sync_platform_metrics(
        self,
        account_id: str,
        post_ids: Optional[List[str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get metrics for posts on a connected account via Zernio."""
        if not self.zernio:
            return {"error": "Zernio not configured. Set ZERNIO_API_KEY to enable metrics sync."}
        
        try:
            return await self.zernio.get_metrics(
                account_id=account_id,
                post_ids=post_ids,
                since=since,
                until=until
            )
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_post(self, post_id: str) -> Dict[str, Any]:
        """Delete a posted clip from platforms via Zernio."""
        if not self.zernio:
            return {"error": "Zernio not configured"}
        
        try:
            return await self.zernio.delete_post(post_id)
        except Exception as e:
            return {"error": str(e)}
