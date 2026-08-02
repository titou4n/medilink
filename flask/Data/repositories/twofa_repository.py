"""
Data/repositories/twofa_repository.py
---------------------------------------
CRUD operations for the ``two_factor_codes`` table.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS: int = 3


class TwoFARepository:
    """Repository for two-factor authentication codes."""

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def insert(
        self,
        user_id: int,
        code_hash: str,
        created_at: str,
    ) -> None:
        """Persist a new 2FA code record."""
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO two_factor_codes (user_id, code_hash, created_at)
                VALUES (?, ?, ?);
                """,
                (user_id, code_hash, created_at),
            )
            conn.commit()
        logger.debug("2FA code inserted for user_id=%d", user_id)

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    def get_latest_valid(self, user_id: int) -> Optional[sqlite3.Row]:
        """
        Return the most recent, unused, non-exhausted 2FA code for
        *user_id*, or ``None`` if none exists.
        """
        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT
                    id_two_factor_codes,
                    code_hash,
                    created_at,
                    attempts,
                    used
                FROM two_factor_codes
                WHERE user_id  = ?
                  AND used     = 0
                  AND attempts < ?
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (user_id, _MAX_ATTEMPTS),
            ).fetchone()

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #

    def increment_attempts(self, id_two_factor_codes: int) -> None:
        """Bump the attempt counter for a specific code row."""
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE two_factor_codes
                SET attempts = attempts + 1
                WHERE id_two_factor_codes = ?;
                """,
                (id_two_factor_codes,),
            )
            conn.commit()

    def mark_as_used(self, id_two_factor_codes: int) -> None:
        """Flag a 2FA code as consumed so it cannot be reused."""
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE two_factor_codes
                SET used = 1
                WHERE id_two_factor_codes = ?;
                """,
                (id_two_factor_codes,),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete_by_user_id(self, user_id: int) -> None:
        """Remove all 2FA codes belonging to *user_id*."""
        with self._db.connect() as conn:
            conn.execute(
                "DELETE FROM two_factor_codes WHERE user_id = ?;",
                (user_id,),
            )
            conn.commit()

    def delete_expired(self) -> None:
        """
        Remove 2FA codes older than 30 minutes.

        Designed to be called by a periodic background task.
        """
        with self._db.connect() as conn:
            conn.execute(
                """
                DELETE FROM two_factor_codes
                WHERE created_at < datetime('now', '-30 minutes');
                """,
            )
            conn.commit()
        logger.debug("Expired 2FA codes cleaned up.")
