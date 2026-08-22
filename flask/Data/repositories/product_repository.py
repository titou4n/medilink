"""
Data/repositories/product_repository.py
------------------------------------------
CRUD operations for the ``products`` table.

Products are never hard-deleted: an order's ``order_items`` snapshot only
stores a copy of the sku/name/price, but deleting the source row would still
be a needless landmine for any future feature that looks products up by id.
Deactivating (``is_active = 0``) removes a product from the shop and blocks
new cart/order operations on it while keeping everything else intact.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ProductRepository:
    """Repository for the ``products`` table."""

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def create(
        self,
        sku: str,
        name: str,
        description: Optional[str],
        price_cents: int,
        currency: str,
        icon_key: Optional[str] = None,
    ) -> int:
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO products (sku, name, description, price_cents, currency, icon_key)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (sku, name, description, price_cents, currency, icon_key),
            )
            conn.commit()
            product_id = cursor.lastrowid
        logger.info("Product created: id=%d sku=%s", product_id, sku)
        return product_id

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def get_by_id(self, product_id: int) -> Optional[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute("SELECT * FROM products WHERE id = ?;", (product_id,)).fetchone()

    def get_by_sku(self, sku: str) -> Optional[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute("SELECT * FROM products WHERE sku = ?;", (sku,)).fetchone()

    def get_all_active(self) -> list[sqlite3.Row]:
        """Every purchasable product, for the public catalog."""
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM products WHERE is_active = 1 ORDER BY name ASC;"
            ).fetchall()

    def get_all_paginated(self, page: int = 1, per_page: int = 25) -> dict:
        """Return a paginated, newest-first list of every product (admin use)."""
        with self._db.connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM products;").fetchone()[0]

            offset = (page - 1) * per_page
            items = conn.execute(
                "SELECT * FROM products ORDER BY created_at DESC LIMIT ? OFFSET ?;",
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

    def sku_exists(self, sku: str, exclude_id: Optional[int] = None) -> bool:
        with self._db.connect() as conn:
            if exclude_id is not None:
                row = conn.execute(
                    "SELECT 1 FROM products WHERE sku = ? AND id != ?;", (sku, exclude_id)
                ).fetchone()
            else:
                row = conn.execute("SELECT 1 FROM products WHERE sku = ?;", (sku,)).fetchone()
            return row is not None

    # ------------------------------------------------------------------ #
    # Updates
    # ------------------------------------------------------------------ #

    def update(
        self,
        product_id: int,
        name: str,
        description: Optional[str],
        price_cents: int,
        icon_key: Optional[str] = None,
    ) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE products
                SET name = ?, description = ?, price_cents = ?, icon_key = ?, updated_at = datetime('now')
                WHERE id = ?;
                """,
                (name, description, price_cents, icon_key, product_id),
            )
            conn.commit()
        logger.info("Product %d updated", product_id)

    def update_image_path(self, product_id: int, image_path: Optional[str]) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE products SET image_path = ?, updated_at = datetime('now') WHERE id = ?;",
                (image_path, product_id),
            )
            conn.commit()
        logger.info("Product %d image_path updated", product_id)

    def set_active(self, product_id: int, is_active: bool) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE products SET is_active = ?, updated_at = datetime('now') WHERE id = ?;",
                (1 if is_active else 0, product_id),
            )
            conn.commit()
        logger.info("Product %d active status set to %s", product_id, is_active)
