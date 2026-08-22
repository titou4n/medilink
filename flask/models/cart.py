"""
models/cart.py
----------------
Represents a user's persistent shopping cart.

Each item carries its own resolved Product (see CartService), so price,
name and availability always reflect the current catalog rather than
whatever was true when the item was added.
"""

from dataclasses import dataclass, field
from typing import Optional

from models.product import Product


@dataclass(slots=True)
class CartItem:
    id: Optional[int]
    cart_id: int
    product: Product
    quantity: int

    @property
    def subtotal_cents(self) -> int:
        return self.product.price_cents * self.quantity


@dataclass(slots=True)
class Cart:
    id: Optional[int]
    user_id: int
    created_at: str = ""
    updated_at: Optional[str] = None
    items: list[CartItem] = field(default_factory=list)

    @property
    def total_cents(self) -> int:
        """
        Sum of purchasable lines only - a deactivated product's line is
        never charged (see OrderService.create_pending_order_from_cart,
        which silently drops it at checkout), so it must not inflate the
        total shown here either.
        """
        return sum(item.subtotal_cents for item in self.items if item.product.is_active)

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def is_empty(self) -> bool:
        return not self.items
