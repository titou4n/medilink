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
        self._seed_visitor_account()
        if not self._config.ENV_PROD:
            self._seed_debug_account()

    def _create_account(self, username: str, password: str, name: str, role_name: str) -> None:
        """Generic helper — avoids code duplication between seeders."""
        if self._accounts.exists_by_username(username):
            logger.debug("Account '%s' already exists -> skip.", username)
            return

        role_id = self._roles.get_role_id(role_name)
        if role_id is None:
            logger.error("Cannot create '%s': role '%s' not found.", username, role_name)
            return

        password_hash = self._hasher.generate_password_hash(password)
        self._accounts.create(username, password_hash, name, role_id)

        user_id = self._accounts.get_id_by_username(username)
        if user_id is None:
            logger.error("Account '%s' created but ID not found -> preferences skipped.", username)
            return

        self._accounts.create_preferences(user_id)
        logger.info("Account '%s' created.", username)

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
          - Idempotent by role, not by username: it only fires if no
            account currently holds the Super Admin role, so it never
            runs again after bootstrap even if the account is later
            renamed.
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

        username = self._config.USERNAME_SUPER_ADMIN
        if self._accounts.exists_by_username(username):
            logger.error(
                "Cannot bootstrap Super Admin: username '%s' is already taken "
                "by a non-Super-Admin account. Set a different USERNAME_SUPER_ADMIN.",
                username,
            )
            return

        password = secrets.token_urlsafe(self._config.SUPER_ADMIN_INITIAL_PASSWORD_LENGTH)
        password_hash = self._hasher.generate_password_hash(password)

        self._accounts.create(username, password_hash, self._config.NAME_SUPER_ADMIN, role_id)

        user_id = self._accounts.get_id_by_username(username)
        if user_id is None:
            logger.error("Super Admin account created but ID not found -> preferences skipped.")
            return

        self._accounts.create_preferences(user_id)

        logger.warning(
            "\n"
            "================================================================\n"
            " SUPER ADMIN INITIAL ACCOUNT CREATED\n"
            "   Username : %s\n"
            "   Password : %s\n"
            "\n"
            " This password is shown ONLY ONCE and is stored nowhere in\n"
            " cleartext. Log in immediately and set a new password — it is\n"
            " mandatory before you can access anything else.\n"
            "================================================================",
            username,
            password,
        )

    def _seed_visitor_account(self) -> None:
        self._create_account(
            username  = self._config.USERNAME_VISITOR,
            password  = self._config.PASSWORD_VISITOR,
            name      = self._config.NAME_VISITOR,
            role_name = self._config.ROLE_NAME_VISITOR,
        )

    def _seed_debug_account(self) -> None:
        self._create_account(
            username  = self._config.USERNAME_DEBUG,
            password  = self._config.PASSWORD_DEBUG,
            name      = self._config.NAME_DEBUG,
            role_name = self._config.ROLE_NAME_DEBUG,
        )