from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config
from flask_mail import Mail
import logging


# ============================================================
# EXTENSIONS
# ============================================================

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
login_manager = LoginManager()
csrf = CSRFProtect()


# ============================================================
# LOGIN CONFIGURATION
# ============================================================

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


# ============================================================
# USER LOADER
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    """
    Safely load the logged-in user.

    If the session contains an invalid user ID or the database
    temporarily fails, return None instead of crashing the request.
    """
    try:
        from app.models.user import User

        if not user_id:
            return None

        return db.session.get(User, int(user_id))

    except (ValueError, TypeError):
        # Invalid user ID stored in the session.
        return None

    except Exception:
        # Never allow a user-session lookup failure to crash
        # the entire application.
        db.session.rollback()
        logging.exception("Failed to load authenticated user.")
        return None


# ============================================================
# APPLICATION FACTORY
# ============================================================

def create_app():

    import os

    # Vercel uses a read-only filesystem except for /tmp.
    # Keep the existing local behavior unchanged.
    instance_path = "/tmp/agromart-instance" if os.environ.get("VERCEL") else None

    app = Flask(
        __name__,
        instance_path=instance_path
    )

    app.config.from_object(Config)

    # ========================================================
    # INITIALIZE EXTENSIONS
    # ========================================================

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # ========================================================
    # REGISTER BLUEPRINTS
    # ========================================================

    from app.routes.home import home_bp
    from app.routes.auth import auth_bp
    from app.routes.product import product_bp
    from app.routes.cart import cart_bp
    from app.routes.admin.dashboard import dashboard_bp
    from app.routes.admin.categories import categories_bp
    from app.routes.admin.customers import customers_bp
    from app.routes.admin.products import products_bp
    from app.routes.admin.orders import orders_bp
    from app.routes.wishlist import wishlist_bp
    from app.routes.admin.homepage import homepage_bp
    from app.routes.seo import seo_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(product_bp, url_prefix="/products")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(dashboard_bp, url_prefix="/admin")
    app.register_blueprint(categories_bp, url_prefix="/admin/categories")
    app.register_blueprint(customers_bp, url_prefix="/admin/customers")
    app.register_blueprint(products_bp, url_prefix="/admin/products")
    app.register_blueprint(orders_bp, url_prefix="/admin/orders")
    app.register_blueprint(wishlist_bp, url_prefix="/wishlist")
    app.register_blueprint(homepage_bp, url_prefix="/admin/homepage")


    app.register_blueprint(seo_bp)



        # ========================================================
    # GOOGLE SEARCH CONSOLE VERIFICATION
    # ========================================================

    @app.route("/googleaaeb185e1a9c2151.html")
    def google_search_console_verification():
        return "google-site-verification: googleaaeb185e1a9c2151.html"

    # ========================================================
    # GENERAL CONTEXT UTILITIES
    # ========================================================

    @app.context_processor
    def inject_utilities():
        return dict(
            # your context variables/functions here
        )

    # ========================================================
    # CART + WISHLIST COUNTS
    # ========================================================

    @app.context_processor
    def inject_cart_count():

        cart_count = 0
        wishlist_count = 0

        if current_user.is_authenticated:

            # ====================================================
            # CART COUNT
            # ====================================================

            try:
                from app.models.cart import Cart

                cart = Cart.query.filter_by(
                    user_id=current_user.id
                ).first()

                if cart:
                    cart_count = sum(
                        item.quantity
                        for item in cart.items
                    )

            except Exception:
                # A failure calculating the cart count should
                # never make the entire page fail.
                db.session.rollback()
                logging.exception(
                    "Failed to calculate cart count for user %s.",
                    getattr(current_user, "id", None)
                )
                cart_count = 0

            # ====================================================
            # WISHLIST COUNT
            # ====================================================

            try:
                from app.models.wishlist import Wishlist

                wishlist_count = Wishlist.query.filter_by(
                    user_id=current_user.id
                ).count()

            except Exception:
                # A wishlist query failure should not crash
                # otherwise unrelated pages.
                db.session.rollback()
                logging.exception(
                    "Failed to calculate wishlist count for user %s.",
                    getattr(current_user, "id", None)
                )
                wishlist_count = 0

        return {
            "cart_count": cart_count,
            "wishlist_count": wishlist_count
        }

    # ========================================================
    # GLOBAL ERROR LOGGING
    # ========================================================
    #
    # These handlers deliberately log the real exception on the
    # server while returning a generic response to the visitor.
    #
    # We will add proper branded error templates separately after
    # checking your existing template structure.
    # ========================================================

    @app.errorhandler(404)
    def handle_not_found(error):
        app.logger.warning(
            "404 Not Found: %s",
            getattr(error, "description", "Resource not found")
        )

        return (
            "The page you requested could not be found.",
            404
        )

    @app.errorhandler(403)
    def handle_forbidden(error):
        app.logger.warning(
            "403 Forbidden: %s",
            getattr(error, "description", "Access denied")
        )

        return (
            "You do not have permission to access this page.",
            403
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        app.logger.warning(
            "405 Method Not Allowed: %s",
            getattr(error, "description", "Method not allowed")
        )

        return (
            "This action is not allowed.",
            405
        )

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        # Roll back any failed SQLAlchemy transaction so the
        # database session is not left in a failed state.
        try:
            db.session.rollback()
        except Exception:
            logging.exception(
                "Failed to rollback database session after 500 error."
            )

        app.logger.exception(
            "Unhandled internal server error."
        )

        return (
            "Something went wrong on our side. "
            "Please try again in a moment.",
            500
        )

    return app