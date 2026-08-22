"""
Data/repositories/cart_repository.py
---------------------------------------
CRUD for ``carts`` and ``cart_items``.

Every user has at most one cart, created lazily on first use
(``get_or_create_cart``). Item rows never store price/name - CartService
always joins against ``products`` so a price change or a product going
inactive is reflected the moment the cart is read.

Ownership is enforced entirely through ``cart_id``: every read/update/delete
below is scoped to a specific ``cart_id`` that callers must have already
resolved from ``get_or_create_cart(user_id)`` - never from a client-supplied
id - so one user can never reach another user's cart items.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class CartRepository:
    """Repository for the ``carts`` and ``cart_items`` tables."""

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Cart
    # ------------------------------------------------------------------ #

    def get_or_create_cart(self, user_id: int) -> sqlite3.Row:
        with self._db.connect() as conn:
            row = conn.execute("SELECT * FROM carts WHERE user_id = ?;", (user_id,)).fetchone()
            if row:
                return row
            cursor = conn.execute("INSERT INTO carts (user_id) VALUES (?);", (user_id,))
            conn.commit()
            return conn.execute("SELECT * FROM carts WHERE id = ?;", (cursor.lastrowid,)).fetchone()

    # ------------------------------------------------------------------ #
    # Items
    # ------------------------------------------------------------------ #

    def get_items(self, cart_id: int) -> list[sqlite3.Row]:
        """Item rows joined with their product, oldest first."""
        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT cart_items.id AS id, cart_items.cart_id AS cart_id,
                       cart_items.quantity AS quantity,
                       products.id AS product_id, products.sku AS product_sku,
                       products.name AS product_name, products.description AS product_description,
                       products.price_cents AS product_price_cents, products.currency AS product_currency,
                       products.is_active AS product_is_active
                FROM cart_items
                JOIN products ON products.id = cart_items.product_id
                WHERE cart_items.cart_id = ?
                ORDER BY cart_items.created_at ASC;
                """,
                (cart_id,),
            ).fetchall()

    def get_item(self, cart_id: int, item_id: int) -> Optional[sqlite3.Row]:
        """Fetch item *item_id*, scoped to *cart_id* - returns None if it belongs to a different cart."""
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM cart_items WHERE id = ? AND cart_id = ?;", (item_id, cart_id)
            ).fetchone()

    def get_item_by_product(self, cart_id: int, product_id: int) -> Optional[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM cart_items WHERE cart_id = ? AND product_id = ?;", (cart_id, product_id)
            ).fetchone()

    def add_item(self, cart_id: int, product_id: int, quantity: int) -> None:
        """
        Insert a new line, or bump the quantity if this product is already in
        the cart. Relies on the UNIQUE(cart_id, product_id) constraint via
        upsert so re-submitting "add to cart" for the same product never
        creates a second row for it.
        """
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO cart_items (cart_id, product_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(cart_id, product_id)
                DO UPDATE SET quantity = quantity + excluded.quantity, updated_at = datetime('now');
                """,
                (cart_id, product_id, quantity),
            )
            conn.execute("UPDATE carts SET updated_at = datetime('now') WHERE id = ?;", (cart_id,))
            conn.commit()

    def update_quantity(self, cart_id: int, item_id: int, quantity: int) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE cart_items SET quantity = ?, updated_at = datetime('now') WHERE id = ? AND cart_id = ?;",
                (quantity, item_id, cart_id),
            )
            conn.execute("UPDATE carts SET updated_at = datetime('now') WHERE id = ?;", (cart_id,))
            conn.commit()

    def remove_item(self, cart_id: int, item_id: int) -> None:
        with self._db.connect() as conn:
            conn.execute("DELETE FROM cart_items WHERE id = ? AND cart_id = ?;", (item_id, cart_id))
            conn.execute("UPDATE carts SET updated_at = datetime('now') WHERE id = ?;", (cart_id,))
            conn.commit()

    def clear(self, cart_id: int) -> None:
        with self._db.connect() as conn:
            conn.execute("DELETE FROM cart_items WHERE cart_id = ?;", (cart_id,))
            conn.execute("UPDATE carts SET updated_at = datetime('now') WHERE id = ?;", (cart_id,))
            conn.commit()

    def count_items(self, user_id: int) -> int:
        """Total quantity across every line in *user_id*'s cart (0 if none/empty). Used by the nav badge."""
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(cart_items.quantity), 0) AS total
                FROM cart_items
                JOIN carts ON carts.id = cart_items.cart_id
                WHERE carts.user_id = ?;
                """,
                (user_id,),
            ).fetchone()
            return row["total"] if row else 0
