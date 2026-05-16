from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel

from app.services.auth import get_current_user
from app.models import Platform
from app.services.database import SupabaseService

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

@router.get("/accounts")
async def list_connected_accounts(user = Depends(get_current_user)):
    """List all connected social accounts."""
    try:
        accounts = await db.list_social_accounts(user.id)
        return {
            "accounts": [
                {
                    "id": a.get("id"),
                    "platform": a.get("platform"),
                    "handle": a.get("handle"),
                    "follower_count": a.get("follower_count", 0),
                    "connected": a.get("status") == "active",
                    "created_at": a.get("created_at")
                }
                for a in accounts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list accounts: {str(e)}")

@router.post("/connect")
async def connect_account(
    request: ConnectAccountRequest,
    user = Depends(get_current_user)
):
    """Connect a new social media account.
    
    Note: Full OAuth flow requires platform-specific developer accounts and tokens.
    This endpoint stores the connection intent; actual OAuth redirect handling is TBD.
    """
    try:
        # Store the connection request
        account = await db.create_social_account({
            "user_id": user.id,
            "platform": request.platform,
            "handle": request.handle,
            "status": "pending",
            "auth_code": request.authorization_code,
            "created_at": "now()"
        })
        return {"success": True, "platform": request.platform, "account_id": account.get("id")}
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
    """Get metrics for a connected platform."""
    try:
        accounts = await db.list_social_accounts(user.id)
        target = next((a for a in accounts if a.get("platform") == platform), None)
        if not target:
            raise HTTPException(status_code=404, detail="Account not connected")
        
        return {
            "platform": platform,
            "handle": target.get("handle"),
            "metrics": {
                "follower_count": target.get("follower_count", 0),
                "total_posts": target.get("total_posts", 0),
                "total_views": target.get("total_views", 0),
                "engagement_rate": target.get("engagement_rate", 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")
