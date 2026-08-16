"""
Data/database_manager.py
------------------------
Responsible for:
  - creating every table (via schema modules)
  - running seeders
  - bootstrapping the database once on first launch
"""

import logging
import extensions as ext
from Data.connection import DatabaseConnection
from Data.schema import accounts, auth, roles, emergency_information, oauth_identities, password_reset
from Data.seeders.roles_permissions import RolesPermissionsSeeder
import sqlite3

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Orchestrates the full database initialisation lifecycle.

    Parameters
    ----------
    db_connection:
        A configured :class:`~Data.connection.DatabaseConnection` instance.
    """

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection
        self._seeder = RolesPermissionsSeeder()
        self._config = ext.config

    def init_database(self) -> None:
        """
        Create all tables, indexes and seed default data.

        This method is idempotent: calling it on an already-initialised
        database is safe (all statements use IF NOT EXISTS / OR IGNORE).
        """
        logger.info("Initialising database …")
        with self._db.connect() as conn:
            self._handle_reset_flags(conn)
            self._create_schema(conn)
            self._run_seeders(conn)
            conn.commit()
        logger.info("Database initialisation complete.")

    def _create_schema(self, conn:sqlite3.Connection) -> None:
        """Execute every DDL statement from every schema module."""
        all_ddl_modules = [
            roles,
            accounts,
            auth,
            emergency_information,
            oauth_identities,
            password_reset,
        ]
        total = 0
        for module in all_ddl_modules:
            for statement in module.ALL_STATEMENTS:
                conn.execute(statement)
                total += 1
        logger.debug("Executed %d DDL statement(s).", total)

    def _run_seeders(self, conn:sqlite3.Connection) -> None:
        """Run all registered seeders inside the current connection."""
        self._seeder.run()


    def _handle_reset_flags(self, conn:sqlite3.Connection) -> None:
        """Reset flags"""
        if self._config.NEED_TO_RESET_ALL_DB:
            logger.warning("NEED_TO_RESET_ALL_DB=True — dropping all tables.")
            self._drop_all_tables(conn)

        elif self._config.NEED_TO_RESET_DB_EXCEPT_ACCOUNT:
            logger.warning("NEED_TO_RESET_DB_EXCEPT_ACCOUNT=True — dropping non-account tables.")
            self._drop_tables_except_accounts(conn)

        elif self._config.NEED_TO_RESET_ROLES_PERMISSIONS_TABLES:
            logger.warning("NEED_TO_RESET_ROLES_PERMISSIONS_TABLES=True — dropping roles/permissions tables.")
            self._drop_roles_permissions_tables(conn)

    def _drop_all_tables(self, conn:sqlite3.Connection) -> None:
        conn.execute("PRAGMA foreign_keys = OFF;")
        tables = self._get_all_tables(conn)
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table};")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        logger.debug("Dropped %d table(s).", len(tables))

    def _drop_tables_except_accounts(self, conn:sqlite3.Connection) -> None:
        conn.execute("PRAGMA foreign_keys = OFF;")
        PROTECTED = {"accounts", "account_preferences"}
        tables = [t for t in self._get_all_tables(conn) if t not in PROTECTED]
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table};")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        logger.debug("Dropped %d non-account table(s).", len(tables))

    def _drop_roles_permissions_tables(self, conn:sqlite3.Connection) -> None:
        conn.execute("PRAGMA foreign_keys = OFF;")
        for table in ("role_permissions", "permissions", "roles"):
            conn.execute(f"DROP TABLE IF EXISTS {table};")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        logger.debug("Dropped roles/permissions tables.")

    @staticmethod
    def _get_all_tables(conn:sqlite3.Connection) -> list[str]:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
        return [row["name"] for row in rows]