"""
Data/seeders/products_seeder.py
---------------------------------
Seeds the original MediLink NFC card as the first row of the ``products``
catalog, once, on a fresh database (INSERT OR IGNORE keyed on sku). After
that the product lives entirely in the database and is managed from the
admin panel - this seeder never overwrites an existing row.
"""
from __future__ import annotations

import logging
import extensions as ext

logger = logging.getLogger(__name__)


class ProductsSeeder:
    def __init__(self) -> None:
        self._db = ext.db_connection
        self._config = ext.config

    def run(self) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO products (sku, name, description, price_cents, currency)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    self._config.NFC_CARD_SKU,
                    self._config.NFC_CARD_NAME,
                    self._config.NFC_CARD_DESCRIPTION,
                    self._config.NFC_CARD_PRICE_CENTS,
                    self._config.SHOP_CURRENCY,
                ),
            )
            conn.commit()
