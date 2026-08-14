"""
Data/schema/oauth_identities.py
--------------------------------
DDL for the ``oauth_identities`` table: links an external OAuth/OIDC
provider identity (e.g. Google) to a local ``account`` row.

An account can have zero or more linked identities (currently at most one
per provider, enforced by the UNIQUE constraint below on (provider,
provider_sub) - not on account_id, so multiple providers could later map
to the same account).
"""

SCHEMA_OAUTH_IDENTITIES: str = """
CREATE TABLE IF NOT EXISTS oauth_identities (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id          INTEGER NOT NULL,
    provider            TEXT    NOT NULL,
    provider_sub        TEXT    NOT NULL,
    email_at_link_time  TEXT    NOT NULL,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (provider, provider_sub),
    FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

INDEX_OAUTH_IDENTITIES_ACCOUNT_ID: str = """
CREATE INDEX IF NOT EXISTS idx_oauth_identities_account_id ON oauth_identities(account_id);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_OAUTH_IDENTITIES,
    INDEX_OAUTH_IDENTITIES_ACCOUNT_ID,
]
