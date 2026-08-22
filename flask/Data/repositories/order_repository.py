"""
Data/repositories/order_repository.py
--------------------------------------
CRUD operations for the ``orders``, ``order_items`` and ``webhook_events``
tables.

``webhook_events`` lives here rather than in its own repository: it exists
solely as an idempotency guard for order-related Stripe webhooks, so it
follows the same lifecycle as orders. If webhooks for another domain are
introduced later, it should move to a repository of its own.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class OrderRepository:
    """Repository for the ``orders``, ``order_items`` and ``webhook_events`` tables."""

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Orders – creation
    # ------------------------------------------------------------------ #

    def create_order(self, user_id: int, currency: str, total_amount_cents: int) -> int:
        """Insert a new order in ``pending`` status and return its id."""
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO orders (user_id, currency, total_amount_cents)
                VALUES (?, ?, ?);
                """,
                (user_id, currency, total_amount_cents),
            )
            conn.commit()
            order_id = cursor.lastrowid
        logger.debug("Order created: id=%d user_id=%d", order_id, user_id)
        return order_id

    def add_item(
        self,
        order_id: int,
        product_sku: str,
        product_name: str,
        unit_price_cents: int,
        quantity: int,
    ) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO order_items (order_id, product_sku, product_name, unit_price_cents, quantity)
                VALUES (?, ?, ?, ?, ?);
                """,
                (order_id, product_sku, product_name, unit_price_cents, quantity),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Orders – reads
    # ------------------------------------------------------------------ #

    def get_by_id(self, order_id: int) -> Optional[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM orders WHERE id = ?;",
                (order_id,),
            ).fetchone()

    def get_by_stripe_checkout_session_id(self, session_id: str) -> Optional[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM orders WHERE stripe_checkout_session_id = ?;",
                (session_id,),
            ).fetchone()

    def get_all_for_user(self, user_id: int) -> list[sqlite3.Row]:
        """Return every order for *user_id*, newest first."""
        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM orders
                WHERE user_id = ?
                ORDER BY created_at DESC;
                """,
                (user_id,),
            ).fetchall()

    def get_items(self, order_id: int) -> list[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM order_items WHERE order_id = ?;",
                (order_id,),
            ).fetchall()

    def get_all_paginated(self, page: int = 1, per_page: int = 25) -> dict:
        """Return a paginated, newest-first list of every order (admin use)."""
        with self._db.connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM orders;").fetchone()[0]

            offset = (page - 1) * per_page
            items = conn.execute(
                """
                SELECT orders.*, account.email AS user_email, account.name AS user_name
                FROM orders
                JOIN account ON account.id = orders.user_id
                ORDER BY orders.created_at DESC
                LIMIT ? OFFSET ?;
                """,
                (per_page, offset),
            ).fetchall()

            pages = (total + per_page - 1) // per_page if total else 0
            has_prev = page > 1
            has_next = page < pages

            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages,
                "has_prev": has_prev,
                "has_next": has_next,
                "prev_num": page - 1 if has_prev else None,
                "next_num": page + 1 if has_next else None,
            }

    # ------------------------------------------------------------------ #
    # Orders – updates
    # ------------------------------------------------------------------ #

    def set_checkout_session_id(self, order_id: int, session_id: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE orders SET stripe_checkout_session_id = ?, updated_at = datetime('now') WHERE id = ?;",
                (session_id, order_id),
            )
            conn.commit()

    def set_payment_intent_id(self, order_id: int, payment_intent_id: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE orders SET stripe_payment_intent_id = ?, updated_at = datetime('now') WHERE id = ?;",
                (payment_intent_id, order_id),
            )
            conn.commit()

    def set_shipping_address(
        self,
        order_id: int,
        name: Optional[str],
        line1: Optional[str],
        line2: Optional[str],
        city: Optional[str],
        postal_code: Optional[str],
        country: Optional[str],
    ) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE orders
                SET shipping_name = ?, shipping_line1 = ?, shipping_line2 = ?,
                    shipping_city = ?, shipping_postal_code = ?, shipping_country = ?,
                    updated_at = datetime('now')
                WHERE id = ?;
                """,
                (name, line1, line2, city, postal_code, country, order_id),
            )
            conn.commit()

    def update_status(self, order_id: int, status: str, expected_statuses: Optional[list[str]] = None) -> bool:
        """
        Set *order_id*'s status to *status*.

        When *expected_statuses* is given, the write only applies if the
        order's current status is still one of them - checked and applied
        atomically by SQLite as a single ``UPDATE ... WHERE``, so a
        concurrent transition (e.g. a Stripe webhook marking an order paid
        at the same moment its owner cancels it) can never be silently lost
        to a stale in-memory status read. Returns whether the write applied.
        """
        with self._db.connect() as conn:
            if expected_statuses:
                placeholders = ",".join("?" for _ in expected_statuses)
                cursor = conn.execute(
                    f"""
                    UPDATE orders SET status = ?, updated_at = datetime('now')
                    WHERE id = ? AND status IN ({placeholders});
                    """,
                    (status, order_id, *expected_statuses),
                )
            else:
                cursor = conn.execute(
                    "UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?;",
                    (status, order_id),
                )
            conn.commit()
            applied = cursor.rowcount > 0
        if applied:
            logger.info("Order %d status set to '%s'", order_id, status)
        return applied

    # ------------------------------------------------------------------ #
    # Webhook idempotency
    # ------------------------------------------------------------------ #

    def record_event_if_new(self, stripe_event_id: str, event_type: str) -> bool:
        """
        Atomically record a Stripe event as processed.

        Returns ``True`` the first time a given *stripe_event_id* is seen,
        ``False`` on every subsequent call (duplicate webhook delivery) -
        relies on the UNIQUE constraint on ``webhook_events.stripe_event_id``
        rather than a separate exists-then-insert check, so it stays safe
        even if the same event is processed concurrently.
        """
        with self._db.connect() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO webhook_events (stripe_event_id, event_type) VALUES (?, ?);",
                (stripe_event_id, event_type),
            )
            conn.commit()
            return cursor.rowcount > 0

    def forget_event(self, stripe_event_id: str) -> None:
        """
        Remove a recorded webhook event.

        Used only when processing that event raised an unexpected error after
        it was already recorded as seen: without this, Stripe's retry of the
        same event would hit the idempotency guard and be silently skipped
        forever, permanently losing whatever that event was supposed to do.
        """
        with self._db.connect() as conn:
            conn.execute(
                "DELETE FROM webhook_events WHERE stripe_event_id = ?;",
                (stripe_event_id,),
            )
            conn.commit()
