"""
Data/repositories/oauth_identity_repository.py
------------------------------------------------
CRUD operations for the ``oauth_identities`` table.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class OAuthIdentityRepository:
    """
    Repository for external OAuth/OIDC identities (e.g. Google) linked to
    local ``account`` rows.
    """

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    def get_account_id_by_provider_sub(self, provider: str, provider_sub: str) -> Optional[int]:
        """Return the linked ``account.id`` for this provider identity, or ``None``."""
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT account_id FROM oauth_identities WHERE provider = ? AND provider_sub = ?;",
                (provider, provider_sub),
            ).fetchone()
        return row["account_id"] if row else None

    def link(self, account_id: int, provider: str, provider_sub: str, email: str) -> None:
        """Link an external identity to *account_id*."""
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO oauth_identities (account_id, provider, provider_sub, email_at_link_time)
                VALUES (?, ?, ?, ?);
                """,
                (account_id, provider, provider_sub, email),
            )
            conn.commit()
        logger.info("Linked %s identity to account_id=%d", provider, account_id)

    def get_by_account_id(self, account_id: int) -> list[sqlite3.Row]:
        """Return every identity linked to *account_id*."""
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM oauth_identities WHERE account_id = ?;",
                (account_id,),
            ).fetchall()
