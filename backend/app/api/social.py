from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel

from app.services.auth import get_current_user
from app.models import Platform

router = APIRouter(prefix="/social", tags=["social"])

class ConnectAccountRequest(BaseModel):
    platform: Platform
    authorization_code: str

class AccountResponse(BaseModel):
    platform: str
    handle: Optional[str]
    follower_count: int
    connected: bool

@router.get("/accounts")
async def list_connected_accounts(user = Depends(get_current_user)):
    """List all connected social accounts."""
    # TODO: Implement
    return {"accounts": []}

@router.post("/connect")
async def connect_account(
    request: ConnectAccountRequest,
    user = Depends(get_current_user)
):
    """Connect a new social media account."""
    # TODO: Implement OAuth flow
    return {"success": True, "platform": request.platform}

@router.delete("/{platform}")
async def disconnect_account(
    platform: Platform,
    user = Depends(get_current_user)
):
    """Disconnect a social media account."""
    # TODO: Implement
    return {"success": True, "platform": platform}

@router.get("/{platform}/metrics")
async def get_platform_metrics(
    platform: Platform,
    user = Depends(get_current_user)
):
    """Get metrics for a connected platform."""
    # TODO: Implement
    return {"platform": platform, "metrics": {}}
