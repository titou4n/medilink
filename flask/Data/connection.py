"""
Data/connection.py
------------------
Low-level SQLite connection factory.

All repositories obtain their connections through this module so that
connection options (row_factory, foreign keys, WAL mode …) are applied
in exactly one place.
"""

import logging
import sqlite3
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Thin wrapper around :func:`sqlite3.connect`.

    A single instance is shared application-wide (created in
    ``extensions.py``) so the *db_path* is configured once.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        logger.debug("DatabaseConnection initialised with path: %s", db_path)

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #

    def get_connection(self) -> sqlite3.Connection:
        """
        Return a new, fully configured :class:`sqlite3.Connection`.

        Callers are responsible for closing the connection.  Prefer
        :meth:`connect` (the context-manager version) whenever possible.
        """
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        self._apply_pragmas(conn)
        return conn

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager that opens a connection, yields it and closes it
        automatically – even on exceptions.

        Usage::

            with db_connection.connect() as conn:
                conn.execute("SELECT 1")
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _apply_pragmas(conn: sqlite3.Connection) -> None:
        """Apply SQLite PRAGMAs that must be set on every new connection."""
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
