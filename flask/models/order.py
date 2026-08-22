"""
models/order.py
----------------
Models representing a NFC card order and its line items.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class OrderItem:
    """A single line item snapshot (price/name frozen at purchase time)."""

    id: Optional[int]
    order_id: int
    product_sku: str
    product_name: str
    unit_price_cents: int
    quantity: int = 1


@dataclass(slots=True)
class Order:
    """
    Represents a NFC card order.

    ``status`` covers both the payment and fulfillment lifecycle:
    pending -> paid -> processing -> shipped -> delivered
    (or -> cancelled / refunded at any point before delivered).
    """

    # ------------------------------------------------------------------ #
    # Primary fields
    # ------------------------------------------------------------------ #

    id: Optional[int]
    user_id: int
    status: str
    currency: str
    total_amount_cents: int

    # ------------------------------------------------------------------ #
    # Stripe references
    # ------------------------------------------------------------------ #

    stripe_checkout_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Shipping
    # ------------------------------------------------------------------ #

    shipping_name: Optional[str] = None
    shipping_line1: Optional[str] = None
    shipping_line2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Audit
    # ------------------------------------------------------------------ #

    created_at: str = ""
    updated_at: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Items (populated separately by the repository/service)
    # ------------------------------------------------------------------ #

    items: list[OrderItem] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<Order id={self.id} user_id={self.user_id} status={self.status}>"
