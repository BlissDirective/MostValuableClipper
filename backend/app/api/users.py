from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.services.auth import get_current_user
from app.services.database import SupabaseService

router = APIRouter(prefix="/users", tags=["users"])
db = SupabaseService()

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
    try:
        profile = await db.get_profile(user.id)
        if profile:
            return {
                "id": user.id,
                "email": user.email,
                "full_name": profile.get("full_name"),
                "avatar_url": profile.get("avatar_url"),
                "subscription_tier": profile.get("subscription_tier", "free"),
                "autonomy_mode": profile.get("autonomy_mode", "approveEach"),
                "onboarding_completed": profile.get("onboarding_completed", False),
                "created_at": profile.get("created_at")
            }
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

@router.patch("/me")
async def update_profile(
    update: UserProfileUpdate,
    user = Depends(get_current_user)
):
    """Update user profile."""
    try:
        update_data = update.model_dump(exclude_unset=True)
        if update_data:
            await db.update_profile(user.id, update_data)
        return {"success": True, "updated": update_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

@router.get("/me/onboarding")
async def get_onboarding_state(user = Depends(get_current_user)):
    """Get onboarding progress."""
    try:
        profile = await db.get_profile(user.id)
        if profile:
            return {
                "current_step": profile.get("onboarding_step", "theme-selection"),
                "steps": profile.get("onboarding_steps", []),
                "completed": profile.get("onboarding_completed", False)
            }
        return {
            "current_step": "theme-selection",
            "steps": [],
            "completed": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get onboarding state: {str(e)}")

@router.post("/me/onboarding")
async def update_onboarding(
    update: OnboardingUpdate,
    user = Depends(get_current_user)
):
    """Update onboarding progress."""
    try:
        await db.update_profile(user.id, {
            "onboarding_step": update.current_step,
            "onboarding_completed": update.completed,
            "onboarding_data": update.data
        })
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update onboarding: {str(e)}")

@router.delete("/me")
async def delete_account(user = Depends(get_current_user)):
    """Delete the current user account (soft delete)."""
    try:
        await db.delete_profile(user.id)
        return {"success": True, "message": "Account deletion scheduled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")


@router.get("/me/export")
async def export_user_data(user = Depends(get_current_user)):
    """Export all user data as JSON (GDPR/CCPA data portability)."""
    try:
        profile = await db.get_profile(user.id)
        pipelines = await db.list_pipelines(user.id)
        clips = await db.list_clips(user_id=user.id, limit=10000)
        sources = await db.list_sources(user.id)
        subscription = await db.get_subscription(user.id)
        
        export_data = {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": profile.get("full_name") if profile else None,
                "created_at": user.created_at if hasattr(user, 'created_at') else None,
            },
            "profile": profile,
            "pipelines": pipelines.get("items", []),
            "clips": clips.get("items", []),
            "sources": sources.get("items", []),
            "subscription": subscription,
            "export_generated_at": datetime.utcnow().isoformat(),
        }
        
        return export_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")

@router.get("/me/subscription")
async def get_subscription(user = Depends(get_current_user)):
    """Get current subscription details."""
    try:
        subscription = await db.get_subscription(user.id)
        if subscription:
            return {
                "tier": subscription.get("tier", "free"),
                "status": subscription.get("status", "active"),
                "current_period_end": subscription.get("current_period_end"),
                "cancel_at_period_end": subscription.get("cancel_at_period_end", False)
            }
        return {
            "tier": "free",
            "status": "active",
            "current_period_end": None,
            "cancel_at_period_end": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subscription: {str(e)}")
