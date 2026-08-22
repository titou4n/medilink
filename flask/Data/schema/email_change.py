"""
Data/schema/email_change.py
----------------------------
DDL for the ``email_change_tokens`` table.
Only CREATE TABLE / CREATE INDEX statements live here.
"""

SCHEMA_EMAIL_CHANGE_TOKENS: str = """
CREATE TABLE IF NOT EXISTS email_change_tokens (
    id_email_change_tokens INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                INTEGER NOT NULL,
    new_email               TEXT    NOT NULL,
    token_hash               TEXT    NOT NULL UNIQUE,
    created_at                TEXT    NOT NULL,
    used                       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

INDEX_EMAIL_CHANGE_TOKENS_USER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_email_change_tokens_user_id
    ON email_change_tokens(user_id);
"""

INDEX_EMAIL_CHANGE_TOKENS_TOKEN_HASH: str = """
CREATE INDEX IF NOT EXISTS idx_email_change_tokens_token_hash
    ON email_change_tokens(token_hash);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_EMAIL_CHANGE_TOKENS,
    INDEX_EMAIL_CHANGE_TOKENS_USER_ID,
    INDEX_EMAIL_CHANGE_TOKENS_TOKEN_HASH,
]
