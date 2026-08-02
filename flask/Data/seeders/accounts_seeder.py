"""
Data/seeders/accounts_seeder.py
"""
from __future__ import annotations

import logging
import secrets

from config import Config
from Data.repositories.account_repository import AccountRepository
from Data.repositories.role_repository    import RoleRepository
from utils.hash_manager import HashManager

logger = logging.getLogger(__name__)


class AccountsSeeder:
    def __init__(
        self,
        config: Config,
        account_repo: AccountRepository,
        role_repo: RoleRepository,
        hash_manager: HashManager,
    ) -> None:
        self._config   = config
        self._accounts = account_repo
        self._roles    = role_repo
        self._hasher   = hash_manager

    def run(self) -> None:
        self._seed_super_admin_account()
        if not self._config.ENV_PROD:
            self._seed_debug_account()

    def _create_account(self, email: str, password: str, name: str, role_name: str) -> None:
        """Generic helper — avoids code duplication between seeders."""
        if self._accounts.exists_by_email(email):
            logger.debug("Account '%s' already exists -> skip.", email)
            return

        role_id = self._roles.get_role_id(role_name)
        if role_id is None:
            logger.error("Cannot create '%s': role '%s' not found.", email, role_name)
            return

        password_hash = self._hasher.generate_password_hash(password)
        self._accounts.create(email, password_hash, name, role_id)

        user_id = self._accounts.get_id_by_email(email)
        if user_id is None:
            logger.error("Account '%s' created but ID not found -> preferences skipped.", email)
            return

        self._accounts.create_preferences(user_id)
        logger.info("Account '%s' created.", email)

    def _seed_super_admin_account(self) -> None:
        """
        Bootstrap the Super Admin account, once, on a fresh database.

        Security design:
          - No password is ever read from a `.env` file, an environment
            variable or a Docker secret — a cryptographically random
            password is generated in memory at creation time and never
            persisted anywhere in cleartext (only its hash is stored).
          - It is printed to the application logs exactly once, at
            creation time, so the operator can retrieve it right after the
            first deployment (`docker logs <container>`) and is never
            written to disk.
          - The account is created with `nbpasswordchange = 0`; the
            application enforces a mandatory password change on first
            login for as long as this stays at 0 (see
            utils/decorators.py::enforce_password_change), closing the
            window during which the generated password remains valid.
          - Idempotent by role, not by email: it only fires if no
            account currently holds the Super Admin role, so it never
            runs again after bootstrap even if the account's email is
            later changed.
        """
        role_id = self._roles.get_role_id(self._config.ROLE_NAME_SUPER_ADMIN)
        if role_id is None:
            logger.error(
                "Cannot bootstrap Super Admin: role '%s' not found.",
                self._config.ROLE_NAME_SUPER_ADMIN,
            )
            return

        if self._accounts.exists_by_role_id(role_id):
            logger.debug("A Super Admin account already exists -> skip bootstrap.")
            return

        email = self._config.EMAIL_SUPER_ADMIN
        if self._accounts.exists_by_email(email):
            logger.error(
                "Cannot bootstrap Super Admin: email '%s' is already taken "
                "by a non-Super-Admin account. Set a different EMAIL_SUPER_ADMIN.",
                email,
            )
            return

        password = secrets.token_urlsafe(self._config.SUPER_ADMIN_INITIAL_PASSWORD_LENGTH)
        password_hash = self._hasher.generate_password_hash(password)

        self._accounts.create(email, password_hash, self._config.NAME_SUPER_ADMIN, role_id)

        user_id = self._accounts.get_id_by_email(email)
        if user_id is None:
            logger.error("Super Admin account created but ID not found -> preferences skipped.")
            return

        self._accounts.create_preferences(user_id)

        logger.warning(
            "\n"
            "================================================================\n"
            " SUPER ADMIN INITIAL ACCOUNT CREATED\n"
            "   Email    : %s\n"
            "   Password : %s\n"
            "\n"
            " This password is shown ONLY ONCE and is stored nowhere in\n"
            " cleartext. Log in immediately and set a new password — it is\n"
            " mandatory before you can access anything else.\n"
            "================================================================",
            email,
            password,
        )

    def _seed_debug_account(self) -> None:
        self._create_account(
            email     = self._config.EMAIL_DEBUG,
            password  = self._config.PASSWORD_DEBUG,
            name      = self._config.NAME_DEBUG,
            role_name = self._config.ROLE_NAME_DEBUG,
        )