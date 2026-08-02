import logging
import extensions as ext
from flask_login import current_user

logger = logging.getLogger(__name__)


class PermissionsManager:
    def __init__(self):
        self.db_account = ext.db_account_repository
        self.db_role = ext.db_role_repository
        self.config = ext.config

    def _has_role(self, role: str) -> bool:
        if not current_user or not current_user.is_authenticated:
            return False
        user_roles = getattr(current_user, 'roles', [])
        if isinstance(user_roles, str):
            user_roles = [user_roles]
        return role in user_roles

    def is_user(self) -> bool:
        return current_user.is_authenticated if current_user else False

    def is_admin(self) -> bool:
        try:
            if not current_user or not current_user.is_authenticated:
                return False

            user_id = getattr(current_user, 'id', None)
            if user_id is None:
                return False

            role_id = self.db_account.get_role_id_by_id(user_id)
            if role_id is None:
                return False

            admin_role_id = self.db_role.get_role_id(role_name="admin")
            super_admin_role_id = self.db_role.get_role_id(role_name="super_admin")

            return role_id in (admin_role_id, super_admin_role_id)
        except Exception as e:
            logger.error("Error checking admin status: %s", str(e))
            return False

    def get_dict(self) -> dict[str, list[str]]:
        try:
            permissions_dict: dict[str, list[str]] = {}

            list_all_role = self.db_role.get_all_roles()
            if list_all_role is None:
                logger.warning("No roles found in database")
                return {}

            for role in list_all_role:
                role_name = role.get("name")
                if role_name:
                    permissions_dict[role_name] = []

            query = self.db_role.get_all_role_permission_pairs()
            if query is None:
                return permissions_dict

            for role_id, permission_id in query:
                role_name = self.db_role.get_role_name(role_id)
                permission_name = self.db_role.get_permission_name(permission_id)

                if not role_name or not permission_name:
                    logger.warning("Found invalid role_id=%s or permission_id=%s", role_id, permission_id)
                    continue

                if role_name in permissions_dict.keys():
                    permissions_dict[role_name].append(permission_name)
                else:
                    permissions_dict[role_name] = [permission_name]

            return permissions_dict
        except Exception as e:
            logger.error("Error retrieving permissions dict: %s", str(e))
            return {}

    def create_role(self, role_name: str, list_permissions: list) -> None:
        if not role_name or not isinstance(role_name, str) or not role_name.strip():
            raise RoleNameError("Role name cannot be empty.")

        if self.db_role.role_exists(role_name):
            raise RoleNameError(f"Role '{role_name}' already exists.")

        if not list_permissions or not isinstance(list_permissions, list):
            raise ListPermissionError("List of permissions cannot be empty.")

        try:
            self.db_role.insert_role(role_name=role_name)
            role_id = self.db_role.get_role_id(role_name=role_name)

            if role_id is None:
                raise RuntimeError(f"Failed to create role '{role_name}'")

            for permission_name in list_permissions:
                permission_id = self.db_role.get_permission_id(permission_name=permission_name)
                if permission_id is not None:
                    self.db_role.insert_role_permission(role_id=role_id, permission_id=permission_id)

            logger.info("Role '%s' created successfully", role_name)
        except (RoleNameError, ListPermissionError):
            raise
        except Exception as e:
            logger.error("Error creating role '%s': %s", role_name, str(e))
            raise RuntimeError(f"Failed to create role: {str(e)}")

    def edit_role(self, role_id: int, new_role_name: str, list_permissions: list) -> None:
        if not new_role_name or not isinstance(new_role_name, str) or not new_role_name.strip():
            raise RoleNameError("Role name cannot be empty.")

        if self.db_role.role_exists(new_role_name):
            raise RoleNameError(f"Role '{new_role_name}' already exists.")

        if not list_permissions or not isinstance(list_permissions, list):
            raise ListPermissionError("List of permissions cannot be empty.")

        try:
            self.db_role.update_role(role_id=role_id, role_name=new_role_name)
            self.db_role.delete_permissions_for_role(role_id=role_id)

            for permission_name in list_permissions:
                permission_id = self.db_role.get_permission_id(permission_name=permission_name)
                if permission_id is not None:
                    self.db_role.insert_role_permission(role_id=role_id, permission_id=permission_id)

            logger.info("Role %s updated successfully", role_id)
        except (RoleNameError, ListPermissionError):
            raise
        except Exception as e:
            logger.error("Error editing role %s: %s", role_id, str(e))
            raise RuntimeError(f"Failed to edit role: {str(e)}")

    def delete_role(self, role_id: int) -> None:
        try:
            self.db_role.delete_permissions_for_role(role_id=role_id)
            self.db_role.delete_role(role_id=role_id)
            logger.info("Role %s deleted successfully", role_id)
        except Exception as e:
            logger.error("Error deleting role %s: %s", role_id, str(e))
            raise RuntimeError(f"Failed to delete role: {str(e)}")


class PermissionsManagerError(Exception):
    pass


class RoleNameError(PermissionsManagerError):
    pass


class ListPermissionError(PermissionsManagerError):
    pass
