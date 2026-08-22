"""
utils/stripe_manager.py
-------------------------
Thin wrapper around the Stripe SDK - the only place in the app that talks to
Stripe directly (see CLAUDE.md separation: Routes -> Services -> Stripe -> Database).

Callers never see `stripe`'s own exception types - StripeManagerError is
raised instead, so routes/services don't need to import the `stripe` package.
"""

import logging

import stripe

import extensions as ext
from models.order import Order

logger = logging.getLogger(__name__)


class StripeManagerError(Exception):
    """Raised when a Stripe API call fails."""


class StripeManager:
    def __init__(self) -> None:
        self.config = ext.config
        if self.config.STRIPE_ENABLED:
            stripe.api_key = self.config.STRIPE_SECRET_KEY

    def create_checkout_session(self, order: Order, success_url: str, cancel_url: str) -> "stripe.checkout.Session":
        """
        Create a Stripe Checkout Session for *order*.

        Every amount comes from the order's own line items - themselves built
        server-side in OrderService.create_pending_order from ext.config, never
        from anything the client could have sent.
        """
        line_items = [
            {
                "price_data": {
                    "currency": order.currency,
                    "product_data": {"name": item.product_name},
                    "unit_amount": item.unit_price_cents,
                },
                "quantity": item.quantity,
            }
            for item in order.items
        ]

        try:
            return stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                shipping_address_collection={
                    "allowed_countries": self.config.STRIPE_SHIPPING_ALLOWED_COUNTRIES,
                },
                # Managed Payments (a Stripe account-level feature) is
                # incompatible with shipping_address_collection - disable it
                # for this session so the classic Checkout shipping flow works.
                managed_payments={"enabled": False},
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(order.id),
                metadata={"order_id": str(order.id)},
            )
        except stripe.error.StripeError as e:
            logger.error("Stripe error creating checkout session for order %d: %s", order.id, str(e))
            raise StripeManagerError("Unable to create Stripe checkout session") from e

    def expire_checkout_session(self, session_id: str) -> None:
        """
        Best-effort invalidation of a Checkout Session that must no longer be
        payable - used when a pending order carrying it is cancelled.

        Without this, a customer who still has the old payment link open
        could complete payment on a session Stripe considers perfectly
        valid, after MediLink has already moved the order to 'cancelled' -
        charging a real card with no corresponding order to fulfill. Stripe
        rejects expiring a session that is already complete/expired with a
        StripeError; that case is expected (nothing to invalidate) and is
        not an error for the caller.
        """
        try:
            stripe.checkout.Session.expire(session_id)
        except stripe.error.StripeError as e:
            logger.info("Stripe session %s could not be expired (likely already final): %s", session_id, str(e))
            raise StripeManagerError("Unable to expire Stripe checkout session") from e

    def refund_payment(self, payment_intent_id: str) -> "stripe.Refund":
        """
        Refund the full payment for *payment_intent_id*.

        Used only for orders admin-confirms as refundable (see
        OrderService.REFUNDABLE_STATUSES) - by the time this is called the
        order has already actually captured a payment, so there is always a
        real charge behind this payment intent to reverse.
        """
        try:
            return stripe.Refund.create(payment_intent=payment_intent_id)
        except stripe.error.StripeError as e:
            logger.error("Stripe error refunding payment intent %s: %s", payment_intent_id, str(e))
            raise StripeManagerError("Unable to refund Stripe payment") from e

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> "stripe.Event":
        """
        Verify and parse an incoming webhook payload.

        Raises StripeManagerError if the signature is missing/invalid or the
        payload is malformed - the caller must reject the request (HTTP 400)
        rather than process it. This is the only thing that turns a raw HTTP
        POST into something MediLink trusts as "really from Stripe".
        """
        try:
            return stripe.Webhook.construct_event(payload, sig_header, self.config.STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.warning("Invalid Stripe webhook payload or signature: %s", str(e))
            raise StripeManagerError("Invalid webhook payload or signature") from e
