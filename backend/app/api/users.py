from fastapi import APIRouter, Depends
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
    # TODO: Implement
    return {
        "id": user.id if hasattr(user, 'id') else None,
        "email": user.email if hasattr(user, 'email') else None,
        "subscription_tier": "free",
        "autonomy_mode": "approveEach",
        "onboarding_completed": False
    }

@router.patch("/me")
async def update_profile(
    update: UserProfileUpdate,
    user = Depends(get_current_user)
):
    """Update user profile."""
    # TODO: Implement
    return {"success": True}

@router.get("/me/onboarding")
async def get_onboarding_state(user = Depends(get_current_user)):
    """Get onboarding progress."""
    # TODO: Implement
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
    # TODO: Implement
    return {"success": True}

@router.get("/me/subscription")
async def get_subscription(user = Depends(get_current_user)):
    """Get current subscription details."""
    # TODO: Implement
    return {
        "tier": "free",
        "status": "active",
        "current_period_end": None,
        "cancel_at_period_end": False
    }
