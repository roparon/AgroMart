from flask import Blueprint, render_template
from app.models.order import Order



admin_bp = Blueprint("admin", __name__)





@admin_bp.route("/orders")
# @login_required
def orders():

    # admin_required()

    orders = Order.query.order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "admin/orders.html",
        orders=orders,
    )


@admin_bp.route(
    "/orders/<int:order_id>"
)
# @login_required
def order_detail(order_id):

    # admin_required()

    order = Order.query.get_or_404(
        order_id
    )

    return render_template(
        "admin/order_detail.html",
        order=order,
    )
