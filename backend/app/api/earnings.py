from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timedelta

from app.models import EarningsSummary
from app.services.auth import get_current_user, get_user_db
from app.services.stripe_service import StripeService
from app.services.database import SupabaseService

router = APIRouter(prefix="/earnings", tags=["earnings"])

from app.services.earnings_service import earnings_service

stripe_service = StripeService()

@router.get("")
async def get_earnings(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    platform: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Get earnings for a date range."""
    try:
        result = await earnings_service.get_computed_earnings(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            platform=platform
        )
        return result
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
        
        result = await earnings_service.get_computed_earnings(
            user_id=user.id,
            start_date=period_start.isoformat(),
            end_date=now.isoformat()
        )
        
        total_revenue = result["summary"]["total_revenue_usd"]
        total_views = result["summary"]["total_views"]
        by_platform = result["summary"]["by_platform"]
        
        return EarningsSummary(
            total_earnings=total_revenue,
            pending_earnings=0,
            paid_earnings=0,
            total_clips_monetized=len(result["items"]),
            by_platform=by_platform
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
        
        lifetime = await earnings_service.get_computed_earnings(
            user_id=user.id,
            start_date="1970-01-01T00:00:00",
            end_date=now.isoformat()
        )
        current_month = await earnings_service.get_computed_earnings(
            user_id=user.id,
            start_date=month_start.isoformat(),
            end_date=now.isoformat()
        )
        
        return {
            "lifetime_revenue_usd": lifetime["summary"]["total_revenue_usd"],
            "lifetime_views": lifetime["summary"]["total_views"],
            "current_month": {
                "revenue_usd": current_month["summary"]["total_revenue_usd"],
                "views": current_month["summary"]["total_views"],
                "platforms": list(current_month["summary"]["by_platform"].keys())
            },
            "by_platform": lifetime["summary"]["by_platform"],
            "rpm_ranges": lifetime["summary"]["rpm_ranges"],
            "recent_payments": [],
            "projected_monthly": current_month["summary"]["total_revenue_usd"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

@router.post("/withdrawal")
async def request_withdrawal(
    amount: float,
    method: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Request a payout/withdrawal."""
    try:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        # Get computed earnings to validate balance
        earnings = await earnings_service.get_computed_earnings(user_id=user.id)
        available = earnings["summary"]["total_revenue_usd"]
        
        if amount > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Available: ${available:.2f}, Requested: ${amount:.2f}"
            )
        
        # Store withdrawal request
        record = await db.create_earning({
            "user_id": user.id,
            "amount": -amount,  # Negative for withdrawal
            "currency": "USD",
            "platform": method,
            "period": "withdrawal",
            "source": "withdrawal_request",
            "status": "pending",
            "created_at": "now()",
            "updated_at": "now()"
        })
        
        return {
            "success": True,
            "user_id": user.id,
            "amount": amount,
            "method": method,
            "status": "pending",
            "available_balance": available,
            "request_id": record.get("id")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Withdrawal request failed: {str(e)}")
