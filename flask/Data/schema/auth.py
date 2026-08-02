"""
Data/schema/auth.py
-------------------
DDL for ``sessions`` and ``two_factor_codes`` tables.
Only CREATE TABLE / CREATE INDEX statements live here.
"""

SCHEMA_SESSIONS: str = """
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id_hash TEXT    NOT NULL UNIQUE,
    user_id         INTEGER NOT NULL,
    created_at      TEXT    NOT NULL,
    expires_at      TEXT    NOT NULL,
    last_used_at    TEXT    NOT NULL,
    ip_hash         TEXT    NOT NULL,
    user_agent_hash TEXT    NOT NULL,
    is_revoked      INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

SCHEMA_TWO_FACTOR_CODES: str = """
CREATE TABLE IF NOT EXISTS two_factor_codes (
    id_two_factor_codes INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    code_hash           TEXT    NOT NULL,
    created_at          TEXT    NOT NULL,
    attempts            INTEGER NOT NULL DEFAULT 0,
    used                INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

INDEX_SESSIONS_USER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
"""

INDEX_SESSIONS_SESSION_ID_HASH: str = """
CREATE INDEX IF NOT EXISTS idx_sessions_session_id_hash
    ON sessions(session_id_hash);
"""

INDEX_TWO_FACTOR_USER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_two_factor_codes_user_id
    ON two_factor_codes(user_id);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_SESSIONS,
    SCHEMA_TWO_FACTOR_CODES,
    INDEX_SESSIONS_USER_ID,
    INDEX_SESSIONS_SESSION_ID_HASH,
    INDEX_TWO_FACTOR_USER_ID,
]
