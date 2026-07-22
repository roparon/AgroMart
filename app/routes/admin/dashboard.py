from flask import (Blueprint, render_template, redirect, url_for, flash, abort)


from app.models.product import Product
from app.models.category import Category
from app.models.order import Order
from app.models.user import User

admin_bp = Blueprint("admin", __name__)

# We will enable this when admin authentication is ready.
#
# def admin_required():
#     if not current_user.is_authenticated:
#         abort(401)
#
#     if current_user.role != "admin":
#         abort(403)
@admin_bp.route("/")
# @login_required
def dashboard():

    # admin_required()

    total_products = Product.query.count()
    total_categories = Category.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()

    return render_template(
        "admin/dashboard.html",
        total_products=total_products,
        total_categories=total_categories,
        total_orders=total_orders,
        total_users=total_users,
    )

