"""
migrate_email_only_auth.py
---------------------------
One-time, idempotent migration: drops the ``username`` column from the
``account`` table and makes ``email`` the sole, mandatory, unique login
identifier.

SQLite cannot drop a column or add a UNIQUE/NOT NULL constraint to an
existing column with a plain ALTER TABLE, so this follows the rebuild
procedure documented by SQLite itself (12-step ALTER TABLE recipe):
disable foreign keys, create a new table with the target schema, copy
every row across (backfilling ``email`` where it is missing), drop the
old table, rename the new one, recreate the indexes, re-enable foreign
keys.

Run once, from the `flask/` directory:

    python migrate_email_only_auth.py

Safe to run multiple times: if the ``account`` table no longer has a
``username`` column, the script logs that and exits without touching
anything.
"""
import logging
import sqlite3

from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PLACEHOLDER_DOMAIN = "medilink.local"


def _sanitize_local_part(value: str) -> str:
    """Keep a placeholder email's local-part reasonably valid/readable."""
    cleaned = "".join(c for c in value.strip().lower() if c.isalnum() or c in "._-")
    return cleaned or "account"


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(account);")}
        if "username" not in columns:
            logger.info("No 'username' column on 'account' - already migrated, nothing to do.")
            return

        rows = conn.execute("""
            SELECT id, role_id, username, password, name, email, email_verified,
                   pay, profile_picture_path, nbpasswordchange, created_at
            FROM account;
        """).fetchall()

        # Known seeded identities are matched by their fixed display `name`
        # (independent of the `username` column being removed), so they end
        # up with exactly the email the seeder/config now expects - avoiding
        # a duplicate seeded account being created on next startup.
        name_to_configured_email = {
            Config.NAME_SUPER_ADMIN: Config.EMAIL_SUPER_ADMIN,
            Config.NAME_VISITOR: Config.EMAIL_VISITOR,
            Config.NAME_DEBUG: Config.EMAIL_DEBUG,
        }

        used_emails: set[str] = {
            row["email"].strip().lower() for row in rows if row["email"] and row["email"].strip()
        }
        backfilled: list[tuple[int, str, str]] = []  # (id, old_username, new_email)
        final_rows = []

        for row in rows:
            email = (row["email"] or "").strip()
            if not email:
                candidate = name_to_configured_email.get(row["name"])
                if not candidate:
                    candidate = f"{_sanitize_local_part(row['username'])}@{PLACEHOLDER_DOMAIN}"

                candidate_lower = candidate.strip().lower()
                if candidate_lower in used_emails:
                    # Extremely unlikely (usernames were unique, configured
                    # addresses are distinct) - guarantee uniqueness anyway.
                    candidate = f"{_sanitize_local_part(row['username'])}+{row['id']}@{PLACEHOLDER_DOMAIN}"
                    candidate_lower = candidate.lower()

                used_emails.add(candidate_lower)
                email = candidate
                backfilled.append((row["id"], row["username"], email))

            final_rows.append((
                row["id"], row["role_id"], row["password"], row["name"], email,
                row["email_verified"], row["pay"], row["profile_picture_path"],
                row["nbpasswordchange"], row["created_at"],
            ))

        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("BEGIN;")

        conn.execute("""
            CREATE TABLE account_new (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id             INTEGER NOT NULL,
                password            TEXT    NOT NULL,
                name                TEXT    NOT NULL UNIQUE,
                email               TEXT    NOT NULL UNIQUE,
                email_verified      INTEGER NOT NULL DEFAULT 0,
                pay                 REAL    NOT NULL DEFAULT 0.0,
                profile_picture_path TEXT,
                nbpasswordchange    INTEGER NOT NULL DEFAULT 0,
                created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
            );
        """)

        conn.executemany("""
            INSERT INTO account_new (
                id, role_id, password, name, email, email_verified,
                pay, profile_picture_path, nbpasswordchange, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, final_rows)

        conn.execute("DROP TABLE account;")
        conn.execute("ALTER TABLE account_new RENAME TO account;")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_account_name ON account(name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_account_email ON account(email);")

        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")

        logger.info("Migration complete: %d account row(s) processed.", len(final_rows))
        if backfilled:
            logger.warning(
                "%d account(s) had no email and were assigned a placeholder - "
                "these cannot receive 2FA codes or password-reset emails until "
                "a real email is set via /settings/account/change_email:",
                len(backfilled),
            )
            for account_id, old_username, new_email in backfilled:
                logger.warning("  id=%s  old_username=%r  ->  email=%s", account_id, old_username, new_email)

    except Exception:
        conn.rollback()
        logger.error("Migration failed and was rolled back.", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate(Config.DATABASE_URL)
