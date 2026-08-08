# blueprints/admin/services.py
# Logique métier admin : isolée des routes pour être partagée entre les
# différents points d'entrée (page "Assign Role" et gestion des utilisateurs).

import logging
import sqlite3
from typing import Optional

import extensions as ext

logger = logging.getLogger(__name__)


def change_user_role(
    current_user_id: int,
    current_user_role_name: str,
    target_account: sqlite3.Row,
    role_name: Optional[str],
) -> tuple[bool, str, str]:
    """
    Apply a role change to *target_account*.

    Enforces the same security rules everywhere a role can be assigned:
    an admin cannot change their own role, Super Admin/Admin accounts are
    protected from role changes, and only a Super Admin may grant the
    Admin or Super Admin role.

    Returns ``(success, message, flash_category)``.
    """
    if not role_name:
        return False, "Please select a role.", "warning"

    if current_user_id == target_account["id"]:
        return False, "You cannot change your own role.", "warning"

    super_admin_role_id = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_SUPER_ADMIN)
    admin_role_id       = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_ADMIN)

    if target_account["role_id"] == super_admin_role_id:
        return False, "You cannot change the role of a Super Admin.", "warning"

    if target_account["role_id"] == admin_role_id:
        return False, "You cannot change the role of an Admin.", "warning"

    role_id = ext.db_role_repository.get_role_id(role_name=role_name)
    if role_id is None:
        return False, "Role doesn't exist", "warning"

    # Security: only a Super Admin may grant the Super Admin or Admin role.
    if role_id in (super_admin_role_id, admin_role_id) and current_user_role_name != ext.config.ROLE_NAME_SUPER_ADMIN:
        return False, "Only a Super Admin can assign the Admin or Super Admin role.", "danger"

    ext.db_account_repository.update_role(user_id=target_account["id"], role_id=role_id)
    logger.info("Admin %s changed role of user %s to '%s'", current_user_id, target_account["id"], role_name)
    return True, "Role assigned successfully.", "success"


def set_user_active_status(
    current_user_id: int,
    current_user_role_name: str,
    target_account: sqlite3.Row,
    activate: bool,
) -> tuple[bool, str, str]:
    """
    Suspend or reactivate *target_account*.

    An admin cannot suspend/reactivate their own account, and only a Super
    Admin may suspend or reactivate an Admin or Super Admin account.
    Returns ``(success, message, flash_category)``.
    """
    if current_user_id == target_account["id"]:
        return False, "You cannot suspend or reactivate your own account.", "warning"

    super_admin_role_id = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_SUPER_ADMIN)
    admin_role_id       = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_ADMIN)

    if target_account["role_id"] in (super_admin_role_id, admin_role_id) and current_user_role_name != ext.config.ROLE_NAME_SUPER_ADMIN:
        return False, "Only a Super Admin can suspend or reactivate an Admin or Super Admin account.", "danger"

    if bool(target_account["is_active"]) == activate:
        state = "active" if activate else "suspended"
        return False, f"This account is already {state}.", "warning"

    ext.db_account_repository.set_active(user_id=target_account["id"], is_active=activate)

    if not activate:
        # Suspension takes effect immediately, not just on the next login attempt.
        ext.db_session_repository.revoke_all_for_user(user_id=target_account["id"])

    logger.info("Admin %s set user %s active=%s", current_user_id, target_account["id"], activate)
    action = "reactivated" if activate else "suspended"
    return True, f"Account {action} successfully.", "success"


def delete_user_account(
    current_user_id: int,
    current_user_role_name: str,
    target_account: sqlite3.Row,
) -> tuple[bool, str, str]:
    """
    Permanently delete *target_account*.

    An admin cannot delete their own account, and only a Super Admin may
    delete an Admin or Super Admin account. Returns
    ``(success, message, flash_category)``.
    """
    if current_user_id == target_account["id"]:
        return False, "You cannot delete your own account.", "warning"

    super_admin_role_id = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_SUPER_ADMIN)
    admin_role_id       = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_ADMIN)

    if target_account["role_id"] in (super_admin_role_id, admin_role_id) and current_user_role_name != ext.config.ROLE_NAME_SUPER_ADMIN:
        return False, "Only a Super Admin can delete an Admin or Super Admin account.", "danger"

    ext.db_account_repository.delete(user_id=target_account["id"])
    logger.info("Admin %s deleted user %s", current_user_id, target_account["id"])
    return True, "Account deleted successfully.", "success"


def create_user_account(
    current_user_role_name: str,
    email: str,
    name: str,
    raw_password: str,
    role_name: Optional[str],
) -> tuple[bool, str, str]:
    """
    Create a new account on an admin's behalf.

    Reuses the same validation as self-registration (email format,
    uniqueness, password strength) and additionally requires a Super
    Admin to grant the Admin or Super Admin role. Returns
    ``(success, message, flash_category)``.
    """
    email = (email or "").strip()
    name = (name or "").strip()

    if not email or not name or not raw_password or not role_name:
        return False, "All fields are required.", "warning"

    is_valid_email, email_error = ext.email_manager.validate_user_email(email)
    if not is_valid_email:
        return False, email_error, "warning"

    if ext.db_account_repository.exists_by_email(email):
        return False, "An account with this email already exists.", "warning"

    if ext.db_account_repository.exists_by_name(name):
        return False, "Name is already used.", "warning"

    password_error = ext.utils.validate_password_strength(raw_password, ext.config.MIN_PASSWORD_LENGTH)
    if password_error:
        return False, password_error, "warning"

    role_id = ext.db_role_repository.get_role_id(role_name=role_name)
    if role_id is None:
        return False, "Role doesn't exist", "warning"

    super_admin_role_id = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_SUPER_ADMIN)
    admin_role_id       = ext.db_role_repository.get_role_id(ext.config.ROLE_NAME_ADMIN)

    if role_id in (super_admin_role_id, admin_role_id) and current_user_role_name != ext.config.ROLE_NAME_SUPER_ADMIN:
        return False, "Only a Super Admin can create an Admin or Super Admin account.", "danger"

    try:
        password_hash = ext.hash_manager.generate_password_hash(raw_password)
        ext.db_account_repository.create(email, password_hash, name, role_id)
        user_id = ext.db_account_repository.get_id_by_email(email)
        ext.db_account_repository.create_preferences(user_id=user_id)
        ext.email_manager.send_welcome_email(user_id=user_id)
        logger.info("Admin created new account: user_id=%s email=%s", user_id, email)
        return True, "Account created successfully.", "success"
    except Exception as e:
        logger.error("Error creating account for %s: %s", email, str(e))
        return False, "Account creation failed. Please try again.", "error"
