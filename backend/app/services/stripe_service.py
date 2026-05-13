import stripe
from typing import Optional, Dict, Any, List
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    """Stripe payment processing service."""
    
    @staticmethod
    async def create_customer(user_id: str, email: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a Stripe customer."""
        customer = stripe.Customer.create(
            email=email,
            name=name or email,
            metadata={"supabase_user_id": user_id}
        )
        return customer
    
    @staticmethod
    async def create_subscription(customer_id: str, price_id: str) -> Dict[str, Any]:
        """Create a subscription."""
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"]
        )
        return subscription
    
    @staticmethod
    async def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a checkout session."""
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"price_id": price_id}
        )
        return session
    
    @staticmethod
    async def cancel_subscription(subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription at period end."""
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        return subscription
    
    @staticmethod
    async def get_customer_subscriptions(customer_id: str) -> List[Dict[str, Any]]:
        """Get all subscriptions for a customer."""
        subscriptions = stripe.Subscription.list(customer=customer_id)
        return subscriptions.data
    
    @staticmethod
    async def construct_webhook_event(payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Verify and construct webhook event."""
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    
    @staticmethod
    async def create_product(name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a Stripe product."""
        product = stripe.Product.create(
            name=name,
            description=description
        )
        return product
    
    @staticmethod
    async def create_price(
        product_id: str,
        unit_amount_cents: int,
        currency: str = "usd",
        interval: str = "month"
    ) -> Dict[str, Any]:
        """Create a price for a product."""
        price = stripe.Price.create(
            product=product_id,
            unit_amount=unit_amount_cents,
            currency=currency,
            recurring={"interval": interval}
        )
        return price
