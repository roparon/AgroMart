from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models.order import Order
from app.services.email_service import send_email


orders_bp = Blueprint("orders", __name__)


ORDER_STATUSES = [
    "Pending",
    "Confirmed",
    "Processing",
    "Shipped",
    "Delivered",
    "Cancelled",
]


@orders_bp.route("/")
@login_required
def orders():

    if not current_user.is_admin:
        flash(
            "You do not have permission to access this page.",
            "danger"
        )
        return redirect(url_for("home.home"))

    orders = Order.query.order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "admin/orders.html",
        orders=orders,
    )


@orders_bp.route("/<int:order_id>")
@login_required
def order_detail(order_id):

    if not current_user.is_admin:
        flash(
            "You do not have permission to access this page.",
            "danger"
        )
        return redirect(url_for("home.home"))

    order = Order.query.get_or_404(order_id)

    return render_template(
        "admin/order_detail.html",
        order=order,
        order_statuses=ORDER_STATUSES,
    )


@orders_bp.route("/<int:order_id>/status", methods=["POST"])
@login_required
def update_order_status(order_id):

    if not current_user.is_admin:
        flash(
            "You do not have permission to perform this action.",
            "danger"
        )
        return redirect(url_for("home.home"))

    order = Order.query.get_or_404(order_id)

    new_status = request.form.get(
        "status",
        ""
    ).strip()

    if new_status not in ORDER_STATUSES:
        flash(
            "Invalid order status.",
            "danger"
        )

        return redirect(
            url_for(
                "orders.order_detail",
                order_id=order.id,
            )
        )

    old_status = order.status

    if old_status == new_status:
        flash(
            "The order status is already set to this value.",
            "info"
        )

        return redirect(
            url_for(
                "orders.order_detail",
                order_id=order.id,
            )
        )

    try:

        order.status = new_status

        db.session.commit()

        send_email(
            subject=f"AgroMart Order Update - {order.order_code}",
            recipients=[order.user.email],
            template="emails/order_status_update.html",
            order=order,
            old_status=old_status,
            new_status=new_status,
        )

        flash(
            f"Order {order.order_code} status updated to {new_status}.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print(
            f"ORDER STATUS UPDATE FAILED: {e}"
        )

        flash(
            "Unable to update the order status. Please try again.",
            "danger"
        )

    return redirect(
        url_for(
            "orders.order_detail",
            order_id=order.id,
        )
    )