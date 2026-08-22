"""
blueprints/orders/service.py
------------------------------
Business logic for NFC card orders: creation, syncing status from verified
Stripe webhook events, and triggering the corresponding transactional emails.
Talking to Stripe itself (API calls, webhook signature verification) lives in
utils/stripe_manager.py - this service only ever receives already-verified
data from it.
"""

import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional

from models.order import Order, OrderItem
from models.cart import Cart
from Data.repositories.order_repository import OrderRepository

import extensions as ext

logger = logging.getLogger(__name__)


@dataclass
class OrderActionResult:
    ok: bool
    message: str


class OrderService:
    """Service layer for NFC card orders."""

    # Linear, one-step-at-a-time fulfillment pipeline for a paid order -
    # deliberately no "skip a step" transition, so admin actions always
    # reflect an actual, sequential progress update.
    FULFILLMENT_TRANSITIONS: dict[str, str] = {
        "paid": "processing",
        "processing": "shipped",
        "shipped": "delivered",
    }

    # Any state that represents a captured payment can still be refunded,
    # including after delivery (e.g. a return) - "pending"/"cancelled" never
    # captured a payment, and "refunded" is already final.
    REFUNDABLE_STATUSES: tuple[str, ...] = ("paid", "processing", "shipped", "delivered")

    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    # ------------------------------------------------------------------ #
    # Conversion helpers
    # ------------------------------------------------------------------ #

    def _item_row_to_model(self, row: sqlite3.Row) -> OrderItem:
        return OrderItem(
            id=row["id"],
            order_id=row["order_id"],
            product_sku=row["product_sku"],
            product_name=row["product_name"],
            unit_price_cents=row["unit_price_cents"],
            quantity=row["quantity"],
        )

    def _row_to_model(self, row: sqlite3.Row, items: list[OrderItem]) -> Order:
        return Order(
            id=row["id"],
            user_id=row["user_id"],
            status=row["status"],
            currency=row["currency"],
            total_amount_cents=row["total_amount_cents"],
            stripe_checkout_session_id=row["stripe_checkout_session_id"],
            stripe_payment_intent_id=row["stripe_payment_intent_id"],
            shipping_name=row["shipping_name"],
            shipping_line1=row["shipping_line1"],
            shipping_line2=row["shipping_line2"],
            shipping_city=row["shipping_city"],
            shipping_postal_code=row["shipping_postal_code"],
            shipping_country=row["shipping_country"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            items=items,
        )

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def create_pending_order_from_cart(self, user_id: int, cart: Cart) -> Optional[Order]:
        """
        Create a pending order from *cart*'s contents.

        Every price/name/sku is taken from the cart's own items, which
        CartService itself always resolves fresh from the ``products`` table
        - never from anything the client could have sent directly. Lines
        whose product has since been deactivated are silently dropped rather
        than blocking checkout entirely; the caller decides what to tell the
        user about the difference between what was in the cart and what was
        actually ordered.

        Returns None if the cart has no purchasable item left, so nothing is
        created - the caller must not treat this as an error to raise, just
        an empty/unusable cart.
        """
        purchasable = [item for item in cart.items if item.product.is_active]
        if not purchasable:
            return None

        currency = purchasable[0].product.currency
        total_amount_cents = sum(item.subtotal_cents for item in purchasable)

        order_id = self._repository.create_order(
            user_id=user_id,
            currency=currency,
            total_amount_cents=total_amount_cents,
        )
        for item in purchasable:
            self._repository.add_item(
                order_id=order_id,
                product_sku=item.product.sku,
                product_name=item.product.name,
                unit_price_cents=item.product.price_cents,
                quantity=item.quantity,
            )

        logger.info("Order created from cart: id=%d user_id=%d", order_id, user_id)
        return self.get_by_id(order_id)

    # ------------------------------------------------------------------ #
    # Stripe
    # ------------------------------------------------------------------ #

    def attach_checkout_session(self, order_id: int, stripe_checkout_session_id: str) -> None:
        self._repository.set_checkout_session_id(order_id, stripe_checkout_session_id)

    def cancel_order(self, order_id: int) -> bool:
        """
        Mark a *pending* order as cancelled.

        The caller (routes.cancel()) must have already verified ownership -
        this method still re-checks the status itself, atomically, because a
        Stripe webhook could mark the order paid at the exact same moment its
        owner clicks cancel; without that guard the cancel could otherwise
        overwrite a just-paid order back to 'cancelled'. A logical
        ``cancelled`` status is used instead of deleting the row so the
        order stays visible in the user's history and in admin reporting.

        Returns whether the order was actually cancelled - False means it
        was no longer 'pending' by the time this ran (e.g. just paid).
        """
        applied = self._repository.update_status(order_id, "cancelled", expected_statuses=["pending"])
        if applied:
            logger.info("Order %d cancelled by its owner", order_id)
        return applied

    def record_webhook_event(self, stripe_event_id: str, event_type: str) -> bool:
        """Return True the first time *stripe_event_id* is seen, False on any replay."""
        return self._repository.record_event_if_new(stripe_event_id, event_type)

    def forget_webhook_event(self, stripe_event_id: str) -> None:
        """Un-record an event after its processing raised, so Stripe's retry is treated as new."""
        self._repository.forget_event(stripe_event_id)

    def mark_paid_from_checkout_session(self, session: dict) -> None:
        """
        Apply a verified Stripe ``checkout.session.completed`` event to the
        matching order.

        The order is normally looked up by the Stripe checkout session id we
        stored ourselves in attach_checkout_session() (Phase 4). If a
        customer re-clicks "Pay" (double click, second tab, browser back
        button) before finishing the first attempt, pay() overwrites that
        stored id with the newer session - so if they then complete payment
        on the *older* session (e.g. a tab left open), this lookup misses.
        Falling back to the order id embedded in the event's own metadata
        (part of the already signature-verified payload, so just as
        trustworthy) prevents a real successful charge from silently never
        reaching a "paid" order. Whichever session actually paid is then
        re-saved as the order's session id, so it stays accurate.

        Only moves a *pending* order to *paid*: an event replayed after the
        order already progressed (or after webhook_events already
        deduplicated it) is a no-op, not an error.
        """
        # Stripe SDK objects don't support dict-style .get() - normalize to a
        # plain (recursively converted) dict once, up front, so the rest of
        # this method can use ordinary dict access.
        if hasattr(session, "to_dict"):
            session = session.to_dict()

        order_row = self._repository.get_by_stripe_checkout_session_id(session["id"])
        if not order_row:
            order_id_from_metadata = (session.get("metadata") or {}).get("order_id") or session.get("client_reference_id")
            if order_id_from_metadata:
                order_row = self._repository.get_by_id(int(order_id_from_metadata))
            if not order_row:
                logger.warning("Webhook: no order found for Stripe session %s", session["id"])
                return
            logger.info(
                "Webhook: session %s wasn't order %d's current session (superseded by a later "
                "Pay attempt) - recovered via event metadata",
                session["id"], order_row["id"],
            )

        order_id = order_row["id"]

        if order_row["status"] != "pending":
            logger.info(
                "Webhook: order %d already in status '%s', ignoring completed session %s",
                order_id, order_row["status"], session["id"],
            )
            return

        # Whichever session actually got paid is the one worth keeping on record.
        self._repository.set_checkout_session_id(order_id, session["id"])

        payment_intent_id = session.get("payment_intent")
        if payment_intent_id:
            self._repository.set_payment_intent_id(order_id, payment_intent_id)

        # Newer Checkout sessions nest shipping under collected_information;
        # fall back to the older top-level field for compatibility.
        shipping = (
            (session.get("collected_information") or {}).get("shipping_details")
            or session.get("shipping_details")
            or {}
        )
        address = shipping.get("address") or {}
        self._repository.set_shipping_address(
            order_id,
            name=shipping.get("name"),
            line1=address.get("line1"),
            line2=address.get("line2"),
            city=address.get("city"),
            postal_code=address.get("postal_code"),
            country=address.get("country"),
        )

        # Atomic, conditional on still being 'pending': protects against the
        # owner's cancel() request racing this same webhook and winning the
        # write after the check above already read 'pending'.
        applied = self._repository.update_status(order_id, "paid", expected_statuses=["pending"])
        if not applied:
            logger.warning(
                "Webhook: order %d left 'pending' concurrently (e.g. cancelled) while this webhook was "
                "processing a completed payment for session %s - payment was captured but the order was "
                "NOT marked paid; needs manual review",
                order_id, session["id"],
            )
            return

        logger.info("Order %d marked as paid via Stripe webhook (session %s)", order_id, session["id"])

        ext.email_manager.send_order_confirmation_email(
            user_id=order_row["user_id"],
            order_id=order_id,
            total_amount_cents=order_row["total_amount_cents"],
            currency=order_row["currency"],
        )

    def notify_payment_failed_from_expired_session(self, session: dict) -> None:
        """
        Apply a verified Stripe ``checkout.session.expired`` event: the
        customer never completed payment before the session's deadline.

        Never touches order.status - the order stays *pending* exactly as it
        already was, so the customer can simply click "Pay" again for a fresh
        Checkout Session. This only sends a heads-up email.
        """
        if hasattr(session, "to_dict"):
            session = session.to_dict()

        order_row = self._repository.get_by_stripe_checkout_session_id(session["id"])
        if not order_row:
            logger.warning("Webhook: no order found for expired Stripe session %s", session["id"])
            return

        if order_row["status"] != "pending":
            return

        ext.email_manager.send_order_payment_failed_email(
            user_id=order_row["user_id"],
            order_id=order_row["id"],
        )

    # ------------------------------------------------------------------ #
    # Admin: fulfillment & refunds
    # ------------------------------------------------------------------ #

    def next_fulfillment_status(self, status: str) -> Optional[str]:
        """The next status in the fulfillment pipeline after *status*, or None if there isn't one."""
        return self.FULFILLMENT_TRANSITIONS.get(status)

    def is_refundable(self, status: str) -> bool:
        return status in self.REFUNDABLE_STATUSES

    def advance_fulfillment(self, order_id: int) -> OrderActionResult:
        """
        Move a paid order one step forward in the fulfillment pipeline
        (paid -> processing -> shipped -> delivered), one step at a time.

        Never touches Stripe - this is a purely logistical status update for
        an order whose payment is already settled.
        """
        order = self.get_by_id(order_id)
        if not order:
            return OrderActionResult(False, "Order not found.")

        next_status = self.next_fulfillment_status(order.status)
        if not next_status:
            return OrderActionResult(False, f"Order cannot be advanced from status '{order.status}'.")

        applied = self._repository.update_status(order_id, next_status, expected_statuses=[order.status])
        if not applied:
            return OrderActionResult(False, "Order status changed - please refresh and try again.")

        logger.info("Order %d advanced to '%s' by admin", order_id, next_status)
        return OrderActionResult(True, f"Order marked as {next_status}.")

    def mark_refunded(self, order_id: int) -> OrderActionResult:
        """
        Record that *order_id* was refunded.

        The caller (routes.admin_refund()) must already have successfully
        called Stripe to actually refund the payment before calling this -
        this method only records the resulting state, atomically, against
        whatever REFUNDABLE_STATUSES the order was still in.
        """
        applied = self._repository.update_status(
            order_id, "refunded", expected_statuses=list(self.REFUNDABLE_STATUSES)
        )
        if not applied:
            return OrderActionResult(False, "Order status changed - please refresh and try again.")

        logger.info("Order %d marked as refunded by admin", order_id)
        return OrderActionResult(True, "Order refunded.")

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    def get_by_id(self, order_id: int) -> Optional[Order]:
        row = self._repository.get_by_id(order_id)
        if not row:
            return None
        items = [self._item_row_to_model(r) for r in self._repository.get_items(order_id)]
        return self._row_to_model(row, items)

    def get_all_for_user(self, user_id: int) -> list[Order]:
        orders = []
        for row in self._repository.get_all_for_user(user_id):
            items = [self._item_row_to_model(r) for r in self._repository.get_items(row["id"])]
            orders.append(self._row_to_model(row, items))
        return orders

    def get_all_paginated(self, page: int = 1, per_page: int = 25) -> dict:
        """
        Return every order, paginated, for the admin dashboard.

        Items aren't fetched here (admin sees them by opening an order) - the
        single-product MVP means a per-row product/quantity summary isn't
        worth an extra query per order yet.
        """
        result = self._repository.get_all_paginated(page, per_page)
        result["items"] = [
            {
                "order": self._row_to_model(row, items=[]),
                "user_email": row["user_email"],
                "user_name": row["user_name"],
            }
            for row in result["items"]
        ]
        return result
