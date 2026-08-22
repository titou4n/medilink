
class Permissions():
    # ──────────────────────── Roles & permissions ───────────────────────── #

    LIST_DEFAULT_ROLES: list[str] = ["super_admin", "admin", "moderator", "user"]

    # -- Permission groups --------------------------------------------------
    # Only permissions actually enforced somewhere in the app are declared
    # here — an unchecked permission is dead weight and a false sense of
    # control (see audits/ for the cleanup that removed the rest).

    LIST_PERMISSIONS_ACCOUNT: list[str] = [
        "view_own_profile",
        "edit_own_profile",
        "delete_own_account",
        "change_own_password",
        "export_own_data",
    ]

    LIST_PERMISSIONS_MANAGE_USERS: list[str] = [
        "view_users",
        "create_user",
        "delete_user",
        "ban_user",
        "assign_role",
        "reset_user_password",
    ]

    LIST_PERMISSIONS_MANAGE_ROLES: list[str] = [
        "view_roles",
        "create_role",
        "edit_role",
        "delete_role",
    ]

    LIST_PERMISSIONS_SYSTEM: list[str] = [
        "access_admin_panel",
    ]

    LIST_ACCESS_SERVICES: list[str] = [
        "emergency_information_access",
        "orders_access",
    ]

    LIST_PERMISSIONS_MANAGE_SHOP: list[str] = [
        "manage_products",
    ]

    LIST_ALL_PERMISSIONS: list[str] = (
        LIST_PERMISSIONS_ACCOUNT
        + LIST_PERMISSIONS_MANAGE_USERS
        + LIST_PERMISSIONS_MANAGE_ROLES
        + LIST_PERMISSIONS_SYSTEM
        + LIST_ACCESS_SERVICES
        + LIST_PERMISSIONS_MANAGE_SHOP
    )

    # -- Per-role permission sets ------------------------------------------
    # Least privilege: only super_admin can manage role definitions
    # (create_role/edit_role/delete_role/view_roles). Granting those to
    # "admin" would let it craft a custom role with equivalent privileges
    # and assign it to an account, sidestepping the super_admin-only checks
    # that already guard admin/super_admin accounts in admin/services.py.

    LIST_USER_PERMS: list[str]      = LIST_PERMISSIONS_ACCOUNT + LIST_ACCESS_SERVICES
    LIST_MODERATOR_PERMS: list[str] = LIST_USER_PERMS + ["access_admin_panel", "view_users", "ban_user"]
    LIST_ADMIN_PERMS: list[str]     = LIST_USER_PERMS + LIST_PERMISSIONS_MANAGE_USERS + LIST_PERMISSIONS_SYSTEM + LIST_PERMISSIONS_MANAGE_SHOP
    LIST_SUPER_ADMIN_PERMS: list[str] = LIST_ALL_PERMISSIONS

    # -- Lookup helpers ----------------------------------------------------

    DICT_PERMISSIONS_BY_TYPE: dict[str, list[str]] = {
        "account":       LIST_PERMISSIONS_ACCOUNT,
        "manage_users":  LIST_PERMISSIONS_MANAGE_USERS,
        "manage_roles":  LIST_PERMISSIONS_MANAGE_ROLES,
        "system":        LIST_PERMISSIONS_SYSTEM,
        "services":      LIST_ACCESS_SERVICES,
        "manage_shop":   LIST_PERMISSIONS_MANAGE_SHOP,
    }

    DICT_ROLE_PERMISSION: dict[str, list[str]] = {
        "super_admin": LIST_SUPER_ADMIN_PERMS,
        "admin":       LIST_ADMIN_PERMS,
        "moderator":   LIST_MODERATOR_PERMS,
        "user":        LIST_USER_PERMS,
    }
