from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from typing import Optional, List
from pydantic import BaseModel
import os

from app.services.auth import get_current_user
from app.models import Platform
from app.services.database import SupabaseService
from app.services.zernio_service import ZernioService

router = APIRouter(prefix="/social", tags=["social"])
db = SupabaseService()

class ConnectAccountRequest(BaseModel):
    platform: Platform
    authorization_code: Optional[str] = None
    handle: Optional[str] = None

class ConnectManualRequest(BaseModel):
    platform: Platform
    handle: str

class AccountResponse(BaseModel):
    platform: str
    handle: Optional[str]
    follower_count: int
    connected: bool

class OAuthInitResponse(BaseModel):
    auth_url: str
    platform: str
    message: str

# Initialize Zernio service if key is configured
zernio: Optional[ZernioService] = None
try:
    zernio = ZernioService()
except ValueError:
    zernio = None

# OAuth callback redirect URL — configured via env or defaults to API base
# In production, this should be your deployed API URL + /social/oauth/callback
# The callback then redirects to the mobile app via deep link
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8000")
APP_DEEP_LINK_SCHEME = os.getenv("APP_DEEP_LINK_SCHEME", "myapp")

@router.get("/oauth/{platform}", response_model=OAuthInitResponse)
async def get_oauth_url(
    platform: Platform,
    user = Depends(get_current_user)
):
    """Get Zernio OAuth URL for a platform.
    
    Frontend should open `auth_url` in a browser/WebBrowser.
    After user authorizes, Zernio redirects to our callback endpoint,
    which stores the account and redirects back to the app.
    """
    if not zernio:
        raise HTTPException(
            status_code=503,
            detail="Zernio not configured. Set ZERNIO_API_KEY to enable social OAuth."
        )
    
    try:
        # Use user ID as the Zernio profile ID (or a dedicated profile ID if stored)
        profile_id = user.id
        
        # Build callback URL — this is where Zernio redirects after OAuth
        redirect_url = f"{OAUTH_REDIRECT_BASE}/api/v1/social/oauth/callback"
        
        # Get OAuth URL from Zernio
        result = await zernio.get_oauth_url(
            platform=platform.value,
            profile_id=profile_id,
            redirect_url=redirect_url
        )
        
        auth_url = result.get("authUrl") or result.get("auth_url") or result.get("url")
        if not auth_url:
            raise HTTPException(
                status_code=500,
                detail="Zernio did not return an auth URL"
            )
        
        return {
            "auth_url": auth_url,
            "platform": platform.value,
            "message": f"Open this URL to connect your {platform.value} account."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get OAuth URL: {str(e)}")

@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    platform: Optional[str] = None,
    accountId: Optional[str] = None,
    handle: Optional[str] = None,
    username: Optional[str] = None,
    profileId: Optional[str] = None,
    connected: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Handle OAuth callback from Zernio.
    
    Zernio redirects here after the user completes authorization.
    We store the connected account and redirect back to the mobile app.
    """
    # Handle errors from Zernio
    if error:
        # Redirect to app with error
        deep_link = f"{APP_DEEP_LINK_SCHEME}://social/callback?success=false&error={error}"
        return RedirectResponse(url=deep_link)
    
    try:
        # Extract platform from query params or try to detect
        detected_platform = platform
        if not detected_platform:
            # Try to infer from connected param or other indicators
            detected_platform = "unknown"
        
        # Use handle or username
        account_handle = handle or username or "unknown"
        
        # Get user ID from profileId (we used user.id as profile_id)
        user_id = profileId
        
        if not user_id or not accountId:
            deep_link = f"{APP_DEEP_LINK_SCHEME}://social/callback?success=false&error=missing_params"
            return RedirectResponse(url=deep_link)
        
        # Store or update the social account
        try:
            # Check if account already exists
            existing = await db.list_social_accounts(user_id)
            target = next((a for a in existing if a.get("platform") == detected_platform), None)
            
            account_data = {
                "user_id": user_id,
                "platform": detected_platform,
                "handle": account_handle,
                "account_id": accountId,
                "access_token": None,  # Zernio manages tokens
                "follower_count": 0,
                "connected_at": "now()",
                "last_synced_at": "now()"
            }
            
            if target:
                # Update existing
                await db.update_social_account(target.get("id"), {
                    "handle": account_handle,
                    "account_id": accountId,
                    "connected_at": "now()",
                    "last_synced_at": "now()"
                })
            else:
                # Create new
                await db.create_social_account(account_data)
        except Exception as db_err:
            # Log but still redirect to app
            print(f"[oauth_callback] DB error: {db_err}")
        
        # Redirect to app with success
        deep_link = f"{APP_DEEP_LINK_SCHEME}://social/callback?success=true&platform={detected_platform}&handle={account_handle}"
        return RedirectResponse(url=deep_link)
        
    except Exception as e:
        deep_link = f"{APP_DEEP_LINK_SCHEME}://social/callback?success=false&error=server_error"
        return RedirectResponse(url=deep_link)

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
    
    If authorization_code is provided, Zernio handles OAuth flow.
    Otherwise, account is stored as manual/BYOK for later token exchange.
    """
    try:
        # Store the connection request
        account = await db.create_social_account({
            "user_id": user.id,
            "platform": request.platform,
            "handle": request.handle,
            "status": "pending" if request.authorization_code else "active",
            "auth_code": request.authorization_code,
            "created_at": "now()",
            "connected_via": "zernio" if request.authorization_code else "manual"
        })
        
        return {
            "success": True, 
            "platform": request.platform, 
            "account_id": account.get("id"),
            "message": "Account connected." if not request.authorization_code else "Account queued for Zernio OAuth. User will complete auth in Zernio dashboard."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect account: {str(e)}")

@router.post("/connect-manual")
async def connect_account_manual(
    request: ConnectManualRequest,
    user = Depends(get_current_user)
):
    """Manually connect a social account by handle (BYOK / manual entry).
    
    Used when OAuth is not available or user provides their own API keys.
    """
    try:
        account = await db.create_social_account({
            "user_id": user.id,
            "platform": request.platform,
            "handle": request.handle,
            "status": "active",
            "auth_code": None,
            "created_at": "now()",
            "connected_via": "manual"
        })
        
        return {
            "success": True,
            "platform": request.platform,
            "account_id": account.get("id"),
            "handle": request.handle,
            "message": f"{request.platform} account @{request.handle} connected manually."
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
