import hashlib
import hmac
from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import logging

import stripe

from app.core.config import settings
from app.services.stripe_service import StripeService
from app.services.database import SupabaseService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

stripe_service = StripeService()
db = SupabaseService()


def _verify_hmac_sha256(body: bytes, secret: str, signature_header: str) -> bool:
    """Verify an HMAC-SHA256 webhook signature of the form 'sha256=<hex>'."""
    if not secret:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. Real signing secret configured."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = await stripe_service.construct_webhook_event(payload, sig_header)
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"[Stripe Webhook] Invalid signature: {e}")
        raise HTTPException(status_code=403, detail="Invalid Stripe signature")
    except Exception as e:
        logger.error(f"[Stripe Webhook] Error constructing event: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event_type = event["type"]
    event_data = event["data"]["object"]

    logger.info(f"[Stripe Webhook] Received: {event_type}")

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


@router.post("/tiktok")
async def tiktok_webhook(request: Request):
    """Handle TikTok webhook events (video posts, metrics updates)."""
    body = await request.body()

    secret = settings.TIKTOK_WEBHOOK_SECRET
    if not secret:
        logger.warning("[TikTok Webhook] TIKTOK_WEBHOOK_SECRET not configured — rejecting")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    sig_header = request.headers.get("X-TikTok-Signature", "")
    if not _verify_hmac_sha256(body, secret, sig_header):
        logger.warning("[TikTok Webhook] Signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid TikTok webhook signature")

    try:
        payload = request.app.state  # parsed below after verification
        import json
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info(f"[TikTok Webhook] Received verified event")

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
    body = await request.body()

    secret = settings.INSTAGRAM_WEBHOOK_SECRET
    if not secret:
        logger.warning("[Instagram Webhook] INSTAGRAM_WEBHOOK_SECRET not configured — rejecting")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    sig_header = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_hmac_sha256(body, secret, sig_header):
        logger.warning("[Instagram Webhook] Signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid Instagram webhook signature")

    try:
        import json
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info("[Instagram Webhook] Received verified event")

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
    hub_challenge: str,
):
    """Verify Instagram webhook subscription challenge."""
    configured_token = settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN
    if not configured_token:
        logger.error("[Instagram Webhook] INSTAGRAM_WEBHOOK_VERIFY_TOKEN not configured")
        raise HTTPException(status_code=503, detail="Webhook verify token not configured")

    if hub_mode != "subscribe" or not hmac.compare_digest(hub_verify_token, configured_token):
        logger.warning("[Instagram Webhook] Verification failed — bad token or mode")
        raise HTTPException(status_code=403, detail="Verification failed")

    # Return plain string — Instagram requires this exact format
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(hub_challenge)


# ─── Stripe event handlers ────────────────────────────────────────────────────

async def _handle_checkout_completed(session: Dict[str, Any]):
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    logger.info(f"[Stripe] Checkout completed for customer: {customer_id}")
    try:
        await db.update_subscription(customer_id, {
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "status": "active",
            "tier": "pro",
            "updated_at": "now()"
        })
    except Exception as e:
        logger.error(f"[Stripe] Failed to update subscription: {e}")


async def _handle_invoice_paid(invoice: Dict[str, Any]):
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
