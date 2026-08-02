import logging
from pathlib import Path
from flask import Flask, request, flash, redirect, url_for
from flask_login import current_user
from werkzeug.exceptions import BadRequest
from config import Config
import redis
import extensions as ext
from werkzeug.middleware.proxy_fix import ProxyFix

from blueprints.auth.register_login_manager import register_login_manager
from app_setup.context_processor import register_context_processors
from app_setup.blueprints import register_blueprints

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _hostname_without_port(host: str) -> str:
    """
    Strip a trailing ":<port>" from a Host header value.

    `request.host` includes the port whenever it's non-default (e.g. the
    dev server on 127.0.0.1:8080 makes browsers send "Host: 127.0.0.1:8080"),
    while ALLOWED_HOSTS only lists bare hostnames. IPv6 literals (e.g.
    "[::1]:8080") keep their brackets so they still match the configured
    "[::1]" entry.
    """
    if host.startswith('['):
        return host.split(']')[0] + ']'
    return host.rsplit(':', 1)[0] if ':' in host else host


def create_app(config_object=Config):
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )

    app.config.from_object(obj=config_object)

    # Number of trusted reverse-proxy hops in front of Flask. Current
    # topology: Client -> Cloudflare -> cloudflared -> nginx (this repo) ->
    # Flask. Must match the real chain or remote_addr silently resolves to
    # the wrong hop's IP (see audits/ - this previously mutualized
    # rate-limiting across all visitors).
    proxy_hops = config_object.PROXY_TRUSTED_HOP_COUNT
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=proxy_hops,
        x_proto=proxy_hops,
        x_host=proxy_hops,
        x_port=proxy_hops,
        x_prefix=0
    )

    @app.before_request
    def validate_host():
        allowed_hosts = config_object.ALLOWED_HOSTS
        if allowed_hosts and _hostname_without_port(request.host) not in allowed_hosts:
            logger.warning("Rejected request with invalid Host header: %s", request.host)
            raise BadRequest("Invalid Host header")

    @app.before_request
    def enforce_password_change():
        """
        Security: an account whose password has never been changed since
        creation (nbpasswordchange == 0) — in practice, a freshly
        bootstrapped Super Admin (see AccountsSeeder._seed_super_admin_account)
        — is locked to the "change password" page until it sets a new one.
        """
        if not current_user.is_authenticated:
            return

        if getattr(current_user, "role_name", None) != config_object.ROLE_NAME_SUPER_ADMIN:
            return

        if getattr(current_user, "nbpasswordchange", 0):
            return

        allowed_endpoints = {"settings.account_change_password", "main.logout", "static"}
        if request.endpoint in allowed_endpoints:
            return

        flash("For security reasons, you must set a new password before continuing.", "warning")
        return redirect(url_for("settings.account_change_password"))

    # Extensions
    ext.csrf.init_app(app)
    ext.login_manager.init_app(app)
    ext.login_manager.login_view = "auth.login"
    ext.session_manager.init_app(app)
    ext.limiter.init_app(app)

    # redis
    try:
        redis_client = redis.from_url(app.config["REDIS_URL"])
        redis_client.ping()
        logger.info("Redis connected successfully")

    except Exception as e:
        logger.error("Redis connection failed: %s",str(e))
        raise RuntimeError("Unable to connect to Redis") from e

    # Configuration applicative
    register_login_manager()
    register_context_processors(app)
    register_blueprints(app)

    logger.info("Application initialized successfully")

    return app


if __name__ == '__main__' and not ext.config.ENV_PROD:
    try:
        # First-run convenience: a fresh dev checkout has no SQLite file yet.
        # Detected *before* anything touches the database, since opening a
        # connection would otherwise create an empty file and hide the check.
        db_path = Path(ext.config.DATABASE_URL)
        needs_init = not db_path.exists()

        app = create_app()

        if needs_init:
            logger.warning("No database found at %s - running first-time initialization...", db_path)
            with app.app_context():
                ext._db_manager.init_database()
                ext._roles_permissions_seeders.run()
                ext._accounts_seeder.run()
            logger.info("Database initialization complete.")

        logger.info("Starting development server on 127.0.0.1:8080")
        app.run(
            debug=ext.config.DEBUG,
            host="127.0.0.1",
            port=8080,
            use_reloader=False
        )
    except Exception as e:
        logger.error("Failed to start application: %s", str(e))
        raise
