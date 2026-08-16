"""
Data/schema/password_reset.py
------------------------------
DDL for the ``password_reset_tokens`` table.
Only CREATE TABLE / CREATE INDEX statements live here.
"""

SCHEMA_PASSWORD_RESET_TOKENS: str = """
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id_password_reset_tokens INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                  INTEGER NOT NULL,
    token_hash                TEXT    NOT NULL UNIQUE,
    created_at                TEXT    NOT NULL,
    used                       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

INDEX_PASSWORD_RESET_TOKENS_USER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id
    ON password_reset_tokens(user_id);
"""

INDEX_PASSWORD_RESET_TOKENS_TOKEN_HASH: str = """
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token_hash
    ON password_reset_tokens(token_hash);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_PASSWORD_RESET_TOKENS,
    INDEX_PASSWORD_RESET_TOKENS_USER_ID,
    INDEX_PASSWORD_RESET_TOKENS_TOKEN_HASH,
]
