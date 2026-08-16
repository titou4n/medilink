from flask import Flask, render_template


def register_error_handlers(app: Flask):

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
