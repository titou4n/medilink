
class Permissions():
    # ──────────────────────── Roles & permissions ───────────────────────── #

    LIST_DEFAULT_ROLES: list[str] = ["super_admin", "admin", "moderator", "user", "visitor"]

    # -- Permission groups --------------------------------------------------

    LIST_PERMISSIONS_USER: list[str] = [
        "view_own_profile",
        "edit_own_profile",
        "delete_own_account",
        "change_own_password",
        "export_own_data",
        "view_other_profile",
        "follow_profile",
    ]

    LIST_PERMISSIONS_USER_CONTENT: list[str] = [
        "view_content",
        "create_content",
        "edit_own_content",
        "delete_own_content",
        "view_messages",
        "create_messages",
        "edit_own_messages",
        "delete_own_messages",
    ]

    LIST_PERMISSIONS_MANAGE_CONTENT: list[str] = LIST_PERMISSIONS_USER_CONTENT + [
        "edit_all_content",
        "delete_all_content",
    ]

    LIST_PERMISSIONS_MANAGE_USERS: list[str] = [
        "view_users",
        "create_user",
        "edit_user",
        "delete_user",
        "ban_user",
        "assign_role",
    ]

    LIST_PERMISSIONS_MANAGE_ROLE: list[str] = [
        "view_roles",
        "create_role",
        "edit_role",
        "delete_role",
        "manage_permissions",
    ]

    LIST_PERMISSIONS_SYSTEM: list[str] = [
        "access_admin_panel",
        "view_logs",
        "manage_settings",
        "backup_database",
        "restore_database",
        "export_data",
        "import_data",
        "access_statistics",
        "moderate_comments",
        "view_sensitive_data",
    ]

    LIST_ACCESS_SERVICES: list[str] = [
        "emergency_information_access"
    ]

    LIST_ALL_PERMISSIONS: list[str] = (
        LIST_PERMISSIONS_USER
        + LIST_PERMISSIONS_MANAGE_CONTENT
        + LIST_PERMISSIONS_MANAGE_USERS
        + LIST_PERMISSIONS_MANAGE_ROLE
        + LIST_PERMISSIONS_SYSTEM
        + LIST_ACCESS_SERVICES
    )

    # -- Per-role permission sets ------------------------------------------

    LIST_VISITOR_PERMS: list[str]   = ["view_content", "view_own_profile"]
    LIST_USER_PERMS: list[str]      = LIST_PERMISSIONS_USER + LIST_PERMISSIONS_USER_CONTENT + LIST_ACCESS_SERVICES
    LIST_MODERATOR_PERMS: list[str] = LIST_USER_PERMS + ["edit_all_content", "delete_all_content"]
    LIST_ADMIN_PERMS: list[str]     = LIST_ALL_PERMISSIONS

    # -- Lookup helpers ----------------------------------------------------

    DICT_PERMISSIONS_BY_TYPE: dict[str, list[str]] = {
        "user":           LIST_PERMISSIONS_USER,
        "manage_content": LIST_PERMISSIONS_MANAGE_CONTENT,
        "manage_users":   LIST_PERMISSIONS_MANAGE_USERS,
        "manage_role":    LIST_PERMISSIONS_MANAGE_ROLE,
        "system":         LIST_PERMISSIONS_SYSTEM,
    }

    DICT_ROLE_PERMISSION: dict[str, list[str]] = {
        "super_admin": LIST_ALL_PERMISSIONS,
        "admin":       LIST_ADMIN_PERMS,
        "moderator":   LIST_MODERATOR_PERMS,
        "user":        LIST_USER_PERMS,
        "visitor":     LIST_VISITOR_PERMS,
    }