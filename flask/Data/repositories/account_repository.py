"""
Data/repositories/account_repository.py
----------------------------------------
CRUD operations for the ``account`` and ``user_preferences`` tables.

Single responsibility: everything that touches an account row lives here.
"""

import logging
import sqlite3
from typing import Optional

from Data.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class AccountRepository:
    """
    Repository for the ``account`` and ``user_preferences`` tables.

    Parameters
    ----------
    db_connection:
        Application-wide :class:`~Data.connection.DatabaseConnection`.
    """

    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection

    # ------------------------------------------------------------------ #
    # Account – creation
    # ------------------------------------------------------------------ #

    def create(
        self,
        username: str,
        password_hash: str,
        name: str,
        role_id: int,
    ) -> None:
        """Insert a new account row."""
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO account (username, password, name, role_id)
                VALUES (?, ?, ?, ?);
                """,
                (username, password_hash, name, role_id),
            )
            conn.commit()
        logger.debug("Account created: username=%s", username)

    # ------------------------------------------------------------------ #
    # Account – reads
    # ------------------------------------------------------------------ #

    def get_by_id(self, user_id: int) -> Optional[sqlite3.Row]:
        """Return the full account row for *user_id*, or ``None``."""
        with self._db.connect() as conn:
            return conn.execute(
                """
                SELECT
                    id, role_id, username, password, name,
                    email, email_verified, pay, profile_picture_path,
                    nbpasswordchange, created_at
                FROM account
                WHERE id = ?;
                """,
                (user_id,),
            ).fetchone()

    def get_by_username(self, username: str) -> Optional[sqlite3.Row]:
        """Return the account row matching *username*, or ``None``."""
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM account WHERE username = ?;",
                (username,),
            ).fetchone()

    def get_by_name(self, name: str) -> Optional[sqlite3.Row]:
        """Return the account row matching *name*, or ``None``."""
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM account WHERE name = ?;",
                (name,),
            ).fetchone()

    def get_id_by_username(self, username: str) -> Optional[int]:
        """Return the *id* for the given *username*, or ``None``."""
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT id FROM account WHERE username = ?;",
                (username,),
            ).fetchone()
        return row["id"] if row else None

    def get_id_by_email(self, email: str) -> Optional[int]:
        """Return the *id* for the given *email*, or ``None``."""
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT id FROM account WHERE email = ?;",
                (email,),
            ).fetchone()
        return row["id"] if row else None

    def get_id_by_name(self, name: str) -> Optional[int]:
        """Return the *id* for the given *name*, or ``None``."""
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT id FROM account WHERE name = ?;",
                (name,),
            ).fetchone()
        return row["id"] if row else None

    def get_username_by_id(self, user_id: int) -> Optional[str]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT username FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row["username"] if row else None

    def get_password_hash(self, user_id: int) -> Optional[str]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT password FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row["password"] if row else None

    def get_name_by_id(self, user_id: int) -> Optional[str]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT name FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row["name"] if row else None

    def get_email_by_id(self, user_id: int) -> Optional[str]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT email FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row["email"] if row else None

    def get_email_verified_by_id(self, user_id: int) -> Optional[int]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT email_verified FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row["email_verified"] if row else None

    def get_profile_picture_path(self, user_id: int) -> Optional[str]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT profile_picture_path FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row["profile_picture_path"] if row else None

    def get_pay_by_id(self, user_id: int) -> Optional[float]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT pay FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row["pay"] if row else None
    
    def get_role_id_by_id(self, user_id: int) -> Optional[int]:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT role_id FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row["role_id"] if row else None

    def count_all(self) -> int:
        """Return the total number of accounts."""
        with self._db.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM account;").fetchone()
        return row["cnt"] if row else 0

    # ------------------------------------------------------------------ #
    # Account – existence checks
    # ------------------------------------------------------------------ #

    def exists_by_id(self, user_id: int) -> bool:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM account WHERE id = ?;",
                (user_id,),
            ).fetchone()
        return row is not None

    def exists_by_username(self, username: str) -> bool:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM account WHERE username = ?;",
                (username,),
            ).fetchone()
        return row is not None

    def exists_by_name(self, name: str) -> bool:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM account WHERE name = ?;",
                (name,),
            ).fetchone()
        return row is not None

    def exists_by_role_id(self, role_id: int) -> bool:
        """Return True if at least one account currently holds *role_id*."""
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM account WHERE role_id = ? LIMIT 1;",
                (role_id,),
            ).fetchone()
        return row is not None

    # ------------------------------------------------------------------ #
    # Account – updates
    # ------------------------------------------------------------------ #

    def update_username(self, user_id: int, new_username: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE account SET username = ? WHERE id = ?;",
                (new_username, user_id),
            )
            conn.commit()

    def update_password(self, user_id: int, new_password_hash: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE account
                SET password = ?, nbpasswordchange = nbpasswordchange + 1
                WHERE id = ?;
                """,
                (new_password_hash, user_id),
            )
            conn.commit()

    def update_name(self, user_id: int, new_name: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE account SET name = ? WHERE id = ?;",
                (new_name, user_id),
            )
            conn.commit()

    def update_email(self, user_id: int, email: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE account SET email = ? WHERE id = ?;",
                (email, user_id),
            )
            conn.commit()

    def update_email_verified(self, user_id: int, verified: bool) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE account SET email_verified = ? WHERE id = ?;",
                (int(verified), user_id),
            )
            conn.commit()

    def update_profile_picture_path(self, user_id: int, path: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE account SET profile_picture_path = ? WHERE id = ?;",
                (path, user_id),
            )
            conn.commit()

    def update_pay(self, user_id: int, new_pay: float) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE account SET pay = ? WHERE id = ?;",
                (new_pay, user_id),
            )
            conn.commit()

    def withdraw_pay(self, user_id: int, amount: float) -> bool:
        """
        Atomically debit *amount* from *user_id*'s balance, but only if the
        balance is sufficient. Avoids the read-then-write race of a separate
        SELECT + UPDATE under concurrent requests. Returns True if the debit
        was applied, False if the balance was insufficient.
        """
        with self._db.connect() as conn:
            cur = conn.execute(
                "UPDATE account SET pay = pay - ? WHERE id = ? AND pay >= ?;",
                (amount, user_id, amount),
            )
            conn.commit()
        return cur.rowcount > 0

    def deposit_pay(self, user_id: int, amount: float) -> None:
        """Atomically credit *amount* to *user_id*'s balance."""
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE account SET pay = pay + ? WHERE id = ?;",
                (amount, user_id),
            )
            conn.commit()

    def update_role(self, user_id: int, role_id: int) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE account SET role_id = ? WHERE id = ?;",
                (role_id, user_id),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Account – deletion
    # ------------------------------------------------------------------ #

    def delete(self, user_id: int) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "DELETE FROM account WHERE id = ?;",
                (user_id,),
            )
            conn.commit()
        logger.info("Account deleted: user_id=%d", user_id)

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def insert_metadata(
        self,
        user_id: int,
        date_connected: str,
        ipv4: str,
    ) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO metadata (user_id, date_connected, ipv4)
                VALUES (?, ?, ?);
                """,
                (user_id, date_connected, ipv4),
            )
            conn.commit()

    def get_metadata_by_user_id(self, user_id: int) -> list[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute(
                "SELECT * FROM metadata WHERE user_id = ?;",
                (user_id,),
            ).fetchall()

    def get_all_metadata(self) -> list[sqlite3.Row]:
        with self._db.connect() as conn:
            return conn.execute("SELECT * FROM metadata;").fetchall()

    # ------------------------------------------------------------------ #
    # User preferences
    # ------------------------------------------------------------------ #

    def create_preferences(self, user_id: int) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "INSERT INTO user_preferences (user_id) VALUES (?);",
                (user_id,),
            )
            conn.commit()

    def get_twofa_enabled(self, user_id: int) -> Optional[bool]:
        """Return the 2FA preference for *user_id*, or ``None`` if missing."""
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT twofa_enabled FROM user_preferences WHERE user_id = ?;",
                (user_id,),
            ).fetchone()
        return bool(row["twofa_enabled"]) if row is not None else None

    def toggle_twofa(self, user_id: int) -> None:
        """Flip the ``twofa_enabled`` flag for *user_id*."""
        current = self.get_twofa_enabled(user_id)
        if current is None:
            logger.warning(
                "toggle_twofa: no preference row found for user_id=%d", user_id
            )
            return
        with self._db.connect() as conn:
            conn.execute(
                "UPDATE user_preferences SET twofa_enabled = ? WHERE user_id = ?;",
                (int(not current), user_id),
            )
            conn.commit()
