from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.auth import get_current_user
from app.services.stripe_service import StripeService
from app.core.config import settings

from app.services.database import SupabaseService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

stripe_service = StripeService()
db = SupabaseService()

TIER_PRICE_MAP = {
    "basic": settings.STRIPE_PRICE_BASIC,
    "pro": settings.STRIPE_PRICE_PRO,
    "premium": settings.STRIPE_PRICE_PRO,  # alias
    "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
}

class CheckoutRequest(BaseModel):
    tier: str

class CheckoutResponse(BaseModel):
    checkout_url: str

class PortalResponse(BaseModel):
    portal_url: str


def _get_base_url() -> str:
    """Return the first CORS origin as the app base URL for redirects."""
    origins = settings.CORS_ORIGINS
    for origin in origins:
        if origin and not origin.startswith("*"):
            return origin.rstrip("/")
    return "http://localhost:3000"


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest, user=Depends(get_current_user)):
    """Create a Stripe checkout session for a subscription tier."""
    price_id = TIER_PRICE_MAP.get(request.tier.lower())
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {request.tier}")

    customer = await stripe_service.create_customer(user.id, user.email)
    base_url = _get_base_url()

    session = await stripe_service.create_checkout_session(
        customer_id=customer["id"],
        price_id=price_id,
        success_url=f"{base_url}/profile/billing?success=true",
        cancel_url=f"{base_url}/profile/billing?canceled=true",
    )

    return {"checkout_url": session["url"]}


@router.post("/portal", response_model=PortalResponse)
async def create_portal(user=Depends(get_current_user)):
    """Create a Stripe customer portal session."""
    customer = await stripe_service.create_customer(user.id, user.email)
    base_url = _get_base_url()

    portal = await stripe_service.create_customer_portal_session(
        customer_id=customer["id"],
        return_url=f"{base_url}/profile/billing",
    )

    return {"portal_url": portal["url"]}


@router.post("/cancel")
async def cancel_subscription(user=Depends(get_current_user)):
    """Cancel the current subscription at period end."""
    try:
        subscription = await db.get_subscription(user.id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found.")
        
        stripe_sub_id = subscription.get("stripe_subscription_id")
        if not stripe_sub_id:
            raise HTTPException(status_code=400, detail="Subscription has no Stripe ID.")
        
        cancelled = await stripe_service.cancel_subscription(stripe_sub_id)
        
        # Update database record
        await db.update_subscription(user.id, {
            "status": "cancelling",
            "cancel_at_period_end": True,
            "current_period_end": cancelled.get("current_period_end"),
            "updated_at": "now()"
        })
        
        return {
            "success": True,
            "message": "Subscription scheduled to cancel at period end.",
            "cancel_at_period_end": True,
            "current_period_end": cancelled.get("current_period_end")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")
