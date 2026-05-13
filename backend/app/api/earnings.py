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
        return {
            "items": [],
            "summary": {
                "total_revenue_cents": 0,
                "total_views": 0,
                "by_platform": {}
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
        # TODO: Query actual earnings from database
        return EarningsSummary(
            total_revenue_cents=0,
            total_views=0,
            by_platform={},
            period_start=(datetime.now() - timedelta(days=30)).isoformat(),
            period_end=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")

@router.get("/dashboard")
async def get_earnings_dashboard(
    user = Depends(get_current_user)
):
    """Get full earnings dashboard data."""
    try:
        return {
            "lifetime_revenue_cents": 0,
            "lifetime_views": 0,
            "current_month": {
                "revenue_cents": 0,
                "views": 0,
                "platforms": []
            },
            "recent_payments": [],
            "projected_monthly": 0
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
