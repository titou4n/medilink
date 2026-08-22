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

    @app.context_processor
    def inject_cart_item_count():
        if not current_user.is_authenticated or not current_user.has_permission("orders_access"):
            return {"cart_item_count": 0}
        return {"cart_item_count": ext.cart_service.get_item_count(current_user.id)}