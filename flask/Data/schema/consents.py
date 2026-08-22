"""
Data/schema/consents.py
------------------------
DDL for the ``terms_consents`` table.
Only CREATE TABLE / CREATE INDEX statements live here.
"""

SCHEMA_TERMS_CONSENTS: str = """
CREATE TABLE IF NOT EXISTS terms_consents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    terms_version   TEXT    NOT NULL,
    accepted_at     TEXT    NOT NULL,
    ipv4            TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES account(id) ON DELETE CASCADE
);
"""

INDEX_TERMS_CONSENTS_USER_ID: str = """
CREATE INDEX IF NOT EXISTS idx_terms_consents_user_id ON terms_consents(user_id);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_TERMS_CONSENTS,
    INDEX_TERMS_CONSENTS_USER_ID,
]
