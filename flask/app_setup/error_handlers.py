import logging

from flask import Flask, render_template

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask):

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.exception("Unhandled server error: %s", error)
        return render_template('errors/500.html'), 500
