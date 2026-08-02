"""
Data/repositories/session_repository.py
-----------------------------------------
CRUD operations for the ``sessions`` table.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for user session management."""

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    def insert(
        self,
        session_id_hash: str,
        user_id: int,
        created_at: str,
        expires_at: str,
        ip_hash: str,
        user_agent_hash: str,
        is_revoked: bool = False,
    ) -> None:
        """Persist a new session record."""
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id_hash,
                    user_id,
                    created_at,
                    expires_at,
                    last_used_at,
                    ip_hash,
                    user_agent_hash,
                    is_revoked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    session_id_hash,
                    user_id,
                    created_at,
                    expires_at,
                    created_at,   # last_used_at = created_at on insert
                    ip_hash,
                    user_agent_hash,
                    int(is_revoked),
                ),
            )
            conn.commit()
        logger.debug("Session inserted for user_id=%d", user_id)

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    def get_by_hash(self, session_id_hash: str) -> Optional[sqlite3.Row]:
        """Return the session row matching *session_id_hash*, or ``None``."""
        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT
                    session_id_hash, user_id, created_at, expires_at,
                    last_used_at, ip_hash, user_agent_hash, is_revoked
                FROM sessions
                WHERE session_id_hash = ?;
                """,
                (session_id_hash,),
            ).fetchone()

    def get_all_by_user_id(self, user_id: int) -> list[sqlite3.Row]:
        """Return all session rows for *user_id*."""
        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT
                    session_id_hash, user_id, created_at, expires_at,
                    last_used_at, ip_hash, user_agent_hash, is_revoked
                FROM sessions
                WHERE user_id = ?;
                """,
                (user_id,),
            ).fetchall()

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #

    def touch(self, session_id_hash: str, last_used_at: str) -> None:
        """Update the ``last_used_at`` timestamp for a session."""
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE sessions SET last_used_at = ? WHERE session_id_hash = ?;",
                (last_used_at, session_id_hash),
            )
            conn.commit()

    def revoke(self, session_id_hash: str) -> None:
        """Mark a single session as revoked."""
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE sessions SET is_revoked = 1 WHERE session_id_hash = ?;",
                (session_id_hash,),
            )
            conn.commit()
        logger.info("Session revoked: hash=%s", session_id_hash)

    def revoke_owned(self, session_id_hash: str, user_id: int) -> bool:
        """
        Mark a single session as revoked, but only if it belongs to *user_id*.

        Returns True if a row was actually revoked, False if no session
        matched (either it doesn't exist or it belongs to someone else) -
        callers must not distinguish between these two cases in the
        response, to avoid leaking whether a given hash exists.
        """
        with self._db.connect() as conn:
            cur = conn.execute(
                "UPDATE sessions SET is_revoked = 1 WHERE session_id_hash = ? AND user_id = ?;",
                (session_id_hash, user_id),
            )
            conn.commit()
        revoked = cur.rowcount > 0
        if revoked:
            logger.info("Session revoked: hash=%s, user_id=%d", session_id_hash, user_id)
        return revoked

    def revoke_all_for_user(self, user_id: int) -> None:
        """Revoke every active session belonging to *user_id*."""
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE sessions SET is_revoked = 1 WHERE user_id = ?;",
                (user_id,),
            )
            conn.commit()
        logger.info("All sessions revoked for user_id=%d", user_id)

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete(self, session_id_hash: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE session_id_hash = ?;",
                (session_id_hash,),
            )
            conn.commit()

    def delete_owned(self, session_id_hash: str, user_id: int) -> bool:
        """
        Delete a single session, but only if it belongs to *user_id*.
        Returns True if a row was actually deleted.
        """
        with self._db.connect() as conn:
            cur = conn.execute(
                "DELETE FROM sessions WHERE session_id_hash = ? AND user_id = ?;",
                (session_id_hash, user_id),
            )
            conn.commit()
        deleted = cur.rowcount > 0
        if deleted:
            logger.info("Session deleted: hash=%s, user_id=%d", session_id_hash, user_id)
        return deleted

    def delete_all(self) -> None:
        """Purge the entire sessions table (use with caution)."""
        with self._db.connect() as conn:
            conn.execute("DELETE FROM sessions;")
            conn.commit()
        logger.warning("All sessions deleted.")
