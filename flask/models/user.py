import logging
from flask_login import UserMixin
import extensions as ext

logger = logging.getLogger(__name__)


class User(UserMixin):
    def __init__(self, user_id: int):
        self._db_account = ext.db_account_repository
        self._db_role = ext.db_role_repository

        self.id = user_id
        self._permissions: list[str] | None = None
        self._is_active = True
        self._load_from_db()

    # ── Flask-Login ──────────────────────────────────────────────── #

    def get_id(self) -> str:
        return str(self.id)

    @property
    def is_active(self) -> bool:
        """
        Overrides UserMixin.is_active (a read-only property defaulting to
        True). UserMixin.is_authenticated delegates to this, so a suspended
        account (account.is_active = 0) is treated as unauthenticated by
        Flask-Login and every @login_required / require_* check the moment
        this object is reloaded - which happens on every request, since
        register_login_manager()'s user_loader builds a fresh User (and
        re-reads the DB) each time rather than caching it across requests.
        """
        return self._is_active

    # ── Data loading ─────────────────────────────────────────────── #

    def _load_from_db(self) -> None:
        user = self._db_account.get_by_id(self.id)
        if user is None:
            logger.warning("User with id %s not found in database", self.id)
            raise ValueError(f"User with id {self.id} not found")

        user = dict(user)
        self.name = user.get("name")
        self.email = user.get("email")
        self.email_verified = user.get("email_verified", False)
        self.role_id = user.get("role_id")
        self.nbpasswordchange = user.get("nbpasswordchange", 0)
        self._is_active = bool(user.get("is_active", True))

        if self.role_id is None:
            logger.warning("User %s has no role_id", self.id)
            self.role_name = "unknown"
        else:
            role_name = self._db_role.get_role_name(role_id=self.role_id)
            self.role_name = role_name if role_name else "unknown"

    def reload_data(self) -> None:
        self._load_from_db()

    # ── Permissions ──────────────────────────────────────────────── #

    def load_permissions(self) -> None:
        try:
            permission_ids = self._db_role.get_permission_ids_for_role(self.role_id)
            if permission_ids is None:
                self._permissions = []
                return

            self._permissions = []
            for pid in permission_ids:
                permission_name = self._db_role.get_permission_name(permission_id=pid)
                if permission_name:
                    self._permissions.append(permission_name)
        except Exception as e:
            logger.error("Error loading permissions for user %s: %s", self.id, str(e))
            self._permissions = []

    def has_permission(self, permission_name: str) -> bool:
        if self._permissions is None:
            self.load_permissions()
        return permission_name in (self._permissions or [])
