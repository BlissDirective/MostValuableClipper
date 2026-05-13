from fastapi import APIRouter, Request, HTTPException, status
from typing import Dict, Any
import logging
import json

from app.core.config import settings
from app.services.stripe_service import StripeService
from app.services.database import SupabaseService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

stripe_service = StripeService()
db = SupabaseService()

@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    try:
        # Verify and construct event
        event = await stripe_service.construct_webhook_event(payload, sig_header)
        
        event_type = event["type"]
        event_data = event["data"]["object"]
        
        logger.info(f"[Stripe Webhook] Received: {event_type}")
        
        # Handle specific events
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(event_data)
        elif event_type == "invoice.paid":
            await _handle_invoice_paid(event_data)
        elif event_type == "invoice.payment_failed":
            await _handle_invoice_failed(event_data)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event_data)
        else:
            logger.info(f"[Stripe Webhook] Unhandled event type: {event_type}")
        
        return {"status": "received", "type": event_type}
        
    except Exception as e:
        logger.error(f"[Stripe Webhook] Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

async def _handle_checkout_completed(session: Dict[str, Any]):
    """Handle checkout.session.completed."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    
    logger.info(f"[Stripe] Checkout completed for customer: {customer_id}")
    
    # TODO: Update user subscription in database
    # await db.update_subscription(customer_id, {
    #     "stripe_subscription_id": subscription_id,
    #     "status": "active"
    # })

async def _handle_invoice_paid(invoice: Dict[str, Any]):
    """Handle invoice.paid."""
    customer_id = invoice.get("customer")
    
    logger.info(f"[Stripe] Invoice paid for customer: {customer_id}")
    
    # TODO: Record payment, update subscription status

async def _handle_invoice_failed(invoice: Dict[str, Any]):
    """Handle invoice.payment_failed."""
    customer_id = invoice.get("customer")
    
    logger.warning(f"[Stripe] Invoice payment failed for customer: {customer_id}")
    
    # TODO: Update subscription status, notify user

async def _handle_subscription_updated(subscription: Dict[str, Any]):
    """Handle customer.subscription.updated."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    
    logger.info(f"[Stripe] Subscription updated: {customer_id} -> {status}")
    
    # TODO: Update subscription status in database

async def _handle_subscription_deleted(subscription: Dict[str, Any]):
    """Handle customer.subscription.deleted."""
    customer_id = subscription.get("customer")
    
    logger.info(f"[Stripe] Subscription cancelled: {customer_id}")
    
    # TODO: Mark subscription as cancelled, downgrade user to free tier

@router.post("/tiktok")
async def tiktok_webhook(request: Request):
    """Handle TikTok webhook events (video posts, metrics updates)."""
    payload = await request.json()
    logger.info(f"[TikTok Webhook] Received: {payload}")
    
    # TODO: Handle video published, metrics updated events
    
    return {"status": "received"}

@router.post("/instagram")
async def instagram_webhook(request: Request):
    """Handle Instagram webhook events."""
    payload = await request.json()
    logger.info(f"[Instagram Webhook] Received: {payload}")
    
    # TODO: Handle media published, insights updated events
    
    return {"status": "received"}

@router.get("/instagram")
async def instagram_webhook_verify(
    hub_mode: str,
    hub_verify_token: str,
    hub_challenge: str
):
    """Verify Instagram webhook subscription."""
    # Instagram sends a verification challenge during setup
    if hub_mode == "subscribe":
        return hub_challenge
    
    return {"status": "ok"}
