"""
Data/schema/products.py
------------------------
DDL for the ``products`` table - the shop catalog.

Prices are stored once, in cents, and are the single source of truth read by
CartService/OrderService when computing totals - never trust a price coming
from the client. Products are never hard-deleted (see ProductRepository):
``is_active`` hides a product from the catalog and blocks new cart/order
operations on it while keeping past order_items snapshots intact.
"""

SCHEMA_PRODUCTS: str = """
CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sku          TEXT    NOT NULL UNIQUE,
    name         TEXT    NOT NULL,
    description  TEXT,
    price_cents  INTEGER NOT NULL,
    currency     TEXT    NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 1,
    image_path   TEXT,
    icon_key     TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT
);
"""

INDEX_PRODUCTS_IS_ACTIVE: str = """
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_PRODUCTS,
    INDEX_PRODUCTS_IS_ACTIVE,
]
