"""
Data/schema/cart.py
--------------------
DDL for ``carts`` and ``cart_items`` - one persistent cart per user.

A cart is created lazily on first use and never deleted; it is only emptied
(its items removed) once its contents become an order, or when the user
clears it explicitly. Item rows never store a price or product name -
CartService always re-reads both from ``products`` at read time, so a price
change or a product going inactive is reflected immediately in every
unconverted cart.
"""

SCHEMA_CARTS: str = """
CREATE TABLE IF NOT EXISTS carts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

SCHEMA_CART_ITEMS: str = """
CREATE TABLE IF NOT EXISTS cart_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id     INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT,
    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE (cart_id, product_id)
);
"""

INDEX_CART_ITEMS_CART_ID: str = """
CREATE INDEX IF NOT EXISTS idx_cart_items_cart_id ON cart_items(cart_id);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_CARTS,
    SCHEMA_CART_ITEMS,
    INDEX_CART_ITEMS_CART_ID,
]
