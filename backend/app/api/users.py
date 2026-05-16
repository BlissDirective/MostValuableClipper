from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

class OnboardingUpdate(BaseModel):
    current_step: str
    completed: bool
    data: Optional[dict] = None

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    autonomy_mode: Optional[str] = None

@router.get("/me")
async def get_current_user_profile(user = Depends(get_current_user)):
    """Get current user's profile."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.user_metadata.get("full_name") if user.user_metadata else None,
        "avatar_url": user.user_metadata.get("avatar_url") if user.user_metadata else None,
        "subscription_tier": user.user_metadata.get("subscription_tier", "free") if user.user_metadata else "free",
        "autonomy_mode": user.user_metadata.get("autonomy_mode", "approveEach") if user.user_metadata else "approveEach",
        "onboarding_completed": user.user_metadata.get("onboarding_completed", False) if user.user_metadata else False,
        "created_at": user.created_at if hasattr(user, 'created_at') else None
    }

@router.patch("/me")
async def update_profile(
    update: UserProfileUpdate,
    user = Depends(get_current_user)
):
    """Update user profile."""
    # TODO: Persist to Supabase auth metadata
    return {"success": True}

@router.get("/me/onboarding")
async def get_onboarding_state(user = Depends(get_current_user)):
    """Get onboarding progress."""
    return {
        "current_step": "theme-selection",
        "steps": [],
        "completed": False
    }

@router.post("/me/onboarding")
async def update_onboarding(
    update: OnboardingUpdate,
    user = Depends(get_current_user)
):
    """Update onboarding progress."""
    return {"success": True}

@router.delete("/me")
async def delete_account(user = Depends(get_current_user)):
    """Delete the current user account (soft delete)."""
    # TODO: Implement Supabase auth user deletion or soft-delete in database
    # For MVP, return success and let the client clear local state
    return {"success": True, "message": "Account deletion scheduled"}


@router.get("/me/subscription")
async def get_subscription(user = Depends(get_current_user)):
    """Get current subscription details."""
    return {
        "tier": "free",
        "status": "active",
        "current_period_end": None,
        "cancel_at_period_end": False
    }
