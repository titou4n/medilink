import extensions as ext
from flask import Flask
from flask_login import current_user

def register_context_processors(app:Flask):

    @app.context_processor
    def inject_format_datetime():
        return {"format_datetime": ext.utils.format_datetime}

    @app.context_processor
    def inject_nav_can_access_admin():
        can_access_admin = (
            current_user.is_authenticated
            and current_user.has_permission("access_admin_panel")
        )
        return {"nav_can_access_admin": can_access_admin}