from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config


# EXTENSIONS

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


# LOGIN CONFIGURATION

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


# USER LOADER

@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return db.session.get(User, int(user_id))

def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.routes.home import home_bp
    from app.routes.auth import auth_bp
    from app.routes.product import product_bp
    from app.routes.cart import cart_bp
    from app.routes.admin.dashboard import dashboard_bp
    from app.routes.admin.categories import categories_bp
    from app.routes.admin.customers import customers_bp
    from app.routes.admin.products import products_bp
    from app.routes.admin.orders import orders_bp




    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(product_bp, url_prefix="/products")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(dashboard_bp, url_prefix="/admin")
    app.register_blueprint(categories_bp, url_prefix="/admin/categories")
    app.register_blueprint(customers_bp, url_prefix="/admin/customers")
    app.register_blueprint(products_bp, url_prefix="/admin/products")
    app.register_blueprint(orders_bp, url_prefix="/admin/orders")



    return app