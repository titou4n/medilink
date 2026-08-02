"""
Data/seeders/roles_permissions.py
"""
from __future__ import annotations

import logging
import extensions as ext

logger = logging.getLogger(__name__)


class RolesPermissionsSeeder:
    def __init__(self) -> None:
        self._db     = ext.db_connection
        self._permissions = ext.permissions

    def run(self) -> None:
        self._seed_roles()
        self._seed_permissions()
        self._seed_role_permissions()

    def _seed_roles(self) -> None:
        with self._db.connect() as conn:
            for role_name in self._permissions.LIST_DEFAULT_ROLES:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO roles (name)
                    VALUES (?);
                    """,
                    (role_name,)
                )
            conn.commit()

    def _seed_permissions(self) -> None:
        with self._db.connect() as conn:
            for permission_name in self._permissions.LIST_ALL_PERMISSIONS:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO permissions (name)
                    VALUES (?);
                    """,
                    (permission_name,)
                )
            conn.commit()

    def _seed_role_permissions(self) -> None:
        with self._db.connect() as conn:

            roles = {}
            rows_roles = conn.execute("""SELECT id, name FROM roles;""").fetchall()
            for row in rows_roles:
                roles[row["name"]] = row["id"]


            permissions = {}
            rows_permissions = conn.execute("""SELECT id, name FROM permissions;""").fetchall()
            for row in rows_permissions: 
                permissions[row["name"]] = row["id"]

            for role_name, permission_names in self._permissions.DICT_ROLE_PERMISSION.items():

                role_id = roles.get(role_name)

                if role_id is None:
                    logger.warning("Role '%s' not found -> skipping.",role_name)
                    continue

                for permission_name in permission_names:

                    permission_id = permissions.get(permission_name)

                    if permission_id is None:
                        logger.warning("Permission '%s' not found – skipping.",permission_name)
                        continue

                    conn.execute(
                        """
                        INSERT OR IGNORE INTO role_permissions (
                            role_id,
                            permission_id
                        )
                        VALUES (?, ?);
                        """,
                        (
                            role_id,
                            permission_id
                        )
                    )

            conn.commit()