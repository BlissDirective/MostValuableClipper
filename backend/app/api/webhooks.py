from fastapi import APIRouter, Request, HTTPException, status
from typing import Dict, Any
import logging

from app.core.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    # TODO: Verify webhook signature
    # TODO: Handle events:
    # - checkout.session.completed
    # - invoice.paid
    # - invoice.payment_failed
    # - customer.subscription.updated
    # - customer.subscription.deleted
    
    logger.info("Received Stripe webhook")
    return {"status": "received"}

@router.post("/tiktok")
async def tiktok_webhook(request: Request):
    """Handle TikTok webhook events (video posts, metrics updates)."""
    payload = await request.json()
    logger.info(f"Received TikTok webhook: {payload}")
    # TODO: Implement
    return {"status": "received"}

@router.post("/instagram")
async def instagram_webhook(request: Request):
    """Handle Instagram webhook events."""
    payload = await request.json()
    logger.info(f"Received Instagram webhook: {payload}")
    # TODO: Implement
    return {"status": "received"}
