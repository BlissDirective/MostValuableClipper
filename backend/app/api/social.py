from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel

from app.services.auth import get_current_user
from app.models import Platform
from app.services.database import SupabaseService
from app.services.zernio_service import ZernioService

router = APIRouter(prefix="/social", tags=["social"])
db = SupabaseService()

class ConnectAccountRequest(BaseModel):
    platform: Platform
    authorization_code: str
    handle: Optional[str] = None

class AccountResponse(BaseModel):
    platform: str
    handle: Optional[str]
    follower_count: int
    connected: bool

# Initialize Zernio service if key is configured
zernio: Optional[ZernioService] = None
try:
    zernio = ZernioService()
except ValueError:
    zernio = None

@router.get("/accounts")
async def list_connected_accounts(user = Depends(get_current_user)):
    """List all connected social accounts via Zernio."""
    try:
        # If Zernio is configured, fetch live accounts from their API
        if zernio:
            try:
                zernio_accounts = await zernio.list_connected_accounts()
                return {
                    "accounts": [
                        {
                            "id": a.get("id"),
                            "platform": ZernioService.map_zernio_to_platform(a.get("platform", "")),
                            "handle": a.get("handle"),
                            "follower_count": a.get("follower_count", 0),
                            "connected": a.get("status") == "active",
                            "created_at": a.get("created_at"),
                            "connected_via": "zernio"
                        }
                        for a in zernio_accounts
                    ],
                    "source": "zernio"
                }
            except Exception as e:
                # Fall back to database if Zernio API fails
                pass
        
        # Fallback: get from database
        accounts = await db.list_social_accounts(user.id)
        return {
            "accounts": [
                {
                    "id": a.get("id"),
                    "platform": a.get("platform"),
                    "handle": a.get("handle"),
                    "follower_count": a.get("follower_count", 0),
                    "connected": a.get("status") == "active",
                    "created_at": a.get("created_at"),
                    "connected_via": "database"
                }
                for a in accounts
            ],
            "source": "database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list accounts: {str(e)}")

@router.post("/connect")
async def connect_account(
    request: ConnectAccountRequest,
    user = Depends(get_current_user)
):
    """Connect a new social media account via Zernio.
    
    Zernio handles OAuth flow — users authenticate directly with Zernio,
    which returns an account ID we store in our database.
    """
    try:
        # Store the connection request
        account = await db.create_social_account({
            "user_id": user.id,
            "platform": request.platform,
            "handle": request.handle,
            "status": "pending",
            "auth_code": request.authorization_code,
            "created_at": "now()",
            "connected_via": "zernio"
        })
        
        return {
            "success": True, 
            "platform": request.platform, 
            "account_id": account.get("id"),
            "message": "Account queued for Zernio OAuth. User will complete auth in Zernio dashboard."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect account: {str(e)}")

@router.delete("/{platform}")
async def disconnect_account(
    platform: Platform,
    user = Depends(get_current_user)
):
    """Disconnect a social media account."""
    try:
        accounts = await db.list_social_accounts(user.id)
        target = next((a for a in accounts if a.get("platform") == platform), None)
        if not target:
            raise HTTPException(status_code=404, detail="Account not found")
        
        success = await db.delete_social_account(target.get("id"))
        return {"success": success, "platform": platform}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect account: {str(e)}")

@router.get("/{platform}/metrics")
async def get_platform_metrics(
    platform: Platform,
    user = Depends(get_current_user)
):
    """Get metrics for a connected platform via Zernio."""
    try:
        accounts = await db.list_social_accounts(user.id)
        target = next((a for a in accounts if a.get("platform") == platform), None)
        if not target:
            raise HTTPException(status_code=404, detail="Account not connected")
        
        # If Zernio is configured, fetch live metrics
        if zernio and target.get("zernio_account_id"):
            try:
                metrics = await zernio.get_metrics(
                    account_id=target.get("zernio_account_id"),
                    since=None,
                    until=None
                )
                return {
                    "platform": platform,
                    "handle": target.get("handle"),
                    "metrics": metrics,
                    "source": "zernio"
                }
            except Exception:
                pass
        
        # Fallback to database metrics
        return {
            "platform": platform,
            "handle": target.get("handle"),
            "metrics": {
                "follower_count": target.get("follower_count", 0),
                "total_posts": target.get("total_posts", 0),
                "total_views": target.get("total_views", 0),
                "engagement_rate": target.get("engagement_rate", 0)
            },
            "source": "database"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.post("/post/{clip_id}")
async def post_clip_to_social(
    clip_id: str,
    platforms: List[Platform],
    user = Depends(get_current_user)
):
    """Post a clip to social platforms via Zernio."""
    try:
        # Get clip details
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        video_url = clip.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="Clip has no video URL")
        
        # Map platforms to Zernio format
        zernio_platforms = [ZernioService.map_platform_to_zernio(p.value) for p in platforms]
        
        if not zernio:
            raise HTTPException(
                status_code=503, 
                detail="Zernio not configured. Set ZERNIO_API_KEY to enable social posting."
            )
        
        # Post via Zernio
        result = await zernio.post_clip(
            video_url=video_url,
            caption=clip.get("caption", ""),
            platforms=zernio_platforms,
            hashtags=clip.get("tags", [])
        )
        
        # Update clip with post IDs
        platform_posts = {}
        for platform_result in result.get("platforms", []):
            platform_name = ZernioService.map_zernio_to_platform(platform_result.get("platform", ""))
            platform_posts[platform_name] = {
                "platform": platform_name,
                "post_id": platform_result.get("post_id"),
                "post_url": platform_result.get("post_url"),
                "status": "posted" if platform_result.get("success") else "failed",
                "metrics": {}
            }
        
        await db.update_clip(clip_id, {
            "platform_posts": platform_posts,
            "status": "posted",
            "posted_at": "now()"
        })
        
        return {
            "success": True,
            "clip_id": clip_id,
            "platforms": platform_posts,
            "zernio_post_id": result.get("post_id")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to post clip: {str(e)}")
