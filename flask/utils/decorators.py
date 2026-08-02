# utils/decorators.py

import logging
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user
import extensions as ext

logger = logging.getLogger(__name__)


def require_login(f):
    """Abort with 401 if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user or not current_user.is_authenticated:
            logger.warning("Unauthorized access attempt to protected route")
            abort(401)
        return f(*args, **kwargs)
    return decorated


def require_permission(permission_name: str):
    """Check that a logged-in user has the requested permission."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                flash("Please log in first.", "warning")
                logger.info("Unauthenticated user tried to access %s", permission_name)
                return redirect(url_for("auth.login"))

            try:
                if not current_user.has_permission(permission_name):
                    flash("You do not have permission to access this page.", "danger")
                    logger.warning("User %s denied access to %s", current_user.id, permission_name)
                    return redirect(url_for("main.home"))
            except AttributeError as e:
                logger.error("Error checking permission %s for user %s: %s", permission_name, getattr(current_user, 'id', 'unknown'), str(e))
                flash("An error occurred. Please try again.", "danger")
                return redirect(url_for("main.home"))

            return view_func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(f):
    """Abort with 403 if the user is not an admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            if not ext.permission_manager.is_admin():
                logger.warning("Non-admin user %s tried to access admin route", getattr(current_user, 'id', 'unknown'))
                abort(403)
        except Exception as e:
            logger.error("Error checking admin permission: %s", str(e))
            abort(403)
        return f(*args, **kwargs)
    return decorated
