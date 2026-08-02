# blueprints/main/routes.py

import logging
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user, logout_user

from blueprints.main import bp
import extensions as ext

logger = logging.getLogger(__name__)


@bp.route('/health')
def health():
    """
    Unauthenticated liveness/readiness probe used by the Docker HEALTHCHECK.

    Checks every hard dependency the app actually needs to serve traffic
    (Redis, main SQLite database). Never returns exception detail to the
    caller - only "ok"/"error" per dependency - the full detail goes to the
    server logs only.
    """
    checks = {}

    try:
        ext.config.SESSION_REDIS.ping()
        checks["redis"] = "ok"
    except Exception as e:
        logger.error("Health check failed: Redis unreachable (%s)", e)
        checks["redis"] = "error"

    try:
        with ext.db_connection.connect() as conn:
            conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Health check failed: main database unreachable (%s)", e)
        checks["database"] = "error"

    is_healthy = all(v == "ok" for v in checks.values())
    return {"status": "ok" if is_healthy else "error", "checks": checks}, 200 if is_healthy else 503


@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    return render_template('main/index.html')


@bp.route('/home')
@bp.route('/home/')
@login_required
def home():
    return render_template('main/home.html',
        id=current_user.id,
        name=ext.db_account_repository.get_name_by_id(current_user.id),
        access_admin_panel=current_user.has_permission("access_admin_panel")
    )


@bp.route('/logout')
@bp.route('/logout/')
@login_required
def logout():
    logout_user()
    ext.session_manager.logout()
    return redirect('/')


@bp.route('/conditions_uses')
@bp.route('/conditions_uses/')
def conditions_uses():
    return render_template('main/conditions_uses.html')
