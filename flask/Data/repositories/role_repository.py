"""
Data/repositories/role_repository.py
--------------------------------------
CRUD operations for the ``roles``, ``permissions`` and
``role_permissions`` tables.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class RoleRepository:
    """
    Repository for roles, permissions and their many-to-many mapping.
    """

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Roles
    # ------------------------------------------------------------------ #

    def get_all_roles(self) -> list[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute("SELECT * FROM roles;").fetchall()

    def get_role_id(self, role_name: str) -> Optional[int]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT id FROM roles WHERE name = ?;",
                (role_name,),
            ).fetchone()
        return row["id"] if row else None

    def get_role_name(self, role_id: int) -> Optional[str]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT name FROM roles WHERE id = ?;",
                (role_id,),
            ).fetchone()
        return row["name"] if row else None

    def role_exists(self, role_name: str) -> bool:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM roles WHERE name = ?;",
                (role_name,),
            ).fetchone()
        return row is not None

    def insert_role(self, role_name: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO roles (name) VALUES (?);",
                (role_name,),
            )
            conn.commit()

    def update_role(self, role_id: int, role_name: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE roles SET name = ? WHERE id = ?;",
                (role_name, role_id),
            )
            conn.commit()

    def delete_role(self, role_id: int) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "DELETE FROM roles WHERE id = ?;",
                (role_id,),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Permissions
    # ------------------------------------------------------------------ #

    def get_permission_id(self, permission_name: str) -> Optional[int]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT id FROM permissions WHERE name = ?;",
                (permission_name,),
            ).fetchone()
        return row["id"] if row else None

    def get_permission_name(self, permission_id: int) -> Optional[str]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT name FROM permissions WHERE id = ?;",
                (permission_id,),
            ).fetchone()
        return row["name"] if row else None

    # ------------------------------------------------------------------ #
    # Role ↔ Permission mappings
    # ------------------------------------------------------------------ #

    def get_all_role_permission_pairs(self) -> list[sqlite3.Row]:
        """Return every (role_id, permission_id) pair."""
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT role_id, permission_id FROM role_permissions;",
            ).fetchall()

    def get_permission_ids_for_role(self, role_id: int) -> list[int]:
        """Return the list of permission IDs assigned to *role_id*."""
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT permission_id FROM role_permissions WHERE role_id = ?;",
                (role_id,),
            ).fetchall()
        return [row["permission_id"] for row in rows]

    def insert_role_permission(self, role_id: int, permission_id: int) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?);
                """,
                (role_id, permission_id),
            )
            conn.commit()

    def delete_permissions_for_role(self, role_id: int) -> None:
        """Remove all permission assignments for *role_id*."""
        with self._db.connect() as conn:
            conn.execute(
                "DELETE FROM role_permissions WHERE role_id = ?;",
                (role_id,),
            )
            conn.commit()
