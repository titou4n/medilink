"""
Data/repositories/email_change_repository.py
-----------------------------------------------
CRUD operations for the ``email_change_tokens`` table.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class EmailChangeRepository:
    """Repository for pending email-change confirmation tokens."""

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def insert(self, user_id: int, new_email: str, token_hash: str, created_at: str) -> None:
        """Persist a new email-change token record."""
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO email_change_tokens (user_id, new_email, token_hash, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (user_id, new_email, token_hash, created_at),
            )
            conn.commit()
        logger.debug("Email change token inserted for user_id=%d", user_id)

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    def get_by_token_hash(self, token_hash: str) -> Optional[sqlite3.Row]:
        """Return the token row matching *token_hash*, or ``None``."""
        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT id_email_change_tokens, user_id, new_email, created_at, used
                FROM email_change_tokens
                WHERE token_hash = ?;
                """,
                (token_hash,),
            ).fetchone()

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #

    def mark_as_used(self, id_email_change_tokens: int) -> None:
        """Flag an email-change token as consumed so it cannot be reused."""
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE email_change_tokens
                SET used = 1
                WHERE id_email_change_tokens = ?;
                """,
                (id_email_change_tokens,),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete_by_user_id(self, user_id: int) -> None:
        """Remove all pending email-change tokens belonging to *user_id*."""
        with self._db.connect() as conn:
            conn.execute(
                "DELETE FROM email_change_tokens WHERE user_id = ?;",
                (user_id,),
            )
            conn.commit()

    def delete_expired(self, expiry_minutes: int) -> None:
        """
        Remove email-change tokens older than *expiry_minutes*.

        Designed to be called opportunistically, like
        PasswordResetRepository.delete_expired.
        """
        with self._db.connect() as conn:
            conn.execute(
                f"""
                DELETE FROM email_change_tokens
                WHERE created_at < datetime('now', '-{int(expiry_minutes)} minutes');
                """,
            )
            conn.commit()
        logger.debug("Expired email change tokens cleaned up.")
