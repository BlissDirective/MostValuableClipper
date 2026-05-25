import os
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from typing import Optional, List
from pydantic import BaseModel

from app.services.auth import get_current_user, get_user_db
from app.models import Platform
from app.services.database import SupabaseService
from app.services.zernio_service import ZernioService
from app.services.queue import CacheService
from app.core.encryption import encrypt_field, decrypt_field

router = APIRouter(prefix="/social", tags=["social"])

class ConnectAccountRequest(BaseModel):
    platform: Platform
    authorization_code: Optional[str] = None
    handle: Optional[str] = None

class ConnectManualRequest(BaseModel):
    platform: Platform
    handle: str

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

# Admin-scoped db for the callback (no user JWT available in callback)
_admin_db = SupabaseService()
_cache = CacheService()

OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8000")
APP_DEEP_LINK_SCHEME = os.getenv("APP_DEEP_LINK_SCHEME", "myapp")
_OAUTH_STATE_TTL = 600  # 10 minutes


def _state_key(nonce: str) -> str:
    return f"oauth_state:{nonce}"


@router.get("/oauth/{platform}", response_model=OAuthInitResponse)
async def get_oauth_url(
    platform: Platform,
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db),
):
    """Get Zernio OAuth URL for a platform.

    Generates a cryptographic state nonce and stores it in Redis (TTL 10 min)
    so the callback can verify which user initiated the OAuth flow — the
    callback never trusts user-supplied identity parameters.
    """
    if not zernio:
        raise HTTPException(
            status_code=503,
            detail="Zernio not configured. Set ZERNIO_API_KEY to enable social OAuth.",
        )

    try:
        # Generate a secure random nonce and store user_id against it
        nonce = secrets.token_urlsafe(32)
        await _cache.set(_state_key(nonce), user.id, ttl_seconds=_OAUTH_STATE_TTL)

        redirect_url = f"{OAUTH_REDIRECT_BASE}/api/v1/social/oauth/callback"

        result = await zernio.get_oauth_url(
            platform=platform.value,
            profile_id=user.id,
            redirect_url=redirect_url,
            state=nonce,  # Zernio passes state back to our callback
        )

        auth_url = result.get("authUrl") or result.get("auth_url") or result.get("url")
        if not auth_url:
            raise HTTPException(status_code=500, detail="Zernio did not return an auth URL")

        return {
            "auth_url": auth_url,
            "platform": platform.value,
            "message": f"Open this URL to connect your {platform.value} account.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth")


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    platform: Optional[str] = None,
    accountId: Optional[str] = None,
    handle: Optional[str] = None,
    username: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Handle OAuth callback from Zernio.

    The `state` parameter is a nonce generated in get_oauth_url and stored in
    Redis. We look it up to determine the user — we never trust profileId or
    any other user-supplied identity parameter in the callback URL.
    """
    if error:
        deep_link = f"{APP_DEEP_LINK_SCHEME}://social/callback?success=false&error={error}"
        return RedirectResponse(url=deep_link)

    # Validate the state nonce
    if not state:
        deep_link = f"{APP_DEEP_LINK_SCHEME}://social/callback?success=false&error=missing_state"
        return RedirectResponse(url=deep_link)

    user_id = await _cache.get(_state_key(state))
    if not user_id:
        deep_link = f"{APP_DEEP_LINK_SCHEME}://social/callback?success=false&error=invalid_state"
        return RedirectResponse(url=deep_link)

    # Consume the nonce — one-time use
    await _cache.delete(_state_key(state))

    if not accountId:
        deep_link = f"{APP_DEEP_LINK_SCHEME}://social/callback?success=false&error=missing_params"
        return RedirectResponse(url=deep_link)

    detected_platform = platform or "unknown"
    account_handle = handle or username or "unknown"

    try:
        existing = await _admin_db.list_social_accounts(user_id)
        target = next((a for a in existing if a.get("platform") == detected_platform), None)

        account_data = {
            "user_id": user_id,
            "platform": detected_platform,
            "handle": account_handle,
            "account_id": accountId,
            "access_token": None,  # Zernio manages tokens server-side
            "follower_count": 0,
            "connected_at": "now()",
            "last_synced_at": "now()",
        }

        if target:
            await _admin_db.update_social_account(
                target.get("id"),
                {
                    "handle": account_handle,
                    "account_id": accountId,
                    "connected_at": "now()",
                    "last_synced_at": "now()",
                },
            )
        else:
            await _admin_db.create_social_account(account_data)
    except Exception as db_err:
        import logging
        logging.getLogger(__name__).error(f"[oauth_callback] DB error: {db_err}")

    deep_link = (
        f"{APP_DEEP_LINK_SCHEME}://social/callback"
        f"?success=true&platform={detected_platform}&handle={account_handle}"
    )
    return RedirectResponse(url=deep_link)


@router.get("/accounts")
async def list_connected_accounts(
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db),
):
    """List all connected social accounts via Zernio."""
    try:
        if zernio:
            try:
                zernio_accounts = await zernio.list_connected_accounts()
                return {
                    "accounts": [
                        {
                            "id": a.get("id"),
                            "platform": ZernioService.map_zernio_to_platform(
                                a.get("platform", "")
                            ),
                            "handle": a.get("handle"),
                            "follower_count": a.get("follower_count", 0),
                            "connected": a.get("status") == "active",
                            "created_at": a.get("created_at"),
                            "connected_via": "zernio",
                        }
                        for a in zernio_accounts
                    ],
                    "source": "zernio",
                }
            except Exception:
                pass

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
                    "connected_via": "database",
                }
                for a in accounts
            ],
            "source": "database",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list accounts: {str(e)}")


@router.post("/connect")
async def connect_account(
    request: ConnectAccountRequest,
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db),
):
    """Connect a social account (manual / BYOK path)."""
    try:
        account = await db.create_social_account({
            "user_id": user.id,
            "platform": request.platform,
            "handle": request.handle,
            "status": "pending" if request.authorization_code else "active",
            # H-07: encrypt credential at rest
            "auth_code": encrypt_field(request.authorization_code),
            "created_at": "now()",
            "connected_via": "zernio" if request.authorization_code else "manual",
        })
        return {
            "success": True,
            "platform": request.platform,
            "account_id": account.get("id"),
            "message": "Account connected.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect account: {str(e)}")


@router.post("/connect-manual")
async def connect_account_manual(
    request: ConnectManualRequest,
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db),
):
    """Manually connect a social account by handle."""
    try:
        account = await db.create_social_account({
            "user_id": user.id,
            "platform": request.platform,
            "handle": request.handle,
            "status": "active",
            "auth_code": None,
            "created_at": "now()",
            "connected_via": "manual",
        })
        return {
            "success": True,
            "platform": request.platform,
            "account_id": account.get("id"),
            "handle": request.handle,
            "message": f"{request.platform} account @{request.handle} connected manually.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect account: {str(e)}")


@router.delete("/{platform}")
async def disconnect_account(
    platform: Platform,
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db),
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
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db),
):
    """Get metrics for a connected platform via Zernio."""
    try:
        accounts = await db.list_social_accounts(user.id)
        target = next((a for a in accounts if a.get("platform") == platform), None)
        if not target:
            raise HTTPException(status_code=404, detail="Account not connected")

        if zernio and target.get("zernio_account_id"):
            try:
                metrics = await zernio.get_metrics(
                    account_id=target.get("zernio_account_id"),
                    since=None,
                    until=None,
                )
                return {"platform": platform, "handle": target.get("handle"), "metrics": metrics, "source": "zernio"}
            except Exception:
                pass

        return {
            "platform": platform,
            "handle": target.get("handle"),
            "metrics": {
                "follower_count": target.get("follower_count", 0),
                "total_posts": target.get("total_posts", 0),
                "total_views": target.get("total_views", 0),
                "engagement_rate": target.get("engagement_rate", 0),
            },
            "source": "database",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/post/{clip_id}")
async def post_clip_to_social(
    clip_id: str,
    platforms: List[Platform],
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db),
):
    """Post a clip to social platforms via Zernio."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        video_url = clip.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="Clip has no video URL")

        if not zernio:
            raise HTTPException(
                status_code=503,
                detail="Zernio not configured. Set ZERNIO_API_KEY to enable social posting.",
            )

        zernio_platforms = [ZernioService.map_platform_to_zernio(p.value) for p in platforms]
        result = await zernio.post_clip(
            video_url=video_url,
            caption=clip.get("caption", ""),
            platforms=zernio_platforms,
            hashtags=clip.get("tags", []),
        )

        platform_posts = {}
        for pr in result.get("platforms", []):
            pname = ZernioService.map_zernio_to_platform(pr.get("platform", ""))
            platform_posts[pname] = {
                "platform": pname,
                "post_id": pr.get("post_id"),
                "post_url": pr.get("post_url"),
                "status": "posted" if pr.get("success") else "failed",
                "metrics": {},
            }

        await db.update_clip(clip_id, {
            "platform_posts": platform_posts,
            "status": "posted",
            "posted_at": "now()",
        })

        return {
            "success": True,
            "clip_id": clip_id,
            "platforms": platform_posts,
            "zernio_post_id": result.get("post_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to post clip: {str(e)}")
