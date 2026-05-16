from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timedelta

from app.models import Earnings, EarningsSummary
from app.services.auth import get_current_user
from app.services.stripe_service import StripeService
from app.services.database import SupabaseService

router = APIRouter(prefix="/earnings", tags=["earnings"])

stripe_service = StripeService()
db = SupabaseService()

@router.get("")
async def get_earnings(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    platform: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Get earnings for a date range."""
    try:
        earnings = await db.get_earnings(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            platform=platform
        )
        
        total = sum(e.get("amount", 0) for e in earnings)
        total_views = sum(e.get("views", 0) for e in earnings)
        by_platform = {}
        for e in earnings:
            p = e.get("platform", "unknown")
            by_platform[p] = by_platform.get(p, 0) + e.get("amount", 0)
        
        return {
            "items": earnings,
            "summary": {
                "total_revenue_cents": int(total * 100),
                "total_views": total_views,
                "by_platform": by_platform
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get earnings: {str(e)}")

@router.get("/summary")
async def get_earnings_summary(
    period: str = "month",
    user = Depends(get_current_user)
):
    """Get earnings summary for the current period."""
    try:
        now = datetime.now()
        if period == "week":
            period_start = now - timedelta(days=7)
        elif period == "month":
            period_start = now - timedelta(days=30)
        elif period == "year":
            period_start = now - timedelta(days=365)
        else:
            period_start = now - timedelta(days=30)
        
        summary = await db.get_earnings_summary(
            user_id=user.id,
            period_start=period_start.isoformat(),
            period_end=now.isoformat()
        )
        
        return EarningsSummary(
            total_earnings=summary.get("total_revenue_cents", 0) / 100,
            pending_earnings=0,
            paid_earnings=0,
            total_clips_monetized=len(await db.get_earnings(user.id, period_start.isoformat(), now.isoformat())),
            by_platform=summary.get("by_platform", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")

@router.get("/dashboard")
async def get_earnings_dashboard(
    user = Depends(get_current_user)
):
    """Get full earnings dashboard data."""
    try:
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        lifetime = await db.get_earnings_summary(user.id, "1970-01-01T00:00:00", now.isoformat())
        current_month = await db.get_earnings_summary(user.id, month_start.isoformat(), now.isoformat())
        
        return {
            "lifetime_revenue_cents": lifetime.get("total_revenue_cents", 0),
            "lifetime_views": lifetime.get("total_views", 0),
            "current_month": {
                "revenue_cents": current_month.get("total_revenue_cents", 0),
                "views": current_month.get("total_views", 0),
                "platforms": list(current_month.get("by_platform", {}).keys())
            },
            "recent_payments": [],
            "projected_monthly": current_month.get("total_revenue_cents", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

@router.post("/withdrawal")
async def request_withdrawal(
    amount: float,
    method: str,
    user = Depends(get_current_user)
):
    """Request a payout/withdrawal."""
    try:
        return {
            "success": True,
            "user_id": user.id,
            "amount": amount,
            "method": method,
            "status": "pending"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Withdrawal request failed: {str(e)}")
