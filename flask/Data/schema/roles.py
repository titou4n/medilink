"""
Data/schema/roles.py
--------------------
DDL for ``roles``, ``permissions`` and ``role_permissions`` tables.
Only CREATE TABLE / CREATE INDEX statements live here.
"""

SCHEMA_ROLES: str = """
CREATE TABLE IF NOT EXISTS roles (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL UNIQUE
);
"""

SCHEMA_PERMISSIONS: str = """
CREATE TABLE IF NOT EXISTS permissions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL UNIQUE
);
"""

SCHEMA_ROLE_PERMISSIONS: str = """
CREATE TABLE IF NOT EXISTS role_permissions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id         INTEGER NOT NULL,
    permission_id   INTEGER NOT NULL,
    UNIQUE (role_id, permission_id),
    FOREIGN KEY (role_id)       REFERENCES roles(id)       ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);
"""

INDEX_ROLE_PERMISSIONS_ROLE_ID: str = """
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id
    ON role_permissions(role_id);
"""

INDEX_ROLE_PERMISSIONS_PERMISSION_ID: str = """
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id
    ON role_permissions(permission_id);
"""

ALL_STATEMENTS: list[str] = [
    SCHEMA_ROLES,
    SCHEMA_PERMISSIONS,
    SCHEMA_ROLE_PERMISSIONS,
    INDEX_ROLE_PERMISSIONS_ROLE_ID,
    INDEX_ROLE_PERMISSIONS_PERMISSION_ID,
]
