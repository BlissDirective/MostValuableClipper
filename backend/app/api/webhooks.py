from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import logging

from app.services.stripe_service import StripeService
from app.services.database import SupabaseService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

stripe_service = StripeService()
db = SupabaseService()

@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. Real signing secret configured."""
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
    
    # Update or create subscription record
    try:
        await db.update_subscription(customer_id, {
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "status": "active",
            "tier": "pro",  # Derive from session if available
            "updated_at": "now()"
        })
    except Exception as e:
        logger.error(f"[Stripe] Failed to update subscription: {e}")

async def _handle_invoice_paid(invoice: Dict[str, Any]):
    """Handle invoice.paid."""
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    
    logger.info(f"[Stripe] Invoice paid for customer: {customer_id}")
    
    try:
        await db.update_subscription(customer_id, {
            "status": "active",
            "stripe_subscription_id": subscription_id,
            "last_payment_status": "paid",
            "updated_at": "now()"
        })
    except Exception as e:
        logger.error(f"[Stripe] Failed to record payment: {e}")

async def _handle_invoice_failed(invoice: Dict[str, Any]):
    """Handle invoice.payment_failed."""
    customer_id = invoice.get("customer")
    
    logger.warning(f"[Stripe] Invoice payment failed for customer: {customer_id}")
    
    try:
        await db.update_subscription(customer_id, {
            "status": "past_due",
            "last_payment_status": "failed",
            "updated_at": "now()"
        })
    except Exception as e:
        logger.error(f"[Stripe] Failed to update subscription status: {e}")

async def _handle_subscription_updated(subscription: Dict[str, Any]):
    """Handle customer.subscription.updated."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    
    logger.info(f"[Stripe] Subscription updated: {customer_id} -> {status}")
    
    try:
        await db.update_subscription(customer_id, {
            "status": status,
            "current_period_end": subscription.get("current_period_end"),
            "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
            "updated_at": "now()"
        })
    except Exception as e:
        logger.error(f"[Stripe] Failed to update subscription: {e}")

async def _handle_subscription_deleted(subscription: Dict[str, Any]):
    """Handle customer.subscription.deleted."""
    customer_id = subscription.get("customer")
    
    logger.info(f"[Stripe] Subscription cancelled: {customer_id}")
    
    try:
        await db.update_subscription(customer_id, {
            "status": "cancelled",
            "tier": "free",
            "cancel_at_period_end": False,
            "updated_at": "now()"
        })
    except Exception as e:
        logger.error(f"[Stripe] Failed to mark subscription cancelled: {e}")

@router.post("/tiktok")
async def tiktok_webhook(request: Request):
    """Handle TikTok webhook events (video posts, metrics updates)."""
    payload = await request.json()
    logger.info(f"[TikTok Webhook] Received: {payload}")
    
    # Store webhook payload for processing
    try:
        await db.store_analytics_event({
            "event_type": "tiktok_webhook",
            "event_data": payload,
            "created_at": "now()"
        })
    except Exception as e:
        logger.error(f"[TikTok Webhook] Failed to store: {e}")
    
    return {"status": "received"}

@router.post("/instagram")
async def instagram_webhook(request: Request):
    """Handle Instagram webhook events."""
    payload = await request.json()
    logger.info(f"[Instagram Webhook] Received: {payload}")
    
    # Store webhook payload for processing
    try:
        await db.store_analytics_event({
            "event_type": "instagram_webhook",
            "event_data": payload,
            "created_at": "now()"
        })
    except Exception as e:
        logger.error(f"[Instagram Webhook] Failed to store: {e}")
    
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
