"""
Data/repositories/password_reset_repository.py
-------------------------------------------------
CRUD operations for the ``password_reset_tokens`` table.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class PasswordResetRepository:
    """Repository for admin-triggered password reset tokens."""

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def insert(self, user_id: int, token_hash: str, created_at: str) -> None:
        """Persist a new password reset token record."""
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token_hash, created_at)
                VALUES (?, ?, ?);
                """,
                (user_id, token_hash, created_at),
            )
            conn.commit()
        logger.debug("Password reset token inserted for user_id=%d", user_id)

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    def get_by_token_hash(self, token_hash: str) -> Optional[sqlite3.Row]:
        """Return the token row matching *token_hash*, or ``None``."""
        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT id_password_reset_tokens, user_id, created_at, used
                FROM password_reset_tokens
                WHERE token_hash = ?;
                """,
                (token_hash,),
            ).fetchone()

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #

    def mark_as_used(self, id_password_reset_tokens: int) -> None:
        """Flag a reset token as consumed so it cannot be reused."""
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE password_reset_tokens
                SET used = 1
                WHERE id_password_reset_tokens = ?;
                """,
                (id_password_reset_tokens,),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete_by_user_id(self, user_id: int) -> None:
        """Remove all reset tokens belonging to *user_id*."""
        with self._db.connect() as conn:
            conn.execute(
                "DELETE FROM password_reset_tokens WHERE user_id = ?;",
                (user_id,),
            )
            conn.commit()

    def delete_expired(self, expiry_minutes: int) -> None:
        """
        Remove reset tokens older than *expiry_minutes*.

        Designed to be called opportunistically, like TwoFARepository.delete_expired.
        """
        with self._db.connect() as conn:
            conn.execute(
                f"""
                DELETE FROM password_reset_tokens
                WHERE created_at < datetime('now', '-{int(expiry_minutes)} minutes');
                """,
            )
            conn.commit()
        logger.debug("Expired password reset tokens cleaned up.")
