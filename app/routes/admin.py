from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.models.product import Product
from app.models.category import Category
from app.models.order import Order
from app.models.user import User

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@login_required
def dashboard():

    if current_user.role != "admin":
        abort(403)

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