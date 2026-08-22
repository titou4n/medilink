"""
Data/schema/orders.py
----------------------
DDL for the ``orders``, ``order_items`` and ``webhook_events`` tables.
Only CREATE TABLE / CREATE INDEX statements live here.

Status lifecycle (see blueprints/orders/service.py):
  orders.status: pending -> paid -> processing -> shipped -> delivered
                 (or -> cancelled / refunded at any point before delivered)

``webhook_events`` is a pure idempotency guard: every processed Stripe
event id is recorded there so a webhook delivered twice (Stripe retries
on anything but a 2xx) is only ever applied once.
"""

SCHEMA_ORDERS: str = """
CREATE TABLE IF NOT EXISTS orders (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                     INTEGER NOT NULL,
    status                      TEXT    NOT NULL DEFAULT 'pending',
    currency                    TEXT    NOT NULL,
    total_amount_cents          INTEGER NOT NULL,
    stripe_checkout_session_id  TEXT    UNIQUE,
    stripe_payment_intent_id    TEXT,
    shipping_name               TEXT,
    shipping_line1              TEXT,
    shipping_line2              TEXT,
    shipping_city               TEXT,
    shipping_postal_code        TEXT,
    shipping_country            TEXT,
    created_at                  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at                  TEXT,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

SCHEMA_ORDER_ITEMS: str = """
CREATE TABLE IF NOT EXISTS order_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id         INTEGER NOT NULL,
    product_sku      TEXT    NOT NULL,
    product_name     TEXT    NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    quantity         INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);
"""

SCHEMA_WEBHOOK_EVENTS: str = """
CREATE TABLE IF NOT EXISTS webhook_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_event_id  TEXT    NOT NULL UNIQUE,
    event_type       TEXT    NOT NULL,
    received_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

INDEX_ORDERS_USER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
"""

INDEX_ORDER_ITEMS_ORDER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_ORDERS,
    SCHEMA_ORDER_ITEMS,
    SCHEMA_WEBHOOK_EVENTS,
    INDEX_ORDERS_USER_ID,
    INDEX_ORDER_ITEMS_ORDER_ID,
]
