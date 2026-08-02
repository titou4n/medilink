"""
Data/schema/accounts.py
-----------------------
DDL for the ``account`` and ``user_preferences`` tables.
Only CREATE TABLE / CREATE INDEX statements live here.
"""

SCHEMA_ACCOUNTS: str = """
CREATE TABLE IF NOT EXISTS account (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id             INTEGER NOT NULL,
    username            TEXT    NOT NULL UNIQUE,
    password            TEXT    NOT NULL,
    name                TEXT    NOT NULL UNIQUE,
    email               TEXT,
    email_verified      INTEGER NOT NULL DEFAULT 0,
    pay                 REAL    NOT NULL DEFAULT 0.0,
    profile_picture_path TEXT,
    nbpasswordchange    INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);
"""

SCHEMA_USER_PREFERENCES: str = """
CREATE TABLE IF NOT EXISTS user_preferences (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE,
    twofa_enabled   INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

SCHEMA_METADATA: str = """
CREATE TABLE IF NOT EXISTS metadata (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    date_connected  TEXT    NOT NULL,
    ipv4            TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

INDEX_ACCOUNT_USERNAME: str = """
CREATE INDEX IF NOT EXISTS idx_account_username ON account(username);
"""

INDEX_ACCOUNT_NAME: str = """
CREATE INDEX IF NOT EXISTS idx_account_name ON account(name);
"""

INDEX_ACCOUNT_EMAIL: str = """
CREATE INDEX IF NOT EXISTS idx_account_email ON account(email);
"""

INDEX_METADATA_USER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_metadata_user_id ON metadata(user_id);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_ACCOUNTS,
    SCHEMA_USER_PREFERENCES,
    SCHEMA_METADATA,
    INDEX_ACCOUNT_USERNAME,
    INDEX_ACCOUNT_NAME,
    INDEX_ACCOUNT_EMAIL,
    INDEX_METADATA_USER_ID,
]
