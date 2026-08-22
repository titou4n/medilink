from flask import Flask
from blueprints.main.routes import bp as main_bp
from blueprints.auth.routes import bp as auth_bp
from blueprints.admin.routes import bp as admin_bp
from blueprints.settings.routes import bp as settings_bp
from blueprints.emergency_information.routes import bp as emergency_information_bp
from blueprints.orders.routes import bp as orders_bp
from blueprints.shop.routes import bp as shop_bp


def register_blueprints(app:Flask):

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,                    url_prefix='/admin_panel')
    app.register_blueprint(settings_bp,                 url_prefix='/settings')
    app.register_blueprint(emergency_information_bp,    url_prefix='/emergency_information')
    app.register_blueprint(orders_bp,                   url_prefix='/orders')
    app.register_blueprint(shop_bp,                      url_prefix='/shop')